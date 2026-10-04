"""Result containers for blockchainkit.consensus."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blockchainkit.structures.systems.block import Block


@dataclass(frozen=True)
class MiningResult:
    """A successful mined block and the number of hashes attempted."""

    block: "Block"
    attempts: int
