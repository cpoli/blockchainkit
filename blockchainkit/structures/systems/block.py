"""Immutable blocks with canonical headers and transaction commitments."""

from dataclasses import dataclass
from functools import cached_property

from blockchainkit._validation import integer
from blockchainkit.constants import UINT64_LIMIT
from blockchainkit.crypto import sha256
from blockchainkit.structures.systems.merkle import MerkleTree
from blockchainkit.structures.systems.transaction import Transaction
from blockchainkit.structures.utils.encoding import canonical_json


def _check_uint64(value: int, name: str) -> None:
    integer(value, name)
    if value >= UINT64_LIMIT:
        raise ValueError(f"{name} must fit an unsigned 64-bit integer")


@dataclass(frozen=True)
class BlockHeader:
    """The 80-byte-style summary a light client downloads instead of a block.

    It commits to the block's transactions through ``merkle_root`` alone, so
    its hash, and therefore its proof of work, can be checked without them.
    ``Block.to_header().hash == Block.hash``.

    Parameters
    ----------
    previous_hash, merkle_root : bytes
        32-byte digests.
    height, timestamp, difficulty, nonce : int
        As for :class:`Block`.
    """

    previous_hash: bytes = bytes(32)
    merkle_root: bytes = bytes(32)
    height: int = 0
    timestamp: int = 0
    difficulty: int = 8
    nonce: int = 0

    def __post_init__(self) -> None:
        for name in ("previous_hash", "merkle_root"):
            value = getattr(self, name)
            if not isinstance(value, bytes) or len(value) != 32:
                raise ValueError(f"{name} must be 32 bytes")
        for name in ("height", "timestamp", "nonce", "difficulty"):
            _check_uint64(getattr(self, name), name)
        if self.difficulty > 256:
            raise ValueError("difficulty cannot exceed 256 bits")

    def encode(self) -> bytes:
        """Return the canonical bytes that are hashed."""
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

    @cached_property
    def hash(self) -> bytes:
        """Return SHA-256 of the canonical header."""
        return sha256(self.encode())


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

    Notes
    -----
    The Merkle root and the block hash are computed once and cached. A
    miner never rebuilds the transaction tree: it calls ``header(nonce=...)``
    with candidate nonces, as real miners vary only the header.
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
            _check_uint64(getattr(self, name), name)
        if self.difficulty > 256:
            raise ValueError("difficulty cannot exceed 256 bits")

    @cached_property
    def merkle_root(self) -> bytes:
        """Return the count-bound commitment to ordered signed transactions."""
        return MerkleTree(tx.to_bytes() for tx in self.transactions).root

    def header(self, nonce: int | None = None) -> bytes:
        """Return canonical bytes committing to all consensus-relevant fields.

        Parameters
        ----------
        nonce : int, optional
            A candidate nonce to place in the header instead of ``self.nonce``.
            ``block.header(nonce=n)`` equals ``replace(block, nonce=n).header()``
            without rebuilding the Merkle tree.
        """
        return self.to_header(nonce).encode()

    def to_header(self, nonce: int | None = None) -> BlockHeader:
        """Return this block's header, optionally with a candidate nonce."""
        return BlockHeader(
            self.previous_hash,
            self.merkle_root,
            self.height,
            self.timestamp,
            self.difficulty,
            self.nonce if nonce is None else nonce,
        )

    @cached_property
    def hash(self) -> bytes:
        """Return SHA-256 of the canonical header."""
        return sha256(self.header())
