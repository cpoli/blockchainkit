"""Arithmetic over a prime field: polynomials, interpolation, and linear systems.

Reed-Solomon codes, data-availability sampling and their fraud proofs all
treat data as the values of a polynomial over the integers modulo a prime.
These helpers are that arithmetic, nothing more: they are not a model of
any protocol, so they live in ``utils``.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.crypto.utils.primes import is_prime

PRIME = 65_537
"""The default field: the Fermat prime 2**16 + 1, large enough for any byte or 16-bit word."""


def check_prime(p: int) -> None:
    """Validate a field modulus."""
    integer(p, "prime", 2)
    if not is_prime(p):
        raise ValueError("the field modulus must be prime")


def inverse(a: int, p: int) -> int:
    """The multiplicative inverse of ``a`` modulo the prime ``p``."""
    if a % p == 0:
        raise ZeroDivisionError("0 has no inverse")
    return pow(a, -1, p)


def evaluate(coefficients: Sequence[int], x: int, p: int) -> int:
    """The polynomial with ``coefficients`` (constant first) at ``x``, by Horner's rule."""
    result = 0
    for c in reversed(coefficients):
        result = (result * x + c) % p
    return result


def interpolate(points: Sequence[tuple[int, int]], x: int, p: int) -> int:
    """Lagrange's formula: the value at ``x`` of the lowest-degree polynomial through ``points``.

    The ``points`` must have distinct abscissas.
    """
    total = 0
    for i, (xi, yi) in enumerate(points):
        numerator = denominator = 1
        for j, (xj, _) in enumerate(points):
            if j != i:
                numerator = numerator * (x - xj) % p
                denominator = denominator * (xi - xj) % p
        total += yi * numerator * inverse(denominator, p)
    return total % p


def solve(matrix: Sequence[Sequence[int]], vector: Sequence[int], p: int) -> list[int] | None:
    """One solution of ``matrix @ x = vector`` modulo ``p``, or None if there is none.

    Gauss-Jordan elimination; free variables are set to 0, so an
    underdetermined system returns one of its solutions.
    """
    rows = [[v % p for v in row] + [b % p] for row, b in zip(matrix, vector, strict=True)]
    columns = len(rows[0]) - 1 if rows else 0
    pivots: list[int] = []
    r = 0
    for c in range(columns):
        pivot = next((i for i in range(r, len(rows)) if rows[i][c]), None)
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        scale = inverse(rows[r][c], p)
        rows[r] = [v * scale % p for v in rows[r]]
        for i, row in enumerate(rows):
            if i != r and row[c]:
                factor = row[c]
                rows[i] = [(a - factor * b) % p for a, b in zip(row, rows[r], strict=True)]
        pivots.append(c)
        r += 1
    if any(row[-1] for row in rows[r:]):
        return None
    solution = [0] * columns
    for i, c in enumerate(pivots):
        solution[c] = rows[i][-1]
    return solution


def divide(
    numerator: Sequence[int], denominator: Sequence[int], p: int
) -> tuple[list[int], list[int]]:
    """Polynomial long division modulo ``p``: ``(quotient, remainder)``, constant term first.

    The denominator's leading coefficient must be nonzero.
    """
    remainder = [c % p for c in numerator] + [0] * (len(denominator) - 1 - len(numerator))
    lead = inverse(denominator[-1], p)
    shift = len(remainder) - len(denominator)
    quotient = [0] * max(shift + 1, 0)
    for i in range(shift, -1, -1):
        factor = remainder[i + len(denominator) - 1] * lead % p
        quotient[i] = factor
        for j, d in enumerate(denominator):
            remainder[i + j] = (remainder[i + j] - factor * d) % p
    return quotient, remainder[: len(denominator) - 1]
