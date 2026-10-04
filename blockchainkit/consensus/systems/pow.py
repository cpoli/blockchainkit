"""Bounded proof-of-work experiments with explicit success probabilities."""

from dataclasses import replace
from typing import TYPE_CHECKING

from blockchainkit._validation import integer
from blockchainkit.consensus.core.base import MiningResult
from blockchainkit.constants import UINT64_LIMIT
from blockchainkit.crypto.systems.hashing import sha256

if TYPE_CHECKING:
    from blockchainkit.structures.systems.block import Block


def target(difficulty: int) -> int:
    """Return the inclusive target for a leading-zero-bit difficulty.

    >>> from blockchainkit.consensus import target
    >>> target(0) == 2**256 - 1
    True
    """
    integer(difficulty, "difficulty")
    if difficulty > 256:
        raise ValueError("difficulty cannot exceed 256")
    return (1 << (256 - difficulty)) - 1


def expected_trials(difficulty: int) -> int:
    """Return 2**difficulty, assuming independent uniform 256-bit hashes."""
    target(difficulty)
    return 1 << difficulty


def valid_pow(block: "Block") -> bool:
    """Check that the block hash, interpreted big-endian, is at most its target."""
    return int.from_bytes(block.hash, "big") <= target(block.difficulty)


def mine(block: "Block", *, max_attempts: int = 100_000) -> MiningResult:
    """Search sequential nonces starting at block.nonce, with a strict bound.

    Raises
    ------
    TimeoutError
        No solution was found within max_attempts (not evidence of no solution).
    ValueError
        The search would exceed the 64-bit nonce space.
    """
    integer(max_attempts, "max_attempts", 1)
    if block.nonce + max_attempts > UINT64_LIMIT:
        raise ValueError("search exceeds the 64-bit nonce space")
    limit = target(block.difficulty)
    # Only the header changes between attempts; the Merkle root is computed once.
    for attempt in range(max_attempts):
        nonce = block.nonce + attempt
        if int.from_bytes(sha256(block.header(nonce=nonce)), "big") <= limit:
            return MiningResult(replace(block, nonce=nonce), attempt + 1)
    raise TimeoutError(f"no solution in {max_attempts} attempts")
