"""Immutable blocks with canonical headers and transaction commitments."""

from dataclasses import dataclass

from blockchainkit._validation import integer
from blockchainkit.constants import UINT64_LIMIT
from blockchainkit.crypto import sha256
from blockchainkit.structures.systems.merkle import MerkleTree
from blockchainkit.structures.systems.transaction import Transaction
from blockchainkit.structures.utils.encoding import canonical_json


@dataclass(frozen=True)
class Block:
    """A teaching block, not a Bitcoin/Ethereum wire-format block.

    Parameters
    ----------
    previous_hash : bytes
        Parent digest, or 32 zero bytes for genesis.
    transactions : tuple of Transaction
        Ordered signed transfers; copied into an immutable tuple.
    height, timestamp, nonce : int
        Nonnegative 64-bit integers; timestamps use simulation units.
    difficulty : int
        Number of required leading zero hash bits, between 0 and 256.
    """

    previous_hash: bytes = bytes(32)
    transactions: tuple[Transaction, ...] = ()
    height: int = 0
    timestamp: int = 0
    difficulty: int = 8
    nonce: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.previous_hash, bytes) or len(self.previous_hash) != 32:
            raise ValueError("previous_hash must be 32 bytes")
        object.__setattr__(self, "transactions", tuple(self.transactions))
        if any(not isinstance(tx, Transaction) for tx in self.transactions):
            raise TypeError("transactions must contain Transaction instances")
        for name in ("height", "timestamp", "nonce", "difficulty"):
            value = getattr(self, name)
            integer(value, name)
            if value >= UINT64_LIMIT:
                raise ValueError(f"{name} must fit an unsigned 64-bit integer")
        if self.difficulty > 256:
            raise ValueError("difficulty cannot exceed 256 bits")

    @property
    def merkle_root(self) -> bytes:
        """Return the count-bound commitment to ordered signed transactions."""
        return MerkleTree(tx.to_bytes() for tx in self.transactions).root

    def header(self) -> bytes:
        """Return canonical bytes committing to all consensus-relevant fields."""
        return canonical_json(
            {
                "version": 1,
                "previous_hash": self.previous_hash.hex(),
                "merkle_root": self.merkle_root.hex(),
                "height": self.height,
                "timestamp": self.timestamp,
                "difficulty": self.difficulty,
                "nonce": self.nonce,
            }
        )

    @property
    def hash(self) -> bytes:
        """Return SHA-256 of the canonical header."""
        return sha256(self.header())
