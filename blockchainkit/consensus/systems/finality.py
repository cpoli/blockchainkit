"""Casper the Friendly Finality Gadget (Buterin and Griffith 2017).

Validators with deposits vote for links between checkpoints, ``source ->
target``. A checkpoint becomes *justified* when two thirds of the stake vote
for a link to it from a justified source, and its source becomes *finalized*
when the target is the very next checkpoint. Two slashing conditions make
conflicting finality cost at least a third of all stake: never cast two
different votes for the same target height, and never cast a vote that
surrounds another.
"""

from collections.abc import Mapping

from blockchainkit._validation import integer
from blockchainkit.consensus.core.base import Offense

Vote = tuple[int, int, bytes]


class FinalityGadget:
    """Track Casper FFG votes, justification, finality, and slashable offenses.

    Checkpoint 0 (genesis) starts justified and finalized.

    Parameters
    ----------
    stakes : Mapping
        Each validator's deposit.

    Examples
    --------
    >>> from blockchainkit.consensus import FinalityGadget
    >>> ffg = FinalityGadget({"a": 1, "b": 1, "c": 1})
    >>> for v in "abc":
    ...     ffg.vote(v, source=0, target=1)
    >>> sorted(ffg.justified)
    [0, 1]
    """

    def __init__(self, stakes: Mapping[str, int]) -> None:
        for weight in stakes.values():
            integer(weight, "stake", 1)
        self._stakes = dict(stakes)
        self._total = sum(self._stakes.values())
        self._votes: dict[str, list[Vote]] = {v: [] for v in self._stakes}
        self._justified, self._finalized = {0}, {0}
        self._offenses: list[Offense] = []

    @property
    def justified(self) -> frozenset[int]:
        """Heights of justified checkpoints."""
        return frozenset(self._justified)

    @property
    def finalized(self) -> frozenset[int]:
        """Heights of finalized checkpoints."""
        return frozenset(self._finalized)

    @property
    def slashable(self) -> tuple[Offense, ...]:
        """Every pair of votes that breaks a slashing condition, in detection order."""
        return tuple(self._offenses)

    def vote(self, validator: str, source: int, target: int, checkpoint: bytes = b"") -> None:
        """Record a vote for the link ``source -> target`` and update finality.

        ``checkpoint`` distinguishes conflicting blocks at the same height.
        """
        if validator not in self._stakes:
            raise ValueError(f"unknown validator {validator!r}")
        integer(source, "source")
        integer(target, "target", source + 1)
        new = (source, target, checkpoint)
        for old in self._votes[validator]:
            if old == new:
                return
            if old[1] == target:
                self._offenses.append(Offense(validator, "double vote", old, new))
            elif old[0] < source and target < old[1] or source < old[0] and old[1] < target:
                self._offenses.append(Offense(validator, "surround vote", old, new))
        self._votes[validator].append(new)
        if source not in self._justified:
            return
        support = sum(
            self._stakes[v]
            for v, votes in self._votes.items()
            if any(vote == new for vote in votes)
        )
        if 3 * support >= 2 * self._total:
            self._justified.add(target)
            if target == source + 1:
                self._finalized.add(source)
