r"""Brain wallets and the thieves who drain them (Vasek et al., 2016).

A brain wallet keeps no file: its private key is the SHA-256 of a
passphrase the owner remembers,

.. math::

   k = \mathrm{SHA256}(\text{passphrase}),

so the coins can be carried in one's head across a border. But anyone can
compute the same key. Thieves hash dictionaries, quotations, song lyrics and
leaked passwords, keep a table from address to key, and watch the chain:
when a deposit reaches an address in the table, they move the coins away.
Vasek et al. searched the Bitcoin chain for such addresses, found hundreds
of funded brain wallets, and found that most were emptied, many within
minutes of their first deposit, by thieves racing one another. The
passphrase has the entropy a person chooses, not the 128 bits a random key
has, and there is no salt and no stretching to slow the thieves down.
"""

import random
from collections.abc import Iterable, Sequence

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as _check_seed
from blockchainkit.crypto.systems.curves import SECP256K1, public_key
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.wallets.core.base import BrainDrain
from blockchainkit.wallets.systems.base58 import p2pkh_address

PHRASEBOOK = (
    "password",
    "bitcoin",
    "satoshi nakamoto",
    "satoshi",
    "hello world",
    "correct horse battery staple",
    "to be or not to be",
    "one two three four five",
    "the quick brown fox jumps over the lazy dog",
    "how much wood could a woodchuck chuck",
    "i love you",
    "letmein",
    "qwerty",
    "123456",
    "abc123",
    "money",
    "god",
    "love",
    "secret",
    "brainwallet",
    "the answer is 42",
    "all your base are belong to us",
    "may the force be with you",
    "in god we trust",
    "carpe diem",
    "veni vidi vici",
    "e equals m c squared",
    "open sesame",
    "chancellor on brink of second bailout for banks",
    "bitcoin is the future",
)
"""tuple of str: Passphrases of the kind thieves hash first: the most common choices."""


def brain_wallet_key(passphrase: str) -> int:
    """The private key of a brain wallet: SHA-256 of the UTF-8 passphrase.

    Examples
    --------
    >>> from blockchainkit.wallets import brain_wallet_key
    >>> hex(brain_wallet_key("password"))[:10]
    '0x5e884898'
    """
    if not isinstance(passphrase, str):
        raise TypeError("passphrase must be a string")
    key = int.from_bytes(sha256(passphrase.encode()), "big")
    if not 0 < key < SECP256K1.order:
        raise ValueError("this passphrase hashes outside the key range")  # p < 2**-127
    return key


def brain_wallet_address(passphrase: str) -> str:
    """The address of a brain wallet, from its uncompressed key as wallets of 2011-2015 used."""
    return p2pkh_address(public_key(brain_wallet_key(passphrase)), compressed=False)


def crack_brain_wallet(address: str, candidates: Iterable[str]) -> str | None:
    """Hash candidate passphrases until one gives ``address``; None if none does.

    Examples
    --------
    >>> from blockchainkit.wallets import brain_wallet_address, crack_brain_wallet
    >>> crack_brain_wallet(brain_wallet_address("letmein"), ["123456", "letmein"])
    'letmein'
    """
    for candidate in candidates:
        if brain_wallet_address(candidate) == address:
            return candidate
    return None


def simulate_brain_drain(
    wallets: int = 60,
    *,
    weak_share: float = 0.5,
    thieves: Sequence[tuple[float, float]] = ((0.7, 2.0), (0.5, 10.0), (0.3, 50.0)),
    seed: int = 0,
) -> BrainDrain:
    """Fund brain wallets and let thieves with precomputed tables race to empty them.

    Parameters
    ----------
    wallets : int
        Wallets funded, each by a different owner.
    weak_share : float
        Probability that an owner picks a phrase from :data:`PHRASEBOOK`;
        the others use a random 128-bit key written as hex.
    thieves : sequence of tuple
        Each thief's coverage, the share of the phrasebook in its table,
        and its mean delay in blocks between a deposit and its sweep.
    seed : int
        Seeds the owners' choices, the tables and the delays.

    Returns
    -------
    BrainDrain

    Examples
    --------
    >>> from blockchainkit.wallets import simulate_brain_drain
    >>> drain = simulate_brain_drain(20, seed=1)
    >>> drain.drained <= drain.weak
    True
    """
    integer(wallets, "wallets", 1)
    probability(weak_share, "weak_share")
    _check_seed(seed)
    rng = random.Random(seed)
    tables = []
    for coverage, delay in thieves:
        probability(coverage, "coverage")
        if not delay > 0:
            raise ValueError("a thief's mean delay must be positive")
        phrases = rng.sample(PHRASEBOOK, round(coverage * len(PHRASEBOOK)))
        tables.append({brain_wallet_address(phrase) for phrase in phrases})
    weak = drained = 0
    delays, hauls = [], [0] * len(tables)
    for _ in range(wallets):
        if rng.random() < weak_share:
            weak += 1
            passphrase = rng.choice(PHRASEBOOK)
        else:
            passphrase = f"{rng.getrandbits(128):032x}"
        address = brain_wallet_address(passphrase)
        sweeps = [
            (1 + int(rng.expovariate(1 / delay)), thief)
            for thief, ((_, delay), table) in enumerate(zip(thieves, tables, strict=True))
            if address in table
        ]
        if sweeps:
            blocks, thief = min(sweeps)
            drained += 1
            delays.append(blocks)
            hauls[thief] += 1
    return BrainDrain(wallets, weak, drained, tuple(delays), tuple(hauls))
