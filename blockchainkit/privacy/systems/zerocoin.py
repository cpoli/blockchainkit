r"""Zerocoin: anonymous coins from commitments and a proof of membership (Miers et al., 2013).

A user *mints* a zerocoin by paying a fixed amount to the ledger together
with a commitment :math:`C = g^S h^r` to a random serial number :math:`S`.
To *spend* it, the user reveals :math:`S` and proves in zero knowledge that
it knows the opening of *some* minted coin with that serial, without
saying which. The ledger records spent serials, so a coin cannot be spent
twice, but the spend cannot be linked to its mint: every coin ever minted
is in the anonymity set.

Miers, Garman, Green and Rubin made the proof constant-size by gathering
the coins, hashed to primes, in an RSA accumulator
:math:`A = u^{\\prod_i c_i} \bmod N`: each coin has a witness
:math:`w = u^{\\prod_{j \ne i} c_j}` with :math:`w^{c_i} = A`, and the spend
proves knowledge of a witness for a committed coin.

Here the membership proof is instead a ring signature over every minted
coin, linear in their number: :math:`C_i g^{-S} = h^{r}` holds exactly for
the coin being spent, so knowing :math:`r` for one ring member is knowing
the opening of one coin. The accumulator is shown with its witnesses, but
the spend does not use it.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.constants import ACCUMULATOR_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.commitments import pedersen_commit, pedersen_generators
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.utils.primes import is_prime
from blockchainkit.privacy.core.base import ZerocoinSpend
from blockchainkit.privacy.systems.ring_signatures import ring_sign, ring_verify

ACCUMULATOR_MODULUS = 3_000_000_019 * 3_010_000_001
"""int: A 63-bit RSA modulus for the accumulator; its factors must stay unknown to users."""

ACCUMULATOR_BASE = 4
"""int: The accumulator's starting value ``u``, a quadratic residue modulo the modulus."""


def hash_to_prime(value: int, bits: int = 32) -> int:
    """Hash ``value`` to a prime of ``bits`` bits, trying successive counters.

    >>> from blockchainkit.privacy import hash_to_prime
    >>> from blockchainkit.crypto import is_prime
    >>> is_prime(hash_to_prime(12345))
    True
    """
    integer(value, "value")
    integer(bits, "bits", 8)
    if bits > 63:
        raise ValueError("bits must be at most 63")
    counter = 0
    while True:
        digest = sha256(ACCUMULATOR_DOMAIN + f"{value}:{counter}".encode())
        candidate = int.from_bytes(digest, "big") % (1 << bits) | 1 << (bits - 1) | 1
        if is_prime(candidate):
            return candidate
        counter += 1


def accumulate(
    primes: Sequence[int], modulus: int = ACCUMULATOR_MODULUS, base: int = ACCUMULATOR_BASE
) -> int:
    """``base**(product of primes) mod modulus``: one number standing for the whole set."""
    value = base
    for prime in primes:
        value = pow(value, prime, modulus)
    return value


def membership_witness(
    primes: Sequence[int],
    index: int,
    modulus: int = ACCUMULATOR_MODULUS,
    base: int = ACCUMULATOR_BASE,
) -> int:
    """The accumulator of every prime but ``primes[index]``."""
    integer(index, "index")
    if index >= len(primes):
        raise IndexError("no prime at this index")
    return accumulate([*primes[:index], *primes[index + 1 :]], modulus, base)


def verify_membership(
    accumulator: int, prime: int, witness: int, modulus: int = ACCUMULATOR_MODULUS
) -> bool:
    """Whether ``witness**prime == accumulator``, so ``prime`` is in the accumulated set."""
    return pow(witness, prime, modulus) == accumulator


def mint_coin(serial: int, blinding: int, group: DHGroup = TEACHING_GROUP) -> int:
    """The commitment ``g**serial * h**blinding`` that is published when minting."""
    integer(blinding, "blinding", 1)
    return pedersen_commit(serial, blinding, group)


def _ring(coins: Sequence[int], serial: int, group: DHGroup) -> list[int]:
    shift = pow(group.g, -serial, group.p)
    return [coin * shift % group.p for coin in coins]


def prove_zerocoin_spend(
    coins: Sequence[int],
    serial: int,
    blinding: int,
    message: bytes,
    *,
    seed: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> ZerocoinSpend:
    """Reveal ``serial`` and prove it belongs to one of ``coins``, signing ``message``.

    Raises
    ------
    ValueError
        No coin in ``coins`` opens to ``(serial, blinding)``.
    """
    coin = mint_coin(serial, blinding, group)
    if coin not in coins:
        raise ValueError("no minted coin opens to this serial and blinding")
    _, h = pedersen_generators(group)
    ring = _ring(coins, serial, group)
    proof = ring_sign(
        message, ring, list(coins).index(coin), blinding, seed=seed, base=h, group=group
    )
    return ZerocoinSpend(serial, proof)


class ZerocoinPool:
    """The ledger's side of Zerocoin: minted coins, the accumulator, and spent serials.

    Examples
    --------
    >>> from blockchainkit.privacy import ZerocoinPool, mint_coin, prove_zerocoin_spend
    >>> pool = ZerocoinPool()
    >>> for serial, blinding in [(101, 7), (202, 8), (303, 9)]:
    ...     _ = pool.mint(mint_coin(serial, blinding))
    >>> pool.spend(prove_zerocoin_spend(pool.coins, 202, 8, b"pay bob"), b"pay bob")
    >>> sorted(pool.spent)
    [202]
    """

    def __init__(self, group: DHGroup = TEACHING_GROUP) -> None:
        self.group = group
        self._coins: list[int] = []
        self._spent: set[int] = set()

    @property
    def coins(self) -> tuple[int, ...]:
        """Every minted coin commitment, in order."""
        return tuple(self._coins)

    @property
    def spent(self) -> frozenset[int]:
        """Serial numbers already spent."""
        return frozenset(self._spent)

    @property
    def accumulator(self) -> int:
        """The RSA accumulator of the coins hashed to primes."""
        return accumulate([hash_to_prime(coin) for coin in self._coins])

    def mint(self, coin: int) -> int:
        """Record a new coin commitment and return its index."""
        integer(coin, "coin", 2)
        if coin >= self.group.p or pow(coin, self.group.q, self.group.p) != 1:
            raise ValueError("a coin must be a commitment in the group")
        self._coins.append(coin)
        return len(self._coins) - 1

    def spend(self, spend: ZerocoinSpend, message: bytes) -> None:
        """Accept a spend signed over ``message`` and record its serial.

        Raises
        ------
        ValueError
            The serial was already spent, or the proof does not verify
            against the current coins.
        """
        if spend.serial in self._spent:
            raise ValueError("double spend: this serial was already revealed")
        _, h = pedersen_generators(self.group)
        ring = _ring(self._coins, spend.serial, self.group)
        if not self._coins or not ring_verify(message, ring, spend.proof, base=h, group=self.group):
            raise ValueError("invalid spend proof")
        self._spent.add(spend.serial)
