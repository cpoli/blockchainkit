"""Propagation delay and forks (Decker and Wattenhofer 2013).

A block takes time to reach the other miners. Until it arrives, they keep
mining on the old tip, and if one of them finds a block in that window the
chain forks. Block discovery is a Poisson process, so with propagation delay
``tau`` and mean block interval ``T`` the chance that a block is followed by a
competitor within ``tau`` is ``1 - exp(-tau / T)``. Shorter intervals or
slower relay mean more forks, wasted work, and an easier time for attackers.
"""

from math import exp
from random import Random

from blockchainkit._validation import integer, positive
from blockchainkit._validation import seed as check_seed


def fork_rate(delay: float, interval: float) -> float:
    """Probability that a competing block appears before a block has propagated.

    Parameters
    ----------
    delay : float
        Time for a block to reach the other miners.
    interval : float
        Mean time between blocks, in the same unit.

    Examples
    --------
    >>> from blockchainkit.network import fork_rate
    >>> round(fork_rate(12.6, 600), 4)
    0.0208
    """
    if isinstance(delay, bool) or not isinstance(delay, (int, float)):
        raise TypeError("delay must be a real number >= 0")
    if not 0 <= delay < float("inf"):
        raise ValueError("delay must be >= 0 and finite")
    positive(interval, "interval")
    return 1 - exp(-delay / interval)


def simulate_fork_rate(
    delay: float, interval: float, *, blocks: int = 10_000, seed: int = 0
) -> float:
    """Measure the fork rate on a simulated chain of Poisson block discoveries.

    Draws exponential gaps with mean ``interval`` between successive blocks
    and counts the blocks whose successor was found less than ``delay``
    later, when its miner could not yet have seen them.

    >>> from blockchainkit.network import simulate_fork_rate
    >>> simulate_fork_rate(0.0, 600, blocks=100)
    0.0
    """
    fork_rate(delay, interval)  # Validates both.
    integer(blocks, "blocks", 1)
    check_seed(seed)
    random = Random(seed)
    forks = sum(1 for _ in range(blocks) if random.expovariate(1 / interval) < delay)
    return forks / blocks
