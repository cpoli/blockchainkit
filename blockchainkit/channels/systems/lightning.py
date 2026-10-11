r"""The Lightning Network's revocable commitments (Poon and Dryja, 2016).

A duplex channel ranks its states by time locks, which limits how many
updates it can hold. Poon and Dryja rank them by *punishment* instead. Each
party holds its own version of the current state, a *commitment
transaction* spending the 2-of-2 funding output and signed by the other
party. It pays the counterparty at once, but pays its holder only after a
delay, and during that delay anyone holding the *revocation key* can take
the holder's output. To move to a new state, each party gives the other the
secret behind its old commitment's revocation key. Publishing a revoked
commitment then hands the counterparty everything in the channel, if it
notices within the delay.

The revocation key combines the holder's per-commitment point with the
counterparty's revocation base point, so neither can sign with it alone
until the holder reveals its per-commitment secret:

.. math::

   R_n = S_n + B, \qquad r_n = s_n + b \pmod q.

The per-commitment secrets are a hash chain used backwards, as in
Lightning's *shachain*: the secret of state ``n - 1`` is the hash of the
secret of state ``n``, so the counterparty stores only the latest one and
derives every older one.

Bitcoin enforces the delay with ``OP_CHECKSEQUENCEVERIFY``, which this
package's Script lacks; the delayed branch here uses
``OP_CHECKLOCKTIMEVERIFY`` against the commitment's age instead. The
deployed protocol also hashes the base points into the revocation key to
stop a party from cancelling the other's point.
"""

from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import Commitment, Settlement
from blockchainkit.channels.utils.scripts import (
    channel_message,
    derived_key,
    key_pair,
    revocable_locking,
    signature,
    two_of_two_locking,
    two_of_two_unlocking,
)
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.curves import SECP256K1, add, public_key
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.systems.hash_chain import hash_chain
from blockchainkit.vm.systems.script import ScriptItem, encode_signature, verify_script


def _scalar(secret: bytes) -> int:
    return int.from_bytes(secret, "big") % (SECP256K1.order - 1) + 1


class LightningChannel:
    """A two-party Poon-Dryja channel.

    Parameters
    ----------
    parties : tuple of str
        The two parties; the first funds ``deposits[0]``, the second ``deposits[1]``.
    keys : tuple of int
        Their private funding keys; revocation, delayed and per-commitment
        keys are derived from them.
    deposits : tuple of int
        Each party's initial balance.
    delay : int
        Blocks a commitment's holder must wait before taking its own output.
    max_states : int
        Length of each party's per-commitment hash chain.

    Examples
    --------
    >>> from blockchainkit.channels import LightningChannel
    >>> channel = LightningChannel(("alice", "bob"), (7, 5), (100, 0), delay=6)
    >>> channel.pay("alice", 30), channel.pay("alice", 20)
    (1, 2)
    >>> _ = channel.publish("alice", state=0, height=100)  # Alice cheats with state 0.
    >>> dict(channel.penalize(height=103).payouts)
    {'alice': 0, 'bob': 100}
    """

    def __init__(
        self,
        parties: tuple[str, str],
        keys: tuple[int, int],
        deposits: tuple[int, int],
        *,
        delay: int = 144,
        max_states: int = 1_000,
    ) -> None:
        if len(set(parties)) != 2:
            raise ValueError("a channel needs two distinct parties")
        for deposit in deposits:
            integer(deposit, "deposit")
        if sum(deposits) == 0:
            raise ValueError("the channel must be funded")
        integer(delay, "delay", 1)
        integer(max_states, "max_states", 2)
        self.parties = parties
        self.delay, self.max_states = delay, max_states
        self._keys = dict(zip(parties, keys, strict=True))
        publics = [key_pair(key, "key")[1] for key in keys]
        self.funding: tuple[ScriptItem, ...] = two_of_two_locking(*publics)
        self.id = sha256(channel_message("lightning", list(parties), [list(p) for p in publics]))
        self._base = {p: derived_key(k, "revocation-base") for p, k in self._keys.items()}
        self._delayed = {p: derived_key(k, "delayed") for p, k in self._keys.items()}
        self._chains = {
            p: hash_chain(sha256(channel_message("shachain", self.id.hex(), p, k)), max_states)
            for p, k in self._keys.items()
        }
        self.state = 0
        self.balances = dict(zip(parties, deposits, strict=True))
        self._revealed: dict[str, bytes] = {}  # Holder -> its latest revealed secret.
        self._signed: dict[tuple[str, int], tuple[Commitment, SchnorrSignature]] = {}
        self._sign_commitments()
        self.published: tuple[Commitment, int] | None = None
        self.settlement: Settlement | None = None

    # Keys -------------------------------------------------------------------

    def other(self, party: str) -> str:
        """The counterparty of ``party``."""
        if party not in self.parties:
            raise ValueError(f"{party!r} is not a party to the channel")
        return self.parties[1] if party == self.parties[0] else self.parties[0]

    def _secret(self, holder: str, state: int) -> bytes:
        return self._chains[holder][self.max_states - 1 - state]

    def revocation_key(self, holder: str, state: int) -> tuple[int, int]:
        """``R = S + B``: the holder's per-commitment point plus the counterparty's base point."""
        point = public_key(_scalar(self._secret(holder, state)))
        revocation = add(point, public_key(self._base[self.other(holder)]), SECP256K1)
        assert revocation is not None  # S = -B has negligible probability.
        return revocation

    def derive_secret(self, holder: str, state: int) -> bytes | None:
        """The per-commitment secret of the holder's ``state``, if the counterparty can derive it.

        It can for every revoked state: it hashes the latest revealed secret
        once per state back.
        """
        latest = self._revealed.get(holder)
        if latest is None or state >= self.state:
            return None
        for _ in range(self.state - 1 - state):
            latest = sha256(latest)
        return latest

    # Off chain --------------------------------------------------------------

    def commitment(self, holder: str, state: int | None = None) -> Commitment:
        """The holder's commitment for ``state`` (the current one by default)."""
        state = self.state if state is None else state
        found = self._signed.get((holder, state))
        if found is None:
            raise ValueError(f"{holder} holds no commitment for state {state}")
        return found[0]

    def _sign_commitments(self) -> None:
        if self.state >= self.max_states:
            raise ValueError("the per-commitment hash chain is exhausted")
        for holder in self.parties:
            other = self.other(holder)
            to_local, to_remote = self.balances[holder], self.balances[other]
            revocation = self.revocation_key(holder, self.state)
            txid = sha256(
                channel_message(
                    "commitment",
                    self.id.hex(),
                    holder,
                    self.state,
                    to_local,
                    to_remote,
                    list(revocation),
                )
            )
            commitment = Commitment(holder, self.state, to_local, to_remote, revocation, txid)
            # The counterparty signs the holder's version and hands it over.
            self._signed[holder, self.state] = (commitment, signature(self._keys[other], txid))

    def pay(self, sender: str, amount: int) -> int:
        """Move ``amount`` from ``sender`` to the counterparty; return the new state number.

        Both parties sign each other's new commitment, then each revokes its
        previous one by revealing that commitment's per-commitment secret.
        """
        if self.published is not None:
            raise ValueError("the channel is closing")
        receiver = self.other(sender)
        integer(amount, "amount", 1)
        if amount > self.balances[sender]:
            raise ValueError("insufficient balance")
        self.balances[sender] -= amount
        self.balances[receiver] += amount
        self.state += 1
        self._sign_commitments()
        for holder in self.parties:
            self._revealed[holder] = self._secret(holder, self.state - 1)
        return self.state

    # On chain ---------------------------------------------------------------

    def close_cooperatively(self, *, height: int) -> Settlement:
        """Both parties sign a transaction paying the current balances, with no delay."""
        integer(height, "height")
        if self.published is not None:
            raise ValueError("a commitment has already been published")
        message = channel_message("close", self.id.hex(), self.state)
        first, second = (signature(self._keys[p], message) for p in self.parties)
        assert verify_script(
            two_of_two_unlocking(first, second), self.funding, message=message
        ).valid
        self.settlement = Settlement(
            "cooperative", MappingProxyType(dict(self.balances)), height, self.state
        )
        return self.settlement

    def publish(self, holder: str, *, state: int | None = None, height: int) -> Commitment:
        """The holder broadcasts one of its commitments, current or revoked.

        The holder adds its own signature to the counterparty's; the pair
        spends the 2-of-2 funding output.
        """
        integer(height, "height")
        if self.published is not None or self.settlement is not None:
            raise ValueError("the funding output is already spent")
        commitment = self.commitment(holder, state)
        counter_signature = self._signed[holder, commitment.state][1]
        own = signature(self._keys[holder], commitment.txid)
        by_party = {holder: own, self.other(holder): counter_signature}
        unlocking = two_of_two_unlocking(*(by_party[p] for p in self.parties))
        assert verify_script(unlocking, self.funding, message=commitment.txid).valid
        self.published = (commitment, height)
        return commitment

    def _to_local(self) -> tuple[Commitment, int, tuple[ScriptItem, ...]]:
        if self.published is None:
            raise ValueError("no commitment has been published")
        if self.settlement is not None:
            raise ValueError("the holder's output has already been claimed")
        commitment, at = self.published
        delayed = public_key(self._delayed[commitment.holder])
        return commitment, at, revocable_locking(commitment.revocation, delayed, self.delay)

    def _settle(self, kind: str, commitment: Commitment, height: int) -> Settlement:
        holder, other = commitment.holder, self.other(commitment.holder)
        local = commitment.to_local if kind == "unilateral" else 0
        payouts = {holder: local, other: commitment.to_remote + commitment.to_local - local}
        self.settlement = Settlement(
            kind, MappingProxyType({p: payouts[p] for p in self.parties}), height, commitment.state
        )
        return self.settlement

    def sweep(self, *, height: int) -> Settlement:
        """The holder takes its delayed output, once ``delay`` blocks have passed.

        Raises
        ------
        ValueError
            The delay has not passed, so Script rejects the spend.
        """
        integer(height, "height")
        commitment, at, lock = self._to_local()
        message = channel_message("sweep", commitment.txid.hex())
        unlocking = (
            encode_signature(signature(self._delayed[commitment.holder], message)),
            "OP_FALSE",
        )
        result = verify_script(unlocking, lock, message=message, locktime=max(height - at, 0))
        if not result.valid:
            raise ValueError(f"the holder's output is locked: {result.error}")
        return self._settle("unilateral", commitment, height)

    def justice_message(self, commitment: Commitment) -> bytes:
        """What the revocation key signs to take a revoked commitment's ``to_local``."""
        return channel_message("penalty", commitment.txid.hex())

    def justice_signature(self, holder: str, state: int) -> SchnorrSignature:
        """The counterparty's signature with the revocation key of the holder's revoked ``state``.

        It can be made in advance, and handed to a watchtower.

        Raises
        ------
        ValueError
            The state has not been revoked, so the counterparty lacks the secret.
        """
        secret = self.derive_secret(holder, state)
        if secret is None:
            raise ValueError(f"{holder}'s state {state} has not been revoked")
        private = (_scalar(secret) + self._base[self.other(holder)]) % SECP256K1.order
        return signature(private, self.justice_message(self.commitment(holder, state)))

    def penalize(self, *, height: int, justice: SchnorrSignature | None = None) -> Settlement:
        """The counterparty takes the holder's output of a revoked commitment.

        Parameters
        ----------
        height : int
            When the penalty is published; it must come before the holder's sweep.
        justice : SchnorrSignature, optional
            A presigned :meth:`justice_signature`, as a watchtower would publish.

        Raises
        ------
        ValueError
            The published commitment is the current one, so it cannot be revoked.
        """
        integer(height, "height")
        commitment, _, lock = self._to_local()
        if justice is None:
            justice = self.justice_signature(commitment.holder, commitment.state)
        unlocking = (encode_signature(justice), "OP_TRUE")
        message = self.justice_message(commitment)
        if not verify_script(unlocking, lock, message=message).valid:
            raise ValueError("the justice signature does not match the revocation key")
        return self._settle("penalty", commitment, height)
