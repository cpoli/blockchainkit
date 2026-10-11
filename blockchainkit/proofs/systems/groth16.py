"""Groth's succinct non-interactive argument (2016): three group elements per proof.

The setup encodes the QAP of a circuit at a secret point tau, blinded by
secrets alpha, beta, gamma and delta. With prover randomness r and s,

    A = alpha + sum z_i A_i(tau) + r delta,
    B = beta  + sum z_i B_i(tau) + s delta,
    C = (sum over private i of z_i K_i(tau) + H(tau) t(tau)) / delta + s A + r B - r s delta,

and the verifier checks one pairing equation,

    e(A, B) = e(alpha, beta) e(sum over public i of x_i L_i, gamma) e(C, delta),

which holds, by the QAP identity, exactly when ``A B - C`` is divisible by
the target. Proofs are three points and verification three pairings plus
one per public input, whatever the circuit; r and s make every proof a
fresh, zero-knowledge one.

This implementation uses the symmetric toy pairing of
:mod:`~blockchainkit.proofs.systems.pairing`, so A, B and C lie in one
group; Groth's paper and deployments use asymmetric pairings, with B in a
second group.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit import _validation
from blockchainkit.crypto.systems.curves import Curve, add, multiply
from blockchainkit.proofs.core.base import (
    R1CS,
    Groth16Proof,
    Groth16Trapdoor,
    ProvingKey,
    VerifyingKey,
)
from blockchainkit.proofs.systems.pairing import PAIRING_CURVE, gt_multiply, pairing
from blockchainkit.proofs.systems.qap import domain_size
from blockchainkit.proofs.utils.groups import linear_combination
from blockchainkit.proofs.utils.polynomials import (
    FIELD_GENERATOR,
    evaluate_on_domain,
    interpolate_on_domain,
    root_of_unity,
)


def groth16_setup(
    r1cs: R1CS, trapdoor: Groth16Trapdoor, curve: Curve = PAIRING_CURVE
) -> ProvingKey:
    """Encode a circuit's QAP at the trapdoor's secret point.

    The QAP polynomials are evaluated at tau directly through the Lagrange
    basis of the domain, ``L_j(tau) = (tau**n - 1) w**j / (n (tau - w**j))``,
    without ever writing them out.

    Parameters
    ----------
    r1cs : R1CS
        Over the curve's scalar field.
    trapdoor : Groth16Trapdoor
        Nonzero secrets, with tau outside the domain. Destroy them after.
    curve : Curve
        The pairing curve.

    Returns
    -------
    ProvingKey
        Its ``verifying_key`` attribute is the verifier's key.
    """
    if not isinstance(r1cs, R1CS) or not isinstance(trapdoor, Groth16Trapdoor):
        raise TypeError("need an R1CS and a Groth16Trapdoor")
    q = curve.order
    if r1cs.prime != q:
        raise ValueError("the circuit's field must be the curve's scalar field")
    secrets = (trapdoor.tau, trapdoor.alpha, trapdoor.beta, trapdoor.gamma, trapdoor.delta)
    if any(type(s) is not int or s % q == 0 for s in secrets):
        raise ValueError("every trapdoor secret must be a nonzero integer modulo the order")
    tau, alpha, beta, gamma, delta = (s % q for s in secrets)
    n = domain_size(r1cs)
    vanishing = (pow(tau, n, q) - 1) % q
    if vanishing == 0:
        raise ValueError("tau must lie outside the domain")
    w, lagrange, point = root_of_unity(n, q), [], 1
    for _ in range(n):
        lagrange.append(vanishing * point * pow(n * (tau - point), -1, q) % q)
        point = point * w % q

    def at_tau(matrix: tuple[tuple[tuple[int, int], ...], ...]) -> list[int]:
        values = [0] * r1cs.num_variables
        for j, row in enumerate(matrix):
            for i, c in row:
                values[i] = (values[i] + c * lagrange[j]) % q
        return values

    a, b, c = at_tau(r1cs.a), at_tau(r1cs.b), at_tau(r1cs.c)

    def encode(scalar: int) -> tuple[int, int] | None:
        return multiply(scalar % q, curve.generator, curve)

    combined = [(beta * a[i] + alpha * b[i] + c[i]) % q for i in range(r1cs.num_variables)]
    public = r1cs.num_public + 1
    gamma_inverse, delta_inverse = pow(gamma, -1, q), pow(delta, -1, q)
    verifying_key = VerifyingKey(
        encode(alpha),
        encode(beta),
        encode(gamma),
        encode(delta),
        tuple(encode(k * gamma_inverse) for k in combined[:public]),
        curve,
    )
    return ProvingKey(
        r1cs,
        n,
        tuple(encode(x) for x in a),
        tuple(encode(x) for x in b),
        tuple(encode(k * delta_inverse) for k in combined[public:]),
        tuple(encode(pow(tau, k, q) * vanishing * delta_inverse) for k in range(n - 1)),
        verifying_key,
    )


def _quotient(r1cs: R1CS, witness: Sequence[int], n: int) -> tuple[int, ...]:
    """H(X) = (A B - C) / (X**n - 1), computed on a shifted domain with the FFT."""
    q = r1cs.prime
    rows = list(r1cs.row_values(witness)) + [(0, 0, 0)] * (n - r1cs.num_constraints)
    shift = FIELD_GENERATOR
    a, b, c = (
        evaluate_on_domain(interpolate_on_domain([row[k] for row in rows], q), n, q, shift)
        for k in range(3)
    )
    inverse = pow(pow(shift, n, q) - 1, -1, q)  # X**n - 1 is constant on the shifted domain.
    values = [(x * y - z) * inverse % q for x, y, z in zip(a, b, c, strict=True)]
    return interpolate_on_domain(values, q, shift)


def groth16_prove(
    proving_key: ProvingKey, witness: Sequence[int], *, seed: int = 0
) -> Groth16Proof:
    """Prove that ``witness`` satisfies the circuit, revealing only its public inputs.

    Parameters
    ----------
    proving_key : ProvingKey
    witness : sequence of int
        ``(1, public..., private...)``, for example from
        :meth:`~blockchainkit.proofs.systems.circuits.Circuit.witness`.
    seed : int
        Seed for the blinding scalars r and s; distinct seeds give distinct
        proofs of the same statement.

    Raises
    ------
    ValueError
        The witness does not satisfy the circuit.
    """
    _validation.seed(seed)
    r1cs = proving_key.r1cs
    curve = proving_key.verifying_key.curve
    q = curve.order
    if not r1cs.is_satisfied(witness):
        raise ValueError("the witness does not satisfy the circuit")
    rng = Random(seed)
    r, s = rng.randrange(1, q), rng.randrange(1, q)
    vk = proving_key.verifying_key
    z = [x % q for x in witness]
    a = add(
        add(vk.alpha, linear_combination(z, proving_key.a_query, curve), curve),
        multiply(r, vk.delta, curve),
        curve,
    )
    b = add(
        add(vk.beta, linear_combination(z, proving_key.b_query, curve), curve),
        multiply(s, vk.delta, curve),
        curve,
    )
    h = _quotient(r1cs, z, proving_key.domain_size)
    c = linear_combination(z[r1cs.num_public + 1 :], proving_key.private_query, curve)
    c = add(c, linear_combination(h, proving_key.h_query[: len(h)], curve), curve)
    c = add(c, multiply(s, a, curve), curve)
    c = add(c, multiply(r, b, curve), curve)
    c = add(c, multiply(-r * s % q, vk.delta, curve), curve)
    return Groth16Proof(a, b, c)


def groth16_verify(
    verifying_key: VerifyingKey, public_inputs: Sequence[int], proof: Groth16Proof
) -> bool:
    """Check ``e(A, B) = e(alpha, beta) e(L, gamma) e(C, delta)``; malformed proofs return False.

    Examples
    --------
    >>> from blockchainkit.proofs import (Circuit, Groth16Trapdoor, groth16_setup,
    ...     groth16_prove, groth16_verify)
    >>> circuit = Circuit()
    >>> out, x = circuit.public(35), circuit.private(3)
    >>> circuit.assert_equal(circuit.mul(circuit.mul(x, x), x) + x + 5, out)
    >>> key = groth16_setup(circuit.r1cs(), Groth16Trapdoor(11, 22, 33, 44, 55))
    >>> proof = groth16_prove(key, circuit.witness(), seed=1)
    >>> vk = key.verifying_key
    >>> groth16_verify(vk, [35], proof), groth16_verify(vk, [36], proof)
    (True, False)
    """
    vk, curve = verifying_key, verifying_key.curve
    if not isinstance(proof, Groth16Proof) or len(public_inputs) != len(vk.public_query) - 1:
        return False
    try:
        inputs = [1, *(x % curve.order for x in public_inputs)]
        combined = linear_combination(inputs, vk.public_query, curve)
        right = gt_multiply(
            pairing(vk.alpha, vk.beta, curve), pairing(combined, vk.gamma, curve), curve
        )
        right = gt_multiply(right, pairing(proof.c, vk.delta, curve), curve)
        return pairing(proof.a, proof.b, curve) == right
    except (TypeError, ValueError):
        return False
