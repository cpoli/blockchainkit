"""Result containers for blockchainkit.structures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MerkleProof:
    """Leaf position, leaf count, and bottom-up siblings (None for promotion)."""

    index: int
    leaf_count: int
    siblings: tuple[bytes | None, ...]
