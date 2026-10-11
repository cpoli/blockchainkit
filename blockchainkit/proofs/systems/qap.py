"""Quadratic arithmetic programs: Gennaro, Gentry, Parno and Raykova (2013), used by Pinocchio.

An R1CS with m constraints is m separate equations. A QAP turns them into
one polynomial identity. Assign constraint j to the point ``w**j`` of a
power-of-two domain, and let ``A_i(X)`` interpolate column i of the first
matrix over the domain (likewise ``B_i`` and ``C_i``). For a witness z,

    A(X) = sum z_i A_i(X),   B(X) = sum z_i B_i(X),   C(X) = sum z_i C_i(X)

agree with the constraint values at each ``w**j``, so every constraint
holds exactly when ``A(X) B(X) - C(X)`` vanishes on the whole domain, that
is, when it is divisible by the target ``t(X) = X**n - 1``:

    A(X) B(X) - C(X) = H(X) t(X).

Pinocchio (Parno, Howell, Gentry and Raykova, 2013) checked this
divisibility at one secret point with pairings, giving the first
practical general-purpose SNARK; Groth16 refined it.
"""

from collections.abc import Sequence

from blockchainkit.proofs.core.base import QAP, R1CS, QAPDivision
from blockchainkit.proofs.utils.polynomials import (
    interpolate_on_domain,
    poly_add,
    poly_divmod,
    poly_mul,
    poly_scale,
    poly_sub,
)


def domain_size(r1cs: R1CS) -> int:
    """The smallest power of two, at least 2, that holds one point per constraint."""
    n = 2
    while n < r1cs.num_constraints:
        n *= 2
    return n


def r1cs_to_qap(r1cs: R1CS) -> QAP:
    """Interpolate each column of the R1CS matrices over the domain of roots of unity.

    Examples
    --------
    >>> from blockchainkit.proofs import Circuit, r1cs_to_qap, qap_divide
    >>> circuit = Circuit()
    >>> out, x = circuit.public(35), circuit.private(3)
    >>> circuit.assert_equal(circuit.mul(circuit.mul(x, x), x) + x + 5, out)
    >>> qap = r1cs_to_qap(circuit.r1cs())
    >>> qap.domain_size, qap_divide(qap, circuit.witness()).satisfied
    (8, True)
    """
    if not isinstance(r1cs, R1CS):
        raise TypeError("r1cs must be an R1CS")
    n = domain_size(r1cs)
    prime = r1cs.prime

    def columns(matrix: tuple[tuple[tuple[int, int], ...], ...]) -> tuple[tuple[int, ...], ...]:
        table = [[0] * n for _ in range(r1cs.num_variables)]
        for j, row in enumerate(matrix):
            for i, c in row:
                table[i][j] = c % prime
        return tuple(interpolate_on_domain(values, prime) for values in table)

    target = poly_sub([0] * n + [1], [1], prime)
    return QAP(prime, n, columns(r1cs.a), columns(r1cs.b), columns(r1cs.c), target)


def qap_divide(qap: QAP, witness: Sequence[int]) -> QAPDivision:
    """Form A, B and C for a witness and divide ``A B - C`` by the target polynomial.

    The witness satisfies the R1CS exactly when the remainder is zero.
    """
    if len(witness) != len(qap.a):
        raise ValueError(f"a witness has {len(qap.a)} entries")
    p = qap.prime

    def combine(polys: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
        total: tuple[int, ...] = ()
        for z, poly in zip(witness, polys, strict=True):
            if z % p:
                total = poly_add(total, poly_scale(poly, z, p), p)
        return total

    left, right, output = combine(qap.a), combine(qap.b), combine(qap.c)
    quotient, remainder = poly_divmod(poly_sub(poly_mul(left, right, p), output, p), qap.target, p)
    return QAPDivision(left, right, output, quotient, remainder)
