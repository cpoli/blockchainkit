"""eltoo: channel updates without penalties (Decker, Russell and Osuntokun, 2018).

Lightning's penalty is harsh, since a party that publishes an old state by
mistake, after restoring a backup, loses everything, and it forces each
party to keep a secret for every past state. eltoo replaces punishment
with *replacement*. State ``n`` is a pair of transactions: an *update*,
which spends the funding output or any earlier update, and a *settlement*,
which pays out state ``n``'s balances after a delay. If an old update is
published, the other party simply publishes a newer one on top of it, and
only the last update's settlement ever becomes valid.

Two things make this work. Updates are signed with ``SIGHASH_NOINPUT``
(BIP 118), so the signature does not name the output it spends and update
``n`` can attach to any earlier update. And each update output can be spent
by a later update only, by encoding the state number in the lock time::

    OP_IF
        <delay> OP_CHECKSEQUENCEVERIFY OP_DROP <settlement 2-of-2>
    OP_ELSE
        <n + 1> OP_CHECKLOCKTIMEVERIFY OP_DROP <update 2-of-2>
    OP_ENDIF

Each party stores only the latest pair of transactions. Here a signature
over a message that omits the spent output stands in for
``SIGHASH_NOINPUT``, and the relative delay is checked with
``OP_CHECKLOCKTIMEVERIFY`` against the update's age.
"""

from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import Settlement
from blockchainkit.channels.utils.scripts import (
    channel_message,
    derived_key,
    key_pair,
    signature,
    two_of_two_locking,
    two_of_two_unlocking,
)
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.curves import public_key
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.vm.systems.script import ScriptItem, number, verify_script


class EltooChannel:
    """A two-party eltoo channel.

    Parameters
    ----------
    parties : tuple of str
        The two parties.
    keys : tuple of int
        Their private update keys; settlement keys are derived from them.
    deposits : tuple of int
        Each party's initial balance.
    delay : int
        Blocks between an update's confirmation and its settlement.

    Examples
    --------
    >>> from blockchainkit.channels import EltooChannel
    >>> channel = EltooChannel(("alice", "bob"), (7, 5), (100, 0), delay=6)
    >>> channel.pay("alice", 30), channel.pay("alice", 20)
    (1, 2)
    >>> channel.publish(state=0, height=100)  # Alice publishes an old state...
    >>> channel.publish(height=102)  # ...and Bob replaces it with the latest.
    >>> dict(channel.settle(height=108).payouts)
    {'alice': 50, 'bob': 50}
    """

    def __init__(
        self,
        parties: tuple[str, str],
        keys: tuple[int, int],
        deposits: tuple[int, int],
        *,
        delay: int = 144,
    ) -> None:
        if len(set(parties)) != 2:
            raise ValueError("a channel needs two distinct parties")
        for deposit in deposits:
            integer(deposit, "deposit")
        integer(delay, "delay", 1)
        self.parties, self.delay = parties, delay
        self._update_keys = [key_pair(key, "key")[0] for key in keys]
        self._settle_keys = [derived_key(key, "eltoo-settle") for key in keys]
        updates = [public_key(k) for k in self._update_keys]
        self._update_lock = two_of_two_locking(*updates)
        self._settle_lock = two_of_two_locking(*(public_key(k) for k in self._settle_keys))
        self.funding: tuple[ScriptItem, ...] = self._update_lock
        self.id = sha256(channel_message("eltoo", list(parties), [list(p) for p in updates]))
        self.state = 0
        self.balances = dict(zip(parties, deposits, strict=True))
        # Every signed state, so that a cheater, or a stale backup, can publish an old one.
        self.history: dict[int, tuple[dict[str, int], tuple[SchnorrSignature, ...]]] = {}
        self._sign()
        self.onchain: tuple[int, int] | None = None  # (state, height) of the last update.
        self.settlement: Settlement | None = None

    def _update_message(self, state: int) -> bytes:
        return channel_message("eltoo-update", self.id.hex(), state)  # NOINPUT: no outpoint.

    def _settle_message(self, state: int, balances: dict[str, int]) -> bytes:
        return channel_message(
            "eltoo-settle", self.id.hex(), state, [balances[p] for p in self.parties]
        )

    def _sign(self) -> None:
        update = self._update_message(self.state)
        settle = self._settle_message(self.state, self.balances)
        signatures = tuple(signature(k, update) for k in self._update_keys) + tuple(
            signature(k, settle) for k in self._settle_keys
        )
        self.history[self.state] = (dict(self.balances), signatures)

    def update_output(self, state: int) -> tuple[ScriptItem, ...]:
        """Update ``state``'s output: settled after the delay, or replaced by a later update."""
        return (
            "OP_IF",
            number(self.delay),
            "OP_CHECKLOCKTIMEVERIFY",
            "OP_DROP",
            *self._settle_lock,
            "OP_ELSE",
            number(state + 1),
            "OP_CHECKLOCKTIMEVERIFY",
            "OP_DROP",
            *self._update_lock,
            "OP_ENDIF",
        )

    def pay(self, sender: str, amount: int) -> int:
        """Move ``amount`` from ``sender`` to the counterparty and sign the new state."""
        if self.onchain is not None:
            raise ValueError("the channel is closing")
        if sender not in self.parties:
            raise ValueError(f"{sender!r} is not a party to the channel")
        integer(amount, "amount", 1)
        if amount > self.balances[sender]:
            raise ValueError("insufficient balance")
        receiver = self.parties[1] if sender == self.parties[0] else self.parties[0]
        self.balances[sender] -= amount
        self.balances[receiver] += amount
        self.state += 1
        self._sign()
        return self.state

    def publish(self, *, state: int | None = None, height: int) -> None:
        """Publish update ``state`` (the latest by default) on the funding output or last update.

        Raises
        ------
        ValueError
            The update is not newer than the one on chain, so Script rejects it.
        """
        integer(height, "height")
        if self.settlement is not None:
            raise ValueError("the channel is settled")
        state = self.state if state is None else state
        if state not in self.history:
            raise ValueError(f"no state {state} was signed")
        first, second = self.history[state][1][:2]
        unlocking = two_of_two_unlocking(first, second)
        branch: tuple[ScriptItem, ...] = ()
        if self.onchain is None:
            lock = self.funding
        else:
            lock, branch = self.update_output(self.onchain[0]), ("OP_FALSE",)
        message = self._update_message(state)
        result = verify_script((*unlocking, *branch), lock, message=message, locktime=state)
        if not result.valid:
            raise ValueError(f"update {state} cannot replace the one on chain: {result.error}")
        self.onchain = (state, height)

    def settle(self, *, height: int) -> Settlement:
        """Publish the settlement of the update on chain, once its delay has passed."""
        integer(height, "height")
        if self.onchain is None:
            raise ValueError("no update has been published")
        if self.settlement is not None:
            raise ValueError("the channel is settled")
        state, at = self.onchain
        balances, signatures = self.history[state]
        unlocking = (*two_of_two_unlocking(*signatures[2:]), "OP_TRUE")
        message = self._settle_message(state, balances)
        result = verify_script(
            unlocking, self.update_output(state), message=message, locktime=max(height - at, 0)
        )
        if not result.valid:
            raise ValueError(f"the settlement is locked: {result.error}")
        self.settlement = Settlement("unilateral", MappingProxyType(dict(balances)), height, state)
        return self.settlement
