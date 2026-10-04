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


@dataclass(frozen=True)
class GeneralsResult:
    """Outcome of an oral-messages run.

    Attributes
    ----------
    decisions : dict
        Each loyal lieutenant's decision.
    agreement : bool
        All loyal lieutenants decided the same (condition IC1).
    validity : bool
        If the commander is loyal, every loyal lieutenant followed its order
        (condition IC2); vacuously true for a traitorous commander.
    """

    decisions: dict[int, str]
    agreement: bool
    validity: bool


@dataclass(frozen=True)
class ConsensusRun:
    """Outcome of a randomized-consensus run: who decided what, after how many rounds."""

    decisions: dict[int, int]
    rounds: int
    decided: bool


@dataclass(frozen=True)
class ViewChangeRun:
    """Views tried under partial synchrony, until the first one that made progress."""

    view_starts: tuple[int, ...]
    timeouts: tuple[int, ...]
    decided_view: int
    decision_time: int


@dataclass(frozen=True)
class SquareRootResult:
    """A modular square root and the multiplications spent computing it."""

    root: int
    multiplications: int


@dataclass(frozen=True)
class PBFTResult:
    """Values each honest replica prepared and committed (None if it did not)."""

    prepared: dict[int, str | None]
    commits: dict[int, str | None]


@dataclass(frozen=True)
class DifficultyRun:
    """Simulated block intervals and the target in force for each block."""

    block_times: tuple[float, ...]
    targets: tuple[int, ...]


@dataclass(frozen=True)
class SelfishMiningResult:
    """Blocks each side contributed to the final chain, and the pool's share."""

    selfish_blocks: int
    honest_blocks: int
    revenue: float


@dataclass(frozen=True)
class Offense:
    """Two votes by one validator that violate a Casper slashing condition."""

    validator: str
    kind: str
    first: tuple[int, int, bytes]
    second: tuple[int, int, bytes]
