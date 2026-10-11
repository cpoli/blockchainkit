"""Sprites and general state channels (Miller et al., 2017).

On a chain with contracts, a channel need not be built from transactions:
a contract can hold the deposits and act as judge. The parties sign
successive versions of any state, and close by submitting the last one. If
one party submits an old version, the other has a dispute period to submit
a newer one, and the contract settles with the highest version it saw. The
state can be balances or the position of a game, so one adjudicator serves
every application: a *general* state channel.

Sprites also cut the time a multi-hop payment locks up collateral. In
Lightning, the expiry of each hop exceeds the next one's by a margin
``delta``, so a payment over ``n`` hops holds the first hop's coins for
about ``n * delta`` blocks. Sprites' hops instead share one deadline: the
recipient must publish the preimage in a global *preimage manager*
contract by then, and every hop settles by asking it. Each hop's expiry is
the same constant, whatever the path's length.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.channels.utils.scripts import PublicKey, channel_message, signature
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.signatures import verify


def state_message(channel: str, version: int, balances: Sequence[int], final: bool) -> bytes:
    """The bytes both parties sign for ``version`` of a channel's state."""
    return channel_message("state", channel, version, list(balances), final)


def sign_state(
    private: int, channel: str, version: int, balances: Sequence[int], *, final: bool = False
) -> SchnorrSignature:
    """One party's signature on a channel state; ``final`` marks a cooperative close.

    Examples
    --------
    >>> from blockchainkit.channels import sign_state
    >>> sign_state(7, "0xchannel", 3, [60, 40]).response > 0
    True
    """
    integer(version, "version")
    return signature(private, state_message(channel, version, balances, final))


class StateChannel(Contract):
    """An adjudicator holding two deposits and settling on the highest signed version.

    Constructor arguments: the parties' public ``keys``, the ``accounts``
    paid at the end, the initial ``balances`` (sent as the deployment's
    value), and the dispute ``period`` in blocks.

    Examples
    --------
    >>> from blockchainkit.channels import StateChannel, sign_state
    >>> from blockchainkit.contracts import World
    >>> from blockchainkit.crypto import public_key
    >>> world = World()
    >>> world.fund("alice", 100)
    >>> keys, accounts = [public_key(7), public_key(5)], ["alice", "bob"]
    >>> channel = world.deploy("alice", StateChannel, keys, accounts, [100, 0], 10, value=100)
    >>> signatures = [sign_state(k, channel, 4, [70, 30]) for k in (7, 5)]
    >>> world.transact("bob", channel, "submit", 4, [70, 30], signatures).success
    True
    >>> world.advance(10)
    >>> world.transact("bob", channel, "settle").success, world.balance("bob")
    (True, 30)
    """

    layout = ("keys", "accounts", "balances", "version", "deadline", "period", "closed")

    def constructor(
        self,
        keys: Sequence[PublicKey],
        accounts: Sequence[str],
        balances: Sequence[int],
        period: int,
    ) -> None:
        self.require(len(keys) == len(accounts) == len(balances) == 2, "a channel has two parties")
        self.require(self.value == sum(balances), "the deposit must equal the balances")
        self.write("keys", tuple((key[0], key[1]) for key in keys))
        self.write("accounts", tuple(accounts))
        self.write("balances", tuple(balances))
        self.write("period", period)

    def _check(
        self,
        version: int,
        balances: Sequence[int],
        signatures: Sequence[SchnorrSignature],
        final: bool,
    ) -> None:
        self.require(not self.read("closed"), "the channel is closed")
        self.require(len(balances) == 2 and min(balances) >= 0, "two non-negative balances")
        self.require(
            sum(balances) == sum(self.read("balances")), "balances must sum to the deposit"
        )
        message = state_message(self.address, version, balances, final)
        self.require(
            len(signatures) == 2
            and all(
                verify(message, s, k) for s, k in zip(signatures, self.read("keys"), strict=True)
            ),
            "both parties must sign",
        )

    def submit(
        self, version: int, balances: Sequence[int], signatures: Sequence[SchnorrSignature]
    ) -> None:
        """Submit a signed state; the first submission opens the dispute period."""
        self._check(version, balances, signatures, False)
        deadline = self.read("deadline")
        self.require(deadline == 0 or self.block_number < deadline, "the dispute period is over")
        self.require(version > self.read("version"), "a newer version was already submitted")
        self.write("version", version)
        self.write("balances", tuple(balances))
        if deadline == 0:
            self.write("deadline", self.block_number + self.read("period"))
        self.emit("Submitted", version=version)

    def close(
        self, version: int, balances: Sequence[int], signatures: Sequence[SchnorrSignature]
    ) -> None:
        """Pay out at once a state both parties signed as final."""
        self._check(version, balances, signatures, True)
        self.write("balances", tuple(balances))
        self._pay()

    def settle(self) -> None:
        """Pay out the highest submitted version once the dispute period is over."""
        deadline = self.read("deadline")
        self.require(deadline != 0, "no state was submitted")
        self.require(self.block_number >= deadline, "the dispute period is not over")
        self.require(not self.read("closed"), "the channel is closed")
        self._pay()

    def _pay(self) -> None:
        self.write("closed", True)
        for account, amount in zip(self.read("accounts"), self.read("balances"), strict=True):
            if amount:
                self.call(account, None, value=amount)


class PreimageManager(Contract):
    """Sprites' global record of when each payment preimage was first published."""

    layout = ("published",)

    def publish(self, preimage: bytes) -> None:
        """Record ``preimage`` at the current block, unless it is already recorded."""
        payment_hash = sha256(preimage)
        if self.read("published", payment_hash) == 0:
            self.write("published", payment_hash, self.block_number)

    def published_by(self, payment_hash: bytes, deadline: int) -> bool:
        """True if the preimage of ``payment_hash`` was published at or before ``deadline``."""
        block = self.read("published", payment_hash)
        return bool(block) and block <= deadline


def htlc_expiries(hops: int, *, delta: int, final: int = 0) -> tuple[int, ...]:
    """Lightning's expiries, sender's hop first: each exceeds the next by ``delta``.

    Examples
    --------
    >>> from blockchainkit.channels import htlc_expiries, sprites_expiries
    >>> htlc_expiries(4, delta=10), sprites_expiries(4, delta=10)
    ((40, 30, 20, 10), (10, 10, 10, 10))
    """
    integer(hops, "hops", 1)
    integer(delta, "delta", 1)
    integer(final, "final")
    return tuple(final + (hops - i) * delta for i in range(hops))


def sprites_expiries(hops: int, *, delta: int, final: int = 0) -> tuple[int, ...]:
    """Sprites' expiries: every hop settles ``delta`` after the shared preimage deadline."""
    integer(hops, "hops", 1)
    integer(delta, "delta", 1)
    integer(final, "final")
    return (final + delta,) * hops


def collateral_time(amounts: Sequence[int], expiries: Sequence[int], *, height: int = 0) -> int:
    """Worst-case coins times blocks a payment locks: the sum of ``amount * (expiry - height)``."""
    integer(height, "height")
    return sum(a * (e - height) for a, e in zip(amounts, expiries, strict=True))
