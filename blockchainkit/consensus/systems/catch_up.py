"""Idealized models of an attacker catching up with the honest chain."""

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
