"""Bounded proof-of-work experiments with explicit success probabilities."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from blockchainkit.crypto.number_theory import integer

if TYPE_CHECKING:
    from blockchainkit.structures.block import Block


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


@dataclass(frozen=True)
class MiningResult:
    """A successful mined block and the number of hashes attempted."""

    block: "Block"
    attempts: int


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
    if block.nonce + max_attempts > 2**64:
        raise ValueError("search exceeds the 64-bit nonce space")
    for attempt in range(max_attempts):
        candidate = replace(block, nonce=block.nonce + attempt)
        if valid_pow(candidate):
            return MiningResult(candidate, attempt + 1)
    raise TimeoutError(f"no solution in {max_attempts} attempts")


def eventual_catch_up(attacker_fraction: float, deficit: int) -> float:
    """Return eventual catch-up probability in an ideal infinite random walk.

    For q<1/2 this is (q/(1-q))**deficit. This is NOT Nakamoto's finite-
    confirmation Poisson model: there is no propagation delay or time bound.

    >>> from blockchainkit.consensus import eventual_catch_up
    >>> eventual_catch_up(0.25, 2)
    0.1111111111111111
    """
    if not 0 <= attacker_fraction <= 1:
        raise ValueError("attacker_fraction must be in [0, 1]")
    integer(deficit, "deficit")
    if deficit == 0 or attacker_fraction >= 0.5:
        return 1.0
    return (attacker_fraction / (1 - attacker_fraction)) ** deficit
