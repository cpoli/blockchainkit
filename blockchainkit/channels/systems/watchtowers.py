"""Watchtowers, and PISA's accountable ones (McCorry, Bakshi, Bentov, Meiklejohn and Miller, 2019).

A Lightning party who goes offline for longer than the channel's delay can
be robbed: the counterparty publishes a revoked commitment and sweeps it
before anyone penalizes it. A *watchtower* watches the chain on the
party's behalf. After every update the party hands it an *appointment*:
the first half of the revoked commitment's txid as a hint, and a presigned
penalty transaction encrypted with a key derived from the whole txid. The
tower learns nothing about the channel until the revoked commitment
actually appears on chain, and then it can decrypt and publish only a
penalty that pays the party.

Nothing obliges such a tower to act. PISA makes it accountable: the tower
signs a *receipt* for each appointment and locks a deposit in a contract;
if a revoked state is swept while the receipt was valid, the party shows
the receipt and claims the deposit. PISA's arbitration contract judges
state channels in general; here the recourse is a function judging one
Lightning channel's outcome.
"""

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import AppointmentReceipt, Settlement
from blockchainkit.channels.systems.lightning import LightningChannel
from blockchainkit.channels.utils.scripts import key_pair, signature
from blockchainkit.constants import WATCHTOWER_DOMAIN
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.one_time_pad import one_time_pad
from blockchainkit.crypto.systems.signatures import verify
from blockchainkit.vm.systems.script import encode_signature

_HINT = 16


def _keystream(txid: bytes, length: int) -> bytes:
    blocks = (length + 31) // 32
    stream = b"".join(
        sha256(WATCHTOWER_DOMAIN + txid + i.to_bytes(4, "big")) for i in range(blocks)
    )
    return stream[:length]


def _decode_signature(data: bytes) -> SchnorrSignature:
    x, y, response = (int.from_bytes(data[i : i + 32], "big") for i in (1, 33, 65))
    return SchnorrSignature((x, y), response)


def make_appointment(channel: LightningChannel, customer: str, state: int) -> tuple[bytes, bytes]:
    """The ``(hint, blob)`` a customer gives a tower for the counterparty's revoked ``state``.

    Examples
    --------
    >>> from blockchainkit.channels import LightningChannel, make_appointment
    >>> channel = LightningChannel(("alice", "bob"), (7, 5), (100, 0), delay=6)
    >>> _ = channel.pay("alice", 40)
    >>> hint, blob = make_appointment(channel, "bob", 0)  # Bob guards against Alice's state 0.
    >>> len(hint), len(blob)
    (16, 97)
    """
    holder = channel.other(customer)
    txid = channel.commitment(holder, state).txid
    penalty = encode_signature(channel.justice_signature(holder, state))
    return txid[:_HINT], one_time_pad(penalty, _keystream(txid, len(penalty)))


def receipt_message(hint: bytes, expires: int) -> bytes:
    """The bytes a tower signs to accept an appointment."""
    return WATCHTOWER_DOMAIN + b"receipt" + hint + expires.to_bytes(8, "big")


class Watchtower:
    """A tower that stores encrypted penalties and publishes them when a hint matches.

    Parameters
    ----------
    key : int
        The tower's private key, which signs receipts.
    collateral : int
        The deposit a customer can claim if the tower fails it (PISA).
    online : bool
        False models a tower that is down, or that does not keep its promise.
    """

    def __init__(self, key: int, *, collateral: int = 0, online: bool = True) -> None:
        integer(collateral, "collateral")
        self._key, self.public_key = key_pair(key, "key")
        self.collateral, self.online = collateral, online
        self.appointments: dict[bytes, tuple[bytes, int]] = {}

    def appoint(self, hint: bytes, blob: bytes, *, expires: int) -> AppointmentReceipt:
        """Store an appointment until ``expires`` and return the signed receipt."""
        integer(expires, "expires")
        if len(hint) != _HINT:
            raise ValueError(f"a hint is {_HINT} bytes")
        self.appointments[hint] = (blob, expires)
        signed = signature(self._key, receipt_message(hint, expires))
        return AppointmentReceipt(self.public_key, hint, expires, signed)

    def watch(self, channel: LightningChannel, *, height: int) -> Settlement | None:
        """Look at the chain; if a watched commitment is there, publish its penalty."""
        integer(height, "height")
        if not self.online or channel.published is None or channel.settlement is not None:
            return None
        txid = channel.published[0].txid
        found = self.appointments.get(txid[:_HINT])
        if found is None or height > found[1]:
            return None
        blob = found[0]
        justice = _decode_signature(one_time_pad(blob, _keystream(txid, len(blob))))
        return channel.penalize(height=height, justice=justice)


def verify_receipt(receipt: AppointmentReceipt) -> bool:
    """True if the tower named in the receipt signed it."""
    message = receipt_message(receipt.hint, receipt.expires)
    return verify(message, receipt.signature, receipt.tower)


def tower_liable(receipt: AppointmentReceipt, channel: LightningChannel) -> bool:
    """PISA's recourse: True if the receipt's commitment was published in time and swept.

    The customer then claims the tower's collateral.
    """
    if not verify_receipt(receipt) or channel.published is None or channel.settlement is None:
        return False
    commitment, published_at = channel.published
    return (
        commitment.txid[:_HINT] == receipt.hint
        and published_at <= receipt.expires
        and channel.settlement.kind == "unilateral"
    )
