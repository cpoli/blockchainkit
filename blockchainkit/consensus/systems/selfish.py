"""Selfish mining (Eyal and Sirer 2014): majority is not enough.

A pool that withholds the blocks it finds, and publishes them only to
overtake or tie the honest chain, wastes the honest miners' work. Above a
threshold hashrate its share of the chain exceeds its share of the hashrate,
so honest miners gain by joining it. ``gamma`` is the fraction of honest
miners who build on the pool's block during a tie.
"""

from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.consensus.core.base import SelfishMiningResult


def _check(alpha: float, gamma: float) -> None:
    if not 0 < alpha < 0.5:
        raise ValueError("alpha must be in (0, 0.5)")
    if not 0 <= gamma <= 1:
        raise ValueError("gamma must be in [0, 1]")


def selfish_mining_revenue(alpha: float, gamma: float) -> float:
    """Return the selfish pool's long-run share of blocks (Eyal and Sirer, eq. 8).

    ``R = (alpha (1-alpha)**2 (4 alpha + gamma (1 - 2 alpha)) - alpha**3)
    / (1 - alpha (1 + (2 - alpha) alpha))``

    >>> from blockchainkit.consensus import selfish_mining_revenue
    >>> round(selfish_mining_revenue(0.4, 0.0), 3)
    0.484
    """
    _check(alpha, gamma)
    a = alpha
    numerator = a * (1 - a) ** 2 * (4 * a + gamma * (1 - 2 * a)) - a**3
    return float(numerator / (1 - a * (1 + (2 - a) * a)))


def selfish_mining_threshold(gamma: float) -> float:
    """Return the hashrate above which selfish mining pays: ``(1 - gamma) / (3 - 2 gamma)``."""
    if not 0 <= gamma <= 1:
        raise ValueError("gamma must be in [0, 1]")
    return (1 - gamma) / (3 - 2 * gamma)


def simulate_selfish_mining(
    alpha: float, gamma: float, *, blocks: int, seed: int = 0
) -> SelfishMiningResult:
    """Simulate the selfish-mining state machine (Eyal and Sirer, Algorithm 1).

    Each event, the pool finds a block with probability alpha, otherwise the
    honest network does. The state is the pool's private lead, plus a tie
    state after the pool publishes to match an honest block.
    """
    _check(alpha, gamma)
    integer(blocks, "blocks", 1)
    check_seed(seed)
    rng = Random(seed)
    lead, tie, selfish, honest = 0, False, 0, 0
    for _ in range(blocks):
        pool_found = rng.random() < alpha
        if tie:
            if pool_found:
                selfish += 2  # The pool extends its own branch and wins both blocks.
            elif rng.random() < gamma:
                selfish, honest = selfish + 1, honest + 1  # Honest block on the pool's branch.
            else:
                honest += 2  # Honest block on the honest branch.
            tie = False
        elif pool_found:
            lead += 1
        elif lead == 0:
            honest += 1
        elif lead == 1:
            lead, tie = 0, True  # Publish and race.
        elif lead == 2:
            lead, selfish = 0, selfish + 2  # Publish both and orphan the honest block.
        else:
            lead, selfish = lead - 1, selfish + 1  # Reveal one block; stay ahead.
    return SelfishMiningResult(selfish, honest, selfish / max(1, selfish + honest))
