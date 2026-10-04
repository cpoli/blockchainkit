"""Immutable signed account transfers and deterministic teaching encodings."""

from dataclasses import dataclass, replace

from blockchainkit._validation import integer
from blockchainkit.constants import DEFAULT_CHAIN_ID, UINT64_LIMIT
from blockchainkit.crypto import (
    SchnorrSignature,
    encode_point,
    public_key,
    sha256,
    sign,
    verify,
)
from blockchainkit.structures.utils.accounts import is_account_id
from blockchainkit.structures.utils.encoding import canonical_json


def address(public: tuple[int, int]) -> str:
    """Return SHA-256(uncompressed public key) as a 64-character account ID."""
    return sha256(encode_point(public)).hex()


@dataclass(frozen=True)
class Transaction:
    """An integer-valued transfer, signed over network ID and account nonce.

    Parameters
    ----------
    sender : tuple of int
        secp256k1 public point.
    recipient : str
        Lowercase 64-character hexadecimal account identifier.
    amount : int
        Positive integer units (no floating-point currency amounts).
    nonce : int
        Sender sequence number, starting at zero.
    chain_id : str
        Domain that prevents replay onto a different teaching network.
    signature : SchnorrSignature, optional
        Signature over the canonical unsigned payload.
    """

    sender: tuple[int, int]
    recipient: str
    amount: int
    nonce: int
    chain_id: str = DEFAULT_CHAIN_ID
    signature: SchnorrSignature | None = None

    def __post_init__(self) -> None:
        encode_point(self.sender)
        if not is_account_id(self.recipient):
            raise ValueError("recipient must be a lowercase SHA-256 account identifier")
        integer(self.amount, "amount", 1)
        integer(self.nonce, "nonce")
        if self.amount >= UINT64_LIMIT or self.nonce >= UINT64_LIMIT:
            raise ValueError("amount and nonce must fit unsigned 64-bit integers")
        if not isinstance(self.chain_id, str) or not 1 <= len(self.chain_id) <= 128:
            raise ValueError("chain_id must contain 1 to 128 characters")
        if self.signature is not None and not isinstance(self.signature, SchnorrSignature):
            raise TypeError("signature must be a SchnorrSignature or None")

    @property
    def sender_address(self) -> str:
        """Return the account identifier derived from the sender's public key."""
        return address(self.sender)

    def payload(self) -> bytes:
        """Return the exact bytes signed, including domain and format version."""
        return canonical_json(
            {
                "version": 1,
                "chain_id": self.chain_id,
                "sender": encode_point(self.sender).hex(),
                "recipient": self.recipient,
                "amount": self.amount,
                "nonce": self.nonce,
            }
        )

    def to_bytes(self) -> bytes:
        """Serialize the unsigned payload and signature without ambiguity."""
        signature = None
        if self.signature is not None:
            signature = [list(self.signature.commitment), self.signature.response]
        return canonical_json({"payload": self.payload().decode(), "signature": signature})

    @property
    def txid(self) -> bytes:
        """Return a digest of the signed transaction encoding."""
        return sha256(self.to_bytes())

    def is_valid(self) -> bool:
        """Check the signature; account balance and nonce are checked by Ledger."""
        return self.signature is not None and verify(self.payload(), self.signature, self.sender)

    def signed(self, private: int, *, signing_nonce: int | None = None) -> "Transaction":
        """Return a signed copy, checking that the key matches this sender."""
        if public_key(private) != self.sender:
            raise ValueError("private key does not match sender")
        return replace(self, signature=sign(self.payload(), private, nonce=signing_nonce))
