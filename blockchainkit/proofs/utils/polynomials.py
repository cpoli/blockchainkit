"""Univariate polynomials over a prime field, and the fast Fourier transform.

A polynomial is a tuple of coefficients, constant term first, with no
trailing zeros: ``(5, 0, 1)`` is 5 + x**2 and ``()`` is the zero
polynomial. Every function takes the field modulus as ``prime``; it
defaults to :data:`FIELD_PRIME`, the BabyBear prime 15 * 2**27 + 1, whose
multiplicative group has a subgroup of every power-of-two order up to
2**27. Those subgroups are the evaluation domains of the FFT, of FRI, and
of PLONK.
"""

from collections.abc import Sequence
from functools import lru_cache

from blockchainkit._validation import integer
from blockchainkit.crypto.utils.primes import is_prime
from blockchainkit.proofs.core.base import Polynomial

FIELD_PRIME = 15 * 2**27 + 1
"""int: The BabyBear prime 2013265921, used by RISC Zero and SP1. Its
multiplicative group has order 2**27 * 15, so power-of-two domains up to
2**27 points exist."""

FIELD_GENERATOR = 31
"""int: A generator of the multiplicative group of :data:`FIELD_PRIME`."""


@lru_cache(maxsize=64)
def _check_prime(prime: int) -> None:
    integer(prime, "prime", 2)
    if not is_prime(prime):
        raise ValueError("the field modulus must be a prime below 2**64")


def _trim(coefficients: list[int]) -> Polynomial:
    while coefficients and coefficients[-1] == 0:
        coefficients.pop()
    return tuple(coefficients)


def _element(value: int, name: str, prime: int) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer, not {type(value).__name__}")
    return value % prime


def _reduce(poly: Sequence[int], prime: int) -> list[int]:
    for c in poly:
        if type(c) is not int:
            raise TypeError(f"coefficients must be integers, not {type(c).__name__}")
    return [c % prime for c in poly]


def polynomial(coefficients: Sequence[int], prime: int = FIELD_PRIME) -> Polynomial:
    """Reduce coefficients into the field and drop trailing zeros.

    >>> from blockchainkit.proofs import polynomial
    >>> polynomial([3, -1, 0], prime=7)
    (3, 6)
    """
    _check_prime(prime)
    return _trim(_reduce(coefficients, prime))


def degree(poly: Sequence[int]) -> int:
    """Return the degree, or -1 for the zero polynomial."""
    return len(_trim(list(poly))) - 1


def poly_add(left: Sequence[int], right: Sequence[int], prime: int = FIELD_PRIME) -> Polynomial:
    """Add two polynomials."""
    _check_prime(prime)
    a, b = _reduce(left, prime), _reduce(right, prime)
    if len(a) < len(b):
        a, b = b, a
    return _trim([(x + (b[i] if i < len(b) else 0)) % prime for i, x in enumerate(a)])


def poly_scale(poly: Sequence[int], scalar: int, prime: int = FIELD_PRIME) -> Polynomial:
    """Multiply every coefficient by ``scalar``."""
    _check_prime(prime)
    scalar = _element(scalar, "scalar", prime)
    return _trim([c * scalar % prime for c in _reduce(poly, prime)])


def poly_sub(left: Sequence[int], right: Sequence[int], prime: int = FIELD_PRIME) -> Polynomial:
    """Subtract ``right`` from ``left``."""
    return poly_add(left, poly_scale(right, -1, prime), prime)


def poly_mul(left: Sequence[int], right: Sequence[int], prime: int = FIELD_PRIME) -> Polynomial:
    """Multiply two polynomials by schoolbook convolution.

    >>> from blockchainkit.proofs import poly_mul
    >>> poly_mul([1, 1], [1, 1], prime=97)
    (1, 2, 1)
    """
    _check_prime(prime)
    a, b = _reduce(left, prime), _reduce(right, prime)
    if not a or not b:
        return ()
    product = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                product[i + j] += x * y
    return _trim([c % prime for c in product])


def poly_divmod(
    numerator: Sequence[int], denominator: Sequence[int], prime: int = FIELD_PRIME
) -> tuple[Polynomial, Polynomial]:
    """Divide with remainder: ``numerator = quotient * denominator + remainder``.

    Raises
    ------
    ZeroDivisionError
        ``denominator`` is the zero polynomial.

    Examples
    --------
    >>> from blockchainkit.proofs import poly_divmod
    >>> poly_divmod([-1, 0, 1], [-1, 1], prime=97)  # (x**2 - 1) / (x - 1)
    ((1, 1), ())
    """
    _check_prime(prime)
    remainder = _trim(_reduce(numerator, prime))
    divisor = _trim(_reduce(denominator, prime))
    if not divisor:
        raise ZeroDivisionError("division by the zero polynomial")
    rest = list(remainder)
    lead_inverse = pow(divisor[-1], -1, prime)
    quotient = [0] * max(len(rest) - len(divisor) + 1, 0)
    for shift in range(len(quotient) - 1, -1, -1):
        factor = rest[shift + len(divisor) - 1] * lead_inverse % prime
        quotient[shift] = factor
        if factor:
            for i, d in enumerate(divisor):
                rest[shift + i] = (rest[shift + i] - factor * d) % prime
    return _trim(quotient), _trim(rest[: len(divisor) - 1])


def poly_eval(poly: Sequence[int], x: int, prime: int = FIELD_PRIME) -> int:
    """Evaluate at ``x`` by Horner's rule.

    >>> from blockchainkit.proofs import poly_eval
    >>> poly_eval([5, 0, 1], 3, prime=97)
    14
    """
    _check_prime(prime)
    x = _element(x, "x", prime)
    result = 0
    for c in reversed(_reduce(poly, prime)):
        result = (result * x + c) % prime
    return result


def vanishing_polynomial(roots: Sequence[int], prime: int = FIELD_PRIME) -> Polynomial:
    """Return the monic polynomial whose roots are ``roots``: the product of (x - root)."""
    result: Polynomial = (1,)
    for root in roots:
        result = poly_mul(result, (-root, 1), prime)
    return result


def interpolate(points: Sequence[tuple[int, int]], prime: int = FIELD_PRIME) -> Polynomial:
    """Return the unique polynomial of degree below ``len(points)`` through ``points``.

    Lagrange's formula, in O(n**2) field operations.

    Raises
    ------
    ValueError
        Two points share an x-coordinate.

    Examples
    --------
    >>> from blockchainkit.proofs import interpolate
    >>> interpolate([(0, 5), (1, 6), (2, 9)], prime=97)  # 5 + x**2
    (5, 0, 1)
    """
    _check_prime(prime)
    xs = _reduce([x for x, _ in points], prime)
    ys = _reduce([y for _, y in points], prime)
    if len(set(xs)) != len(xs):
        raise ValueError("interpolation points need distinct x-coordinates")
    full = vanishing_polynomial(xs, prime)
    result = [0] * len(xs)
    for xi, yi in zip(xs, ys, strict=True):
        if not yi:
            continue
        basis, _ = poly_divmod(full, (-xi, 1), prime)  # Product of (x - xj) for j != i.
        scale = yi * pow(poly_eval(basis, xi, prime), -1, prime) % prime
        for k, c in enumerate(basis):
            result[k] = (result[k] + scale * c) % prime
    return _trim(result)


def root_of_unity(n: int, prime: int = FIELD_PRIME) -> int:
    """Return an element of multiplicative order exactly ``n``, a power of two.

    The domain ``{w**i}`` of the FFT. ``n`` must divide ``prime - 1``.

    >>> from blockchainkit.proofs import root_of_unity
    >>> w = root_of_unity(8)
    >>> pow(w, 8, 2013265921), pow(w, 4, 2013265921) != 1
    (1, True)
    """
    _check_prime(prime)
    integer(n, "n", 1)
    if n & (n - 1) or (prime - 1) % n:
        raise ValueError("n must be a power of two dividing prime - 1")
    if n == 1:
        return 1
    if prime == FIELD_PRIME:
        return pow(FIELD_GENERATOR, (prime - 1) // n, prime)
    candidate = 2
    while True:  # Half of all nonzero elements are non-residues, so this ends quickly.
        w = pow(candidate, (prime - 1) // n, prime)
        if pow(w, n // 2, prime) != 1:
            return w
        candidate += 1


def domain(n: int, prime: int = FIELD_PRIME, offset: int = 1) -> tuple[int, ...]:
    """Return the ``n`` points ``offset * w**i`` of a (shifted) power-of-two subgroup."""
    w = root_of_unity(n, prime)
    integer(offset, "offset", 1)
    points, x = [], offset % prime
    for _ in range(n):
        points.append(x)
        x = x * w % prime
    return tuple(points)


def _fft(values: list[int], w: int, prime: int) -> list[int]:
    n = len(values)
    if n == 1:
        return values
    even = _fft(values[0::2], w * w % prime, prime)
    odd = _fft(values[1::2], w * w % prime, prime)
    result = [0] * n
    factor = 1
    for i in range(n // 2):
        t = factor * odd[i] % prime
        result[i] = (even[i] + t) % prime
        result[i + n // 2] = (even[i] - t) % prime
        factor = factor * w % prime
    return result


def evaluate_on_domain(
    poly: Sequence[int], n: int, prime: int = FIELD_PRIME, offset: int = 1
) -> tuple[int, ...]:
    """Evaluate at the ``n`` points of :func:`domain` with the radix-2 FFT.

    Costs O(n log n) field operations instead of the O(n**2) of evaluating
    point by point. The polynomial's degree must be below ``n``.

    >>> from blockchainkit.proofs import evaluate_on_domain, poly_eval, domain
    >>> evaluate_on_domain([1, 2, 3], 4) == tuple(poly_eval([1, 2, 3], x) for x in domain(4))
    True
    """
    coefficients = _reduce(poly, prime)
    w = root_of_unity(n, prime)
    integer(offset, "offset", 1)
    if len(_trim(list(coefficients))) > n:
        raise ValueError("the polynomial's degree must be below n")
    coefficients = (coefficients + [0] * n)[:n]
    shift = 1
    for i in range(n):
        coefficients[i] = coefficients[i] * shift % prime
        shift = shift * offset % prime
    return tuple(_fft(coefficients, w, prime))


def interpolate_on_domain(
    values: Sequence[int], prime: int = FIELD_PRIME, offset: int = 1
) -> Polynomial:
    """Inverse of :func:`evaluate_on_domain`: the polynomial taking ``values`` on the domain.

    >>> from blockchainkit.proofs import evaluate_on_domain, interpolate_on_domain
    >>> interpolate_on_domain(evaluate_on_domain([4, 0, 7], 8, offset=31), offset=31)
    (4, 0, 7)
    """
    n = len(values)
    w = root_of_unity(n, prime)
    integer(offset, "offset", 1)
    if offset % prime == 0:
        raise ValueError("offset must be invertible")
    coefficients = _fft(_reduce(values, prime), pow(w, -1, prime), prime)
    scale, unshift = pow(n, -1, prime), pow(offset, -1, prime)
    factor = scale
    for i in range(n):
        coefficients[i] = coefficients[i] * factor % prime
        factor = factor * unshift % prime
    return _trim(coefficients)
