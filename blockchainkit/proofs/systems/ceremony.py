"""Trusted-setup ceremonies: Zcash's parameter generation (2016) and the powers of tau.

A pairing-based SNARK needs ``[tau**i] G`` for a tau nobody knows. In a
ceremony, each participant in turn multiplies the current string by its
own secret s, raising every power to ``(tau s)**i``, and then destroys s.
The final tau is the product of all the secrets, so it stays unknown
unless *every* participant kept theirs: one honest participant is enough.

Anyone can check each contribution with pairings: it publishes ``[s] G``,
and the new string must satisfy

    e(new_1, G) = e(old_1, [s] G)    and    e(new_(i+1), G) = e(new_i, new_1),

the first proving the update used s, the second that the result is still
a list of consecutive powers. Bowe, Gabizon and Miers (2017) made the
ceremony scale to any number of participants, as Zcash's Powers of Tau
(2017-2018) and Ethereum's KZG ceremony (2023) did.
"""

from blockchainkit._validation import integer
from blockchainkit.crypto.systems.curves import Curve, multiply
from blockchainkit.proofs.core.base import SRS, Contribution
from blockchainkit.proofs.systems.pairing import PAIRING_CURVE, pairing


def start_ceremony(max_degree: int, curve: Curve = PAIRING_CURVE) -> SRS:
    """Return the trivial string with tau = 1: every power is the generator.

    >>> from blockchainkit.proofs import start_ceremony, contribute, verify_contribution
    >>> srs = start_ceremony(4)
    >>> step = contribute(srs, 1234)
    >>> verify_contribution(srs, step)
    True
    """
    integer(max_degree, "max_degree", 1)
    return SRS((curve.generator,) * (max_degree + 1), curve)


def contribute(srs: SRS, secret: int) -> Contribution:
    """Multiply the hidden tau by ``secret``: power i is multiplied by ``secret**i``.

    The participant publishes the new string and ``[secret] G``, then
    must forget ``secret``.
    """
    curve = srs.curve
    integer(secret, "secret", 1)
    if secret % curve.order == 0:
        raise ValueError("secret must be nonzero modulo the group order")
    powers, factor = [], 1
    for point in srs.powers:
        powers.append(multiply(factor, point, curve))
        factor = factor * secret % curve.order
    return Contribution(SRS(tuple(powers), curve), multiply(secret, curve.generator, curve))


def verify_contribution(before: SRS, contribution: Contribution) -> bool:
    """Check with pairings that a contribution updated ``before`` by a known secret.

    It fails if the new string is not a list of consecutive powers, if it
    does not build on ``before``, or if the contribution is degenerate.
    """
    after, curve = contribution.srs, before.curve
    g = curve.generator
    if after.curve != curve or len(after.powers) != len(before.powers):
        return False
    if after.powers[0] != g or after.powers[1] is None or contribution.public is None:
        return False
    try:
        if pairing(after.powers[1], g, curve) != pairing(
            before.powers[1], contribution.public, curve
        ):
            return False
        return all(
            pairing(after.powers[i + 1], g, curve)
            == pairing(after.powers[i], after.powers[1], curve)
            for i in range(1, len(after.powers) - 1)
        )
    except ValueError:
        return False
