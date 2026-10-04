"""Threshold secret sharing: Shamir (1979) and Feldman's verifiable variant (1987)."""

import secrets
from collections.abc import Callable, Sequence

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import FeldmanShares
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
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
    if not is_prime(prime):
        raise ValueError("need a prime modulus below 2**64")
    coefficients = _sample_polynomial(secret, threshold, shares, prime, randbelow)
    return _evaluate(coefficients, shares, prime)


def _sample_polynomial(
    secret: int, threshold: int, shares: int, prime: int, randbelow: Callable[[int], int]
) -> list[int]:
    integer(secret, "secret")
    integer(threshold, "threshold", 2)
    integer(shares, "shares", threshold)
    if secret >= prime or shares >= prime:
        raise ValueError("need secret < prime and shares < prime")
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
    return coefficients


def _evaluate(coefficients: list[int], shares: int, prime: int) -> tuple[tuple[int, int], ...]:
    return tuple(
        (x, sum(c * pow(x, i, prime) for i, c in enumerate(coefficients)) % prime)
        for x in range(1, shares + 1)
    )


def feldman_split(
    secret: int,
    threshold: int,
    shares: int,
    group: DHGroup = TEACHING_GROUP,
    *,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> FeldmanShares:
    """Shamir-share a secret modulo the group order, and publish ``g**a_j``.

    Each commitment hides one polynomial coefficient in the exponent. A share
    holder checks ``g**y == prod(C_j**(x**j))``, which holds exactly when
    their share lies on the committed polynomial, so a cheating dealer is
    caught without anyone learning the secret. The commitment ``g**secret``
    is public, so the secret is only computationally hidden.

    Parameters
    ----------
    secret : int
        Element of the integers modulo the group order q.
    threshold, shares : int
        As for :func:`split_secret`.
    group : DHGroup
        Prime-order group; shares live modulo its order q.
    randbelow : callable
        Uniform randomness source.

    Returns
    -------
    FeldmanShares
        The shares and the public coefficient commitments.

    Examples
    --------
    >>> from random import Random
    >>> from blockchainkit.crypto import feldman_split, feldman_verify, TEACHING_GROUP
    >>> dealt = feldman_split(42, 2, 3, randbelow=Random(0).randrange)
    >>> all(feldman_verify(share, dealt.commitments) for share in dealt.shares)
    True
    """
    coefficients = _sample_polynomial(secret, threshold, shares, group.q, randbelow)
    commitments = tuple(pow(group.g, a, group.p) for a in coefficients)
    return FeldmanShares(_evaluate(coefficients, shares, group.q), commitments)


def feldman_verify(
    share: tuple[int, int], commitments: Sequence[int], group: DHGroup = TEACHING_GROUP
) -> bool:
    """Check one share against the dealer's public commitments."""
    x, y = share
    if type(x) is not int or type(y) is not int or not 0 < x < group.q or not 0 <= y < group.q:
        return False
    expected = 1
    for j, commitment in enumerate(commitments):
        expected = expected * pow(commitment, pow(x, j, group.q), group.p) % group.p
    return pow(group.g, y, group.p) == expected


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
