"""Reed-Solomon codes (1960): data as a polynomial, redundancy as more of its values.

Reed and Solomon encoded ``k`` symbols of a finite field as a polynomial of
degree below ``k`` and transmitted its values at ``n > k`` points. Two
distinct such polynomials agree on at most ``k - 1`` points, so any ``k``
values determine the rest: the code recovers from up to ``n - k`` lost
symbols (erasures), and from up to ``(n - k) // 2`` wrong ones (errors).

This is the systematic form used for data availability: the data are the
polynomial's values at ``0, 1, ..., k - 1``, and the extension adds its
values at ``k, ..., n - 1``. Errors are corrected by Berlekamp and Welch's
algorithm (1986), which finds an error-locator polynomial by linear algebra.
"""

from collections.abc import Mapping, Sequence

from blockchainkit._validation import integer
from blockchainkit.channels.utils.field import (
    PRIME,
    check_prime,
    divide,
    evaluate,
    interpolate,
    solve,
)


def _check_symbols(data: Sequence[int], prime: int) -> None:
    for value in data:
        integer(value, "symbol")
        if value >= prime:
            raise ValueError("symbols must be below the field modulus")


def rs_encode(data: Sequence[int], n: int, *, prime: int = PRIME) -> tuple[int, ...]:
    """Extend ``k = len(data)`` symbols to an ``n``-symbol codeword.

    Parameters
    ----------
    data : sequence of int
        Field elements, the polynomial's values at ``0, ..., k - 1``.
    n : int
        Codeword length, at least ``k`` and at most ``prime``.
    prime : int
        The field modulus.

    Returns
    -------
    tuple of int
        The values at ``0, ..., n - 1``; the first ``k`` are ``data``.

    Examples
    --------
    >>> from blockchainkit.channels import rs_encode
    >>> rs_encode([3, 1, 4], 6)  # The parabola through (0, 3), (1, 1), (2, 4).
    (3, 1, 4, 12, 25, 43)
    """
    check_prime(prime)
    _check_symbols(data, prime)
    k = len(data)
    integer(k, "len(data)", 1)
    integer(n, "n", k)
    if n > prime:
        raise ValueError("a codeword cannot be longer than the field has points")
    points = list(enumerate(data))
    return tuple(data) + tuple(interpolate(points, x, prime) for x in range(k, n))


def is_codeword(shares: Mapping[int, int], k: int, *, prime: int = PRIME) -> bool:
    """True if the ``shares`` (position to value) lie on one polynomial of degree below ``k``."""
    check_prime(prime)
    integer(k, "k", 1)
    points = sorted(shares.items())
    if len(points) < k:
        raise ValueError(f"need at least k = {k} shares")
    basis = points[:k]
    return all(interpolate(basis, x, prime) == y % prime for x, y in points[k:])


def rs_recover(shares: Mapping[int, int], k: int, n: int, *, prime: int = PRIME) -> tuple[int, ...]:
    """Rebuild the whole codeword from any ``k`` of its symbols (erasure decoding).

    Parameters
    ----------
    shares : Mapping
        Position to value, for at least ``k`` positions in ``range(n)``.
    k, n : int
        Data and codeword lengths.
    prime : int
        The field modulus.

    Raises
    ------
    ValueError
        Fewer than ``k`` shares, a position out of range, or shares that are
        not all on one polynomial of degree below ``k``.

    Examples
    --------
    >>> from blockchainkit.channels import rs_recover
    >>> rs_recover({3: 12, 5: 43, 1: 1}, 3, 6)
    (3, 1, 4, 12, 25, 43)
    """
    integer(n, "n", 1)
    for position in shares:
        integer(position, "position")
        if position >= n:
            raise ValueError("share position out of range")
    if not is_codeword(shares, k, prime=prime):
        raise ValueError("the shares are not on one polynomial of degree below k")
    basis = sorted(shares.items())[:k]
    return tuple(interpolate(basis, x, prime) for x in range(n))


def rs_decode(received: Sequence[int | None], k: int, *, prime: int = PRIME) -> tuple[int, ...]:
    """Correct errors and erasures, and return the ``k`` data symbols (Berlekamp-Welch).

    With ``m`` symbols received (``None`` marks an erasure), up to
    ``(m - k) // 2`` of them may be wrong. The algorithm looks for an error
    locator ``E`` (monic, of degree ``e``) and ``Q = P E`` of degree below
    ``k + e`` with ``Q(x_i) = y_i E(x_i)`` at every received point, a linear
    system, then divides.

    Raises
    ------
    ValueError
        Too many errors to correct.

    Examples
    --------
    >>> from blockchainkit.channels import rs_decode
    >>> rs_decode([3, 1, 4, 99, 25, None], 3)  # One error, one erasure.
    (3, 1, 4)
    """
    check_prime(prime)
    integer(k, "k", 1)
    points = [(x, y) for x, y in enumerate(received) if y is not None]
    _check_symbols([y for _, y in points], prime)
    if len(points) < k:
        raise ValueError(f"need at least k = {k} symbols")
    e = (len(points) - k) // 2
    # Unknowns: Q's k + e coefficients, then E's e lower coefficients (E is monic).
    matrix, vector = [], []
    for x, y in points:
        row = [pow(x, j, prime) for j in range(k + e)]
        row += [-y * pow(x, j, prime) % prime for j in range(e)]
        matrix.append(row)
        vector.append(y * pow(x, e, prime) % prime)
    solution = solve(matrix, vector, prime)
    if solution is not None:
        q, locator = solution[: k + e], [*solution[k + e :], 1]
        message, remainder = divide(q, locator, prime)
        # P agrees with every received symbol except at E's at most e roots.
        if not any(remainder):
            return tuple(evaluate(message, x, prime) for x in range(k))
    raise ValueError("too many errors to correct")
