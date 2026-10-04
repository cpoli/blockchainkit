"""Shamir threshold secret sharing over small prime fields."""

import secrets
from collections.abc import Callable, Sequence

from blockchainkit._validation import integer
from blockchainkit.crypto.utils.primes import is_prime


def split_secret(
    secret: int,
    threshold: int,
    shares: int,
    prime: int = 2089,
    *,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> tuple[tuple[int, int], ...]:
    """Sample a polynomial with constant term ``secret`` and return its shares.

    Parameters
    ----------
    secret : int
        Field element in [0, prime).
    threshold : int
        Number of shares needed, between 2 and shares.
    shares : int
        Number of distinct nonzero evaluation points, below prime.
    prime : int
        Prime field modulus below 2**64.
    randbelow : callable
        Uniform randomness source. Inject ``random.Random(seed).randrange``
        only for reproducible teaching experiments.

    Returns
    -------
    tuple
        (x, y) pairs at x = 1, ..., shares.
    """
    integer(secret, "secret")
    integer(threshold, "threshold", 2)
    integer(shares, "shares", threshold)
    if not is_prime(prime) or secret >= prime or shares >= prime:
        raise ValueError("need prime modulus, secret < prime, and shares < prime")
    coefficients = [secret]
    for _ in range(threshold - 1):
        coefficient = randbelow(prime)
        integer(coefficient, "random coefficient")
        if coefficient >= prime:
            raise ValueError("randbelow returned a value outside the field")
        coefficients.append(coefficient)
    # Coefficients, including the leading one, may be zero. Sampling every
    # polynomial with this constant term uniformly is what makes any
    # threshold - 1 shares independent of the secret (perfect secrecy).
    return tuple(
        (x, sum(c * pow(x, i, prime) for i, c in enumerate(coefficients)) % prime)
        for x in range(1, shares + 1)
    )


def recover_secret(shares: Sequence[tuple[int, int]], prime: int = 2089) -> int:
    """Interpolate at x=0 using Lagrange coefficients.

    The caller must supply enough authentic shares. Without commitments,
    this function cannot detect too few shares or a malicious participant.

    >>> from blockchainkit.crypto import recover_secret
    >>> recover_secret([(1, 8), (2, 11)], prime=17)
    5
    """
    if not shares or not is_prime(prime):
        raise ValueError("need shares and a prime modulus below 2**64")
    for x, y in shares:
        integer(x, "x", 1)
        integer(y, "y")
        if x >= prime or y >= prime:
            raise ValueError("share coordinates must be field elements")
    if len({x for x, _ in shares}) != len(shares):
        raise ValueError("share x coordinates must be distinct")
    result = 0
    for i, (xi, yi) in enumerate(shares):
        weight = 1
        for j, (xj, _) in enumerate(shares):
            if i != j:
                weight = weight * (-xj) * pow(xi - xj, -1, prime) % prime
        result = (result + yi * weight) % prime
    return result
