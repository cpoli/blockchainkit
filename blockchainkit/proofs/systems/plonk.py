"""PLONK: gates, permutation arguments and a universal setup (2019).

Gabizon, Williamson and Ciobotaru wrote a circuit as n gates, each

    q_L a + q_R b + q_O c + q_M a b + q_C = 0,

over the gate's left, right and output wires a, b, c, with the selectors q
fixing the gate's kind. That a wire carries the same value in two gates is
a separate *copy constraint*: the wire values must be unchanged by a
permutation sigma of the 3n wire positions. PLONK checks it with a grand
product. With random beta and gamma,

    prod over positions (w + beta id + gamma) = prod over positions (w + beta sigma + gamma)

holds whp only if the values are constant on every cycle of sigma. The
prover builds the running product z(X) over the domain, z(1) = 1 and

    z(w X) prod (w_k + beta sigma_k(X) + gamma) = z(X) prod (w_k + beta k_k X + gamma),

so gates, copies, and ``z(1) = 1`` all become polynomial identities that
vanish on the domain, combined with powers of a random alpha and divided by
``X**n - 1``. Every polynomial is a KZG commitment, opened at a random zeta.
Unlike Groth16, the setup is *universal*: one powers-of-tau string serves
every circuit up to its size.

This version opens every polynomial at zeta instead of using PLONK's
linearization, and adds no blinding, so it is succinct and sound but not
zero-knowledge. There are no public inputs: constants go in q_C.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import Point
from blockchainkit.crypto.systems.curves import add, multiply
from blockchainkit.proofs.core.base import SRS, KZGOpening, PlonkKey, PlonkProof
from blockchainkit.proofs.systems.kzg import kzg_commit, kzg_open, kzg_verify
from blockchainkit.proofs.utils.polynomials import (
    FIELD_GENERATOR,
    FIELD_PRIME,
    _check_prime,
    evaluate_on_domain,
    interpolate_on_domain,
    poly_add,
    poly_eval,
    poly_scale,
    root_of_unity,
)
from blockchainkit.proofs.utils.transcript import Transcript

K1, K2 = FIELD_GENERATOR, FIELD_GENERATOR**2
"""The coset shifts that label the right and output wire columns."""


class PlonkCircuit:
    """Build PLONK gates over numbered variables.

    Examples
    --------
    >>> from blockchainkit.proofs import PlonkCircuit
    >>> circuit = PlonkCircuit()
    >>> x = circuit.variable(3)
    >>> x3 = circuit.mul(circuit.mul(x, x), x)
    >>> circuit.assert_constant(circuit.add(x3, x), 30)  # x**3 + x = 30
    >>> len(circuit.gates), circuit.is_satisfied()
    (4, True)
    """

    def __init__(self, prime: int = FIELD_PRIME) -> None:
        _check_prime(prime)
        self.prime = prime
        self.values: list[int] = []
        self.gates: list[tuple[tuple[int, int, int], tuple[int, int, int, int, int]]] = []

    def variable(self, value: int) -> int:
        """Add a variable holding ``value``; return its index."""
        if type(value) is not int:
            raise TypeError(f"value must be an integer, not {type(value).__name__}")
        self.values.append(value % self.prime)
        return len(self.values) - 1

    def gate(
        self,
        left: int,
        right: int,
        output: int,
        *,
        ql: int = 0,
        qr: int = 0,
        qo: int = 0,
        qm: int = 0,
        qc: int = 0,
    ) -> None:
        """Add the gate ``ql a + qr b + qo c + qm a b + qc = 0`` on three variables."""
        for index in (left, right, output):
            integer(index, "variable")
            if index >= len(self.values):
                raise IndexError("no such variable")
        for s in (ql, qr, qo, qm, qc):
            if type(s) is not int:
                raise TypeError("selectors must be integers")
        p = self.prime
        self.gates.append(((left, right, output), (ql % p, qr % p, qo % p, qm % p, qc % p)))

    def add(self, left: int, right: int) -> int:
        """Return a new variable constrained to ``left + right``."""
        out = self.variable(self.values[left] + self.values[right])
        self.gate(left, right, out, ql=1, qr=1, qo=-1)
        return out

    def mul(self, left: int, right: int) -> int:
        """Return a new variable constrained to ``left * right``."""
        out = self.variable(self.values[left] * self.values[right])
        self.gate(left, right, out, qm=1, qo=-1)
        return out

    def assert_constant(self, variable: int, value: int) -> None:
        """Add the gate ``variable - value = 0``."""
        self.gate(variable, variable, variable, ql=1, qc=-value)

    def wire_values(self) -> tuple[tuple[int, int, int], ...]:
        """The values on each gate's left, right and output wires."""
        v = self.values
        return tuple((v[a], v[b], v[c]) for (a, b, c), _ in self.gates)

    def is_satisfied(self) -> bool:
        """Whether every gate equation holds."""
        return all(
            _gate_value(selectors, row, self.prime) == 0
            for (_, selectors), row in zip(self.gates, self.wire_values(), strict=True)
        )


def _gate_value(selectors: Sequence[int], row: Sequence[int], prime: int) -> int:
    ql, qr, qo, qm, qc = selectors
    a, b, c = row
    return (ql * a + qr * b + qo * c + qm * a * b + qc) % prime


def plonk_setup(circuit: PlonkCircuit, srs: SRS) -> PlonkKey:
    """Preprocess a circuit: interpolate and commit to its selectors and permutation.

    The same ``srs`` serves every circuit whose padded size n satisfies
    ``3 n <= srs.max_degree``.
    """
    if not isinstance(circuit, PlonkCircuit) or not circuit.gates:
        raise ValueError("need a PlonkCircuit with at least one gate")
    p = srs.curve.order
    if circuit.prime != p:
        raise ValueError("the circuit's field must be the curve's scalar field")
    n = 2
    while n < len(circuit.gates):
        n *= 2
    if 3 * n > srs.max_degree:
        raise ValueError(f"a circuit of {n} gates needs a setup of degree {3 * n}")
    padding = len(circuit.values)  # A zero-valued variable that fills unused rows.
    wiring = [wires for wires, _ in circuit.gates] + [(padding,) * 3] * (n - len(circuit.gates))
    selector_rows = [s for _, s in circuit.gates] + [(0,) * 5] * (n - len(circuit.gates))
    w = root_of_unity(n, p)
    labels = [[k * pow(w, i, p) % p for i in range(n)] for k in (1, K1, K2)]
    positions: dict[int, list[tuple[int, int]]] = {}
    for i, wires in enumerate(wiring):
        for column, variable in enumerate(wires):
            positions.setdefault(variable, []).append((column, i))
    sigma = [list(column) for column in labels]
    for cycle in positions.values():
        for (column, i), (next_column, next_i) in zip(cycle, cycle[1:] + cycle[:1], strict=True):
            sigma[column][i] = labels[next_column][next_i]
    selectors = tuple(interpolate_on_domain([row[k] for row in selector_rows], p) for k in range(5))
    sigmas = tuple(interpolate_on_domain(column, p) for column in sigma)
    return PlonkKey(
        p,
        n,
        w,
        tuple(wiring),
        selectors,
        sigmas,
        tuple(tuple(column) for column in sigma),
        tuple(kzg_commit(poly, srs) for poly in selectors),
        tuple(kzg_commit(poly, srs) for poly in sigmas),
    )


def permutation_product(
    key: PlonkKey, rows: Sequence[Sequence[int]], beta: int, gamma: int
) -> tuple[int, ...]:
    """Return the running product z_0 = 1, z_1, ..., z_n of the copy-constraint argument.

    The last value is 1 when every copy constraint holds, and differs from
    1 whp otherwise.
    """
    prime = key.prime
    padded = _pad(key, rows)
    z, accumulated = [1], 1
    for i in range(key.n):
        numerator = denominator = 1
        for k, shift in enumerate((1, K1, K2)):
            identity = shift * pow(key.omega, i, prime) % prime
            numerator = numerator * (padded[k][i] + beta * identity + gamma) % prime
            denominator = (
                denominator * (padded[k][i] + beta * key.sigma_labels[k][i] + gamma) % prime
            )
        accumulated = accumulated * numerator * pow(denominator, -1, prime) % prime
        z.append(accumulated)
    return tuple(z)


def _pad(key: PlonkKey, rows: Sequence[Sequence[int]]) -> list[list[int]]:
    prime = key.prime
    if len(rows) > key.n or any(len(row) != 3 for row in rows):
        raise ValueError(f"need at most {key.n} rows of three wire values")
    return [[row[k] % prime for row in rows] + [0] * (key.n - len(rows)) for k in range(3)]


def _transcript(key: PlonkKey) -> Transcript:
    transcript = Transcript(b"plonk")
    transcript.append(
        "circuit", [key.n, list(key.selector_commitments), list(key.sigma_commitments)]
    )
    return transcript


def _identity(
    key: PlonkKey,
    e: Sequence[int],
    alpha: int,
    beta: int,
    gamma: int,
    zeta: int,
    prime: int,
) -> int:
    """gate + alpha * permutation + alpha**2 * (z - 1) L_1 at zeta, from the openings."""
    a, b, c, s1, s2, s3, ql, qr, qo, qm, qc, z, _, z_shifted = e
    gate = _gate_value((ql, qr, qo, qm, qc), (a, b, c), prime)
    left = (
        z
        * (a + beta * zeta + gamma)
        * (b + beta * K1 * zeta + gamma)
        * (c + beta * K2 * zeta + gamma)
    )
    right = z_shifted * (a + beta * s1 + gamma) * (b + beta * s2 + gamma) * (c + beta * s3 + gamma)
    vanishing = (pow(zeta, key.n, prime) - 1) % prime
    first = vanishing * pow(key.n * (zeta - 1), -1, prime) % prime
    return (gate + alpha * (left - right) + alpha * alpha * (z - 1) * first) % prime


def plonk_prove(key: PlonkKey, srs: SRS, rows: Sequence[Sequence[int]]) -> PlonkProof:
    """Prove that wire values satisfy the gates and the copy constraints.

    Parameters
    ----------
    key : PlonkKey
        From :func:`plonk_setup`.
    srs : SRS
        The setup the key was made with.
    rows : sequence of sequence of int
        Left, right and output values per gate, as
        :meth:`PlonkCircuit.wire_values` returns them.

    Raises
    ------
    ValueError
        A gate fails, or a copy constraint fails (the running product does
        not return to 1).

    Examples
    --------
    >>> from blockchainkit.proofs import (PlonkCircuit, plonk_setup, plonk_prove,
    ...     plonk_verify, trusted_setup)
    >>> circuit = PlonkCircuit()
    >>> x = circuit.variable(3)
    >>> circuit.assert_constant(circuit.add(circuit.mul(circuit.mul(x, x), x), x), 30)
    >>> srs = trusted_setup(12, secret=4321)
    >>> key = plonk_setup(circuit, srs)
    >>> plonk_verify(key, srs, plonk_prove(key, srs, circuit.wire_values()))
    True
    """
    p, n = srs.curve.order, key.n
    columns = _pad(key, rows)
    for i in range(n):
        selectors = [poly_eval(q, pow(key.omega, i, p), p) for q in key.selectors]
        if _gate_value(selectors, [columns[k][i] for k in range(3)], p):
            raise ValueError(f"gate {i} is not satisfied")
    wires = [interpolate_on_domain(column, p) for column in columns]
    transcript = _transcript(key)
    commitments = [kzg_commit(poly, srs) for poly in wires]
    transcript.append("wires", commitments)
    beta, gamma = transcript.challenge("beta", p), transcript.challenge("gamma", p)
    running = permutation_product(key, rows, beta, gamma)
    if running[-1] != 1:
        raise ValueError("a copy constraint is not satisfied")
    z = interpolate_on_domain(running[:-1], p)
    z_commitment = kzg_commit(z, srs)
    transcript.append("z", z_commitment)
    alpha = transcript.challenge("alpha", p)

    size, shift = 4 * n, FIELD_GENERATOR
    xs = evaluate_on_domain([0, 1], size, p, shift)
    z_shifted = tuple(c * pow(key.omega, i, p) % p for i, c in enumerate(z))
    first = interpolate_on_domain([1] + [0] * (n - 1), p)
    polys = [*wires, *key.sigmas, *key.selectors, z, z_shifted, first]
    a, b, c, s1, s2, s3, ql, qr, qo, qm, qc, zx, zw, l1 = (
        evaluate_on_domain(poly, size, p, shift) for poly in polys
    )
    quotient = []
    for i, x in enumerate(xs):
        gate = _gate_value((ql[i], qr[i], qo[i], qm[i], qc[i]), (a[i], b[i], c[i]), p)
        left = zx[i] * (a[i] + beta * x + gamma) * (b[i] + beta * K1 * x + gamma)
        left = left * (c[i] + beta * K2 * x + gamma)
        right = zw[i] * (a[i] + beta * s1[i] + gamma) * (b[i] + beta * s2[i] + gamma)
        right = right * (c[i] + beta * s3[i] + gamma)
        total = gate + alpha * (left - right) + alpha * alpha * (zx[i] - 1) * l1[i]
        quotient.append(total * pow(pow(x, n, p) - 1, -1, p) % p)
    t = interpolate_on_domain(quotient, p, shift)
    t_commitment = kzg_commit(t, srs)
    transcript.append("t", t_commitment)
    zeta = transcript.challenge("zeta", p)

    opened = [*wires, *key.sigmas, *key.selectors, z, t]
    evaluations = tuple(poly_eval(poly, zeta, p) for poly in opened) + (
        poly_eval(z, zeta * key.omega, p),
    )
    transcript.append("evaluations", list(evaluations))
    v = transcript.challenge("v", p)
    combined: tuple[int, ...] = ()
    for power, poly in enumerate(opened):
        combined = poly_add(combined, poly_scale(poly, pow(v, power, p), p), p)
    return PlonkProof(
        tuple(commitments),
        z_commitment,
        t_commitment,
        evaluations,
        kzg_open(combined, zeta, srs).witness,
        kzg_open(z, zeta * key.omega % p, srs).witness,
    )


def plonk_verify(key: PlonkKey, srs: SRS, proof: PlonkProof) -> bool:
    """Recompute the challenges, check the identity at zeta, and check both batched openings."""
    p, curve = srs.curve.order, srs.curve
    if not isinstance(proof, PlonkProof) or len(proof.evaluations) != 14 or len(proof.wires) != 3:
        return False
    try:
        transcript = _transcript(key)
        transcript.append("wires", list(proof.wires))
        beta, gamma = transcript.challenge("beta", p), transcript.challenge("gamma", p)
        transcript.append("z", proof.z)
        alpha = transcript.challenge("alpha", p)
        transcript.append("t", proof.t)
        zeta = transcript.challenge("zeta", p)
        transcript.append("evaluations", list(proof.evaluations))
        v = transcript.challenge("v", p)
        e = [x % p for x in proof.evaluations]
        vanishing = (pow(zeta, key.n, p) - 1) % p
        if e[12] * vanishing % p != _identity(key, e, alpha, beta, gamma, zeta, p):
            return False
        opened: list[Point] = [
            *proof.wires,
            *key.sigma_commitments,
            *key.selector_commitments,
            proof.z,
            proof.t,
        ]
        commitment: Point = None
        value = 0
        for power, (point, evaluation) in enumerate(zip(opened, e[:13], strict=True)):
            factor = pow(v, power, p)
            commitment = add(commitment, multiply(factor, point, curve), curve)
            value = (value + factor * evaluation) % p
        return kzg_verify(commitment, KZGOpening(zeta, value, proof.opening), srs) and kzg_verify(
            proof.z, KZGOpening(zeta * key.omega % p, e[13], proof.shifted_opening), srs
        )
    except (TypeError, ValueError):
        return False
