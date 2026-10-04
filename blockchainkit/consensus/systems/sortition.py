"""Cryptographic sortition (Algorand 2017): secret, stake-weighted committee selection.

Algorand picks each round's committee by lottery. Every unit of stake is a
ticket; a user hashes a round seed with their private key (in Algorand a
verifiable random function, so others can check the result) and maps the
hash to a number of selected tickets that is Binomial(stake, tau / W).
Nobody, not even the user, knows who is on the committee before they speak,
and splitting stake across accounts does not change the expected seats.
"""

from math import comb

from blockchainkit._validation import integer
from blockchainkit.constants import SORTITION_DOMAIN
from blockchainkit.crypto.systems.hashing import sha256


def sortition(
    secret: bytes, stake: int, total_stake: int, expected: int, *, round_seed: bytes
) -> int:
    """Return how many of a user's stake units are selected this round.

    The hash of ``secret || round_seed``, read as a uniform number in [0, 1),
    is located in the cumulative Binomial(stake, expected / total_stake)
    distribution. Teaching simplification: a hash of the secret replaces
    the verifiable random function, so others cannot verify the draw.

    Examples
    --------
    >>> from blockchainkit.consensus import sortition
    >>> sortition(b"my key", 0, 1000, 20, round_seed=b"r1")
    0
    """
    if not isinstance(secret, bytes) or not isinstance(round_seed, bytes):
        raise TypeError("secret and round_seed must be bytes")
    integer(stake, "stake")
    integer(total_stake, "total_stake", 1)
    integer(expected, "expected", 1)
    if stake > total_stake or expected > total_stake:
        raise ValueError("stake and expected committee size cannot exceed total stake")
    draw = int.from_bytes(sha256(SORTITION_DOMAIN + secret + round_seed), "big") / 2**256
    p = expected / total_stake
    cumulative = 0.0
    for j in range(stake):
        cumulative += comb(stake, j) * p**j * (1 - p) ** (stake - j)
        if draw < cumulative:
            return j
    return stake  # The last bucket, which also absorbs floating-point rounding.
