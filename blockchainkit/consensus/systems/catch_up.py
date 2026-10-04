"""Idealized models of an attacker catching up with the honest chain."""

from math import exp

from blockchainkit._validation import integer


def eventual_catch_up(attacker_fraction: float, deficit: int) -> float:
    """Return eventual catch-up probability in an ideal infinite random walk.

    For q<1/2 this is (q/(1-q))**deficit. This is NOT Nakamoto's finite-
    confirmation Poisson model: there is no propagation delay or time bound.

    >>> from blockchainkit.consensus import eventual_catch_up
    >>> eventual_catch_up(0.25, 2)
    0.1111111111111111
    """
    if isinstance(attacker_fraction, bool) or not isinstance(attacker_fraction, (int, float)):
        raise TypeError("attacker_fraction must be a real number in [0, 1]")
    if not 0 <= attacker_fraction <= 1:
        raise ValueError("attacker_fraction must be in [0, 1]")
    integer(deficit, "deficit")
    if deficit == 0 or attacker_fraction >= 0.5:
        return 1.0
    return (attacker_fraction / (1 - attacker_fraction)) ** deficit


def attacker_success_probability(attacker_fraction: float, confirmations: int) -> float:
    """Return Nakamoto's probability that an attacker ever overtakes ``z`` confirmations.

    While the honest chain gains z blocks, the attacker's progress is
    approximately Poisson with mean ``lambda = z q / p``. From each possible
    lead k, the attacker still needs to make up ``z - k`` blocks, which by
    :func:`eventual_catch_up` happens with probability ``(q/p)**(z-k)``
    (whitepaper, section 11):

    ``P = 1 - sum_{k=0}^{z} e^(-lambda) lambda^k / k! * (1 - (q/p)^(z-k))``.

    Examples
    --------
    >>> from blockchainkit.consensus import attacker_success_probability
    >>> round(attacker_success_probability(0.1, 5), 7)
    0.0009137
    """
    if isinstance(attacker_fraction, bool) or not isinstance(attacker_fraction, (int, float)):
        raise TypeError("attacker_fraction must be a real number in [0, 1]")
    if not 0 <= attacker_fraction <= 1:
        raise ValueError("attacker_fraction must be in [0, 1]")
    integer(confirmations, "confirmations")
    q, z = attacker_fraction, confirmations
    if q >= 0.5:
        return 1.0
    p = 1 - q
    lam = z * q / p
    total, poisson = 1.0, exp(-lam)
    for k in range(z + 1):
        if k:
            poisson *= lam / k
        total -= poisson * (1 - (q / p) ** (z - k))
    return max(0.0, total)
