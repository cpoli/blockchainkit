"""One-way micropayment channels (Spilman and Hearn, 2013).

Paying a few satoshis per second of a service on chain would cost more in
fees than the payments themselves. Jeremy Spilman's channel moves them off
chain. The payer locks the channel's capacity in an output that needs both
parties' signatures, after the payee has signed a *refund* that returns
everything to the payer once a lock time has passed. Each payment is a new
transaction from that output, paying a little more to the payee, which the
payer signs and hands over; the payee countersigns only the last one and
publishes it before the refund becomes valid. Mike Hearn implemented the
scheme in bitcoinj the same year.

The payee can take no more than the payer signed, and the payer can never
take back what it paid, because the payee holds a signed transaction for
it; the refund only protects the payer from a payee who disappears.
"""

from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import Settlement
from blockchainkit.channels.utils.scripts import (
    channel_message,
    key_pair,
    signature,
    two_of_two_locking,
    two_of_two_unlocking,
)
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.vm.systems.script import ScriptItem, verify_script


class SpilmanChannel:
    """A unidirectional payment channel from ``payer`` to ``payee``.

    Parameters
    ----------
    payer, payee : str
        Names used in the settlement.
    payer_key, payee_key : int
        The parties' private keys.
    capacity : int
        Coins locked in the 2-of-2 funding output.
    expiry : int
        The refund's lock time: from this height the payer can take everything back.

    Examples
    --------
    >>> from blockchainkit.channels import SpilmanChannel
    >>> channel = SpilmanChannel("alice", "bob", payer_key=7, payee_key=5, capacity=100, expiry=50)
    >>> channel.pay(10), channel.pay(15)
    (10, 25)
    >>> dict(channel.close(height=20).payouts)
    {'alice': 75, 'bob': 25}
    """

    def __init__(
        self,
        payer: str,
        payee: str,
        *,
        payer_key: int,
        payee_key: int,
        capacity: int,
        expiry: int,
    ) -> None:
        if payer == payee:
            raise ValueError("payer and payee must differ")
        integer(capacity, "capacity", 1)
        integer(expiry, "expiry", 1)
        self.payer, self.payee = payer, payee
        self.capacity, self.expiry = capacity, expiry
        self._payer_key, payer_public = key_pair(payer_key, "payer_key")
        self._payee_key, payee_public = key_pair(payee_key, "payee_key")
        self.funding: tuple[ScriptItem, ...] = two_of_two_locking(payer_public, payee_public)
        self.id = sha256(channel_message("spilman", payer, payee, capacity, list(payer_public)))
        # The payee signs the refund first; only then does the payer fund the channel.
        self._refund_signature = signature(payee_key, self._message(0, expiry))
        self.paid = 0
        self.payments = 0
        self._latest: SchnorrSignature | None = None
        self.settlement: Settlement | None = None

    def _message(self, paid: int, locktime: int) -> bytes:
        return channel_message("spilman", self.id.hex(), paid, locktime)

    def _open(self) -> None:
        if self.settlement is not None:
            raise ValueError("the channel is closed")

    def pay(self, amount: int) -> int:
        """Sign a new transaction paying ``amount`` more to the payee; return the total paid."""
        self._open()
        integer(amount, "amount", 1)
        if self.paid + amount > self.capacity:
            raise ValueError("payment exceeds the channel's capacity")
        self.paid += amount
        self.payments += 1
        self._latest = signature(self._payer_key, self._message(self.paid, 0))
        return self.paid

    def _spend(self, payer_signature: SchnorrSignature, message: bytes) -> None:
        payee_signature = signature(self._payee_key, message)
        unlocking = two_of_two_unlocking(payer_signature, payee_signature)
        result = verify_script(unlocking, self.funding, message=message)
        assert result.valid  # Both signatures are over the message just signed.

    def close(self, *, height: int) -> Settlement:
        """The payee countersigns the latest payment and publishes it."""
        self._open()
        integer(height, "height")
        if self._latest is None:
            raise ValueError("nothing has been paid")
        self._spend(self._latest, self._message(self.paid, 0))
        payouts = {self.payer: self.capacity - self.paid, self.payee: self.paid}
        self.settlement = Settlement(
            "cooperative", MappingProxyType(payouts), height, self.payments
        )
        return self.settlement

    def refund(self, *, height: int) -> Settlement:
        """The payer publishes the refund, which a block accepts only from ``expiry`` on."""
        self._open()
        integer(height, "height")
        if height < self.expiry:
            raise ValueError(f"the refund is locked until height {self.expiry}")
        message = self._message(0, self.expiry)
        payer_signature = signature(self._payer_key, message)
        unlocking = two_of_two_unlocking(payer_signature, self._refund_signature)
        assert verify_script(unlocking, self.funding, message=message).valid
        self.settlement = Settlement(
            "refund", MappingProxyType({self.payer: self.capacity, self.payee: 0}), height, 0
        )
        return self.settlement
