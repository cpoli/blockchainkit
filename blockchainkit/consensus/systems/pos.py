"""Stake-weighted proposer sampling, not a complete PoS consensus protocol."""

from bisect import bisect_right
from collections.abc import Mapping
from itertools import accumulate
from random import Random

from blockchainkit._validation import integer


class StakeSampler:
    """Select proposers with exact integer weights and reproducible randomness.

    Parameters
    ----------
    stakes : Mapping
        Nonnegative weights with a positive total. Names are sorted so mapping
        insertion order does not alter results.
    seed : int
        Simulation seed, not an unpredictable consensus randomness beacon.

    Examples
    --------
    >>> from blockchainkit.consensus import StakeSampler
    >>> StakeSampler({"alice": 1, "bob": 0}, seed=7).sample(3)
    ('alice', 'alice', 'alice')
    """

    def __init__(self, stakes: Mapping[str, int], *, seed: int = 0) -> None:
        if not stakes or any(not isinstance(name, str) or not name for name in stakes):
            raise ValueError("provide nonempty validator names")
        for weight in stakes.values():
            integer(weight, "stake")
        self._stakes = tuple(sorted(stakes.items()))
        self._total = sum(stakes.values())
        if self._total == 0:
            raise ValueError("total stake must be positive")
        self._cumulative = tuple(accumulate(weight for _, weight in self._stakes))
        self._random = Random(seed)

    def choose(self) -> str:
        """Select one validator with probability stake / total stake."""
        ticket = self._random.randrange(self._total)
        # ticket < total guarantees an index inside the cumulative weights.
        # bisect_right skips repeated boundaries from zero-weight validators.
        return self._stakes[bisect_right(self._cumulative, ticket)][0]

    def sample(self, rounds: int) -> tuple[str, ...]:
        """Return proposers for a bounded number of rounds."""
        integer(rounds, "rounds")
        return tuple(self.choose() for _ in range(rounds))
