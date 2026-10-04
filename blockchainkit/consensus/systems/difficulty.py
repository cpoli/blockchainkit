"""Difficulty retargeting (Bitcoin 2009): hold the block interval steady as hashrate changes.

The whitepaper (section 4) says proof-of-work difficulty is set by a moving
average targeting an average number of blocks per hour. Bitcoin's first
release recomputes the target every 2016 blocks, scaling it by the ratio of
actual to expected time, clamped to a factor of four in either direction.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.consensus.core.base import DifficultyRun

_SCALE = 2**48


def retarget(target: int, actual_time: int, expected_time: int) -> int:
    """Return ``target * actual / expected``, clamped to ``[target/4, 4*target]``.

    A larger target is easier. Blocks that came too fast shrink it.

    >>> from blockchainkit.consensus import retarget
    >>> retarget(1000, actual_time=600, expected_time=1200)
    500
    """
    integer(target, "target", 1)
    integer(actual_time, "actual_time", 1)
    integer(expected_time, "expected_time", 1)
    clamped = min(max(actual_time, expected_time // 4), expected_time * 4)
    return max(1, target * clamped // expected_time)


def simulate_difficulty(
    hashrates: Sequence[float], *, interval: int = 600, window: int = 2016, seed: int = 0
) -> DifficultyRun:
    """Simulate block discovery with exponential waiting times and periodic retargets.

    With target T, a block needs about ``2**48 / T`` hashes on average, so at
    hashrate h its waiting time is exponential with mean ``2**48 / (T h)``.

    Parameters
    ----------
    hashrates : sequence of float
        The network hashrate while each successive block is mined.
    interval : int
        The target block time, in seconds.
    window : int
        Blocks between retargets.
    seed : int
        Seed for the waiting times.

    Returns
    -------
    DifficultyRun
        Each block's waiting time and the target it was mined under.
    """
    integer(interval, "interval", 1)
    integer(window, "window", 1)
    check_seed(seed)
    if not hashrates or any(h <= 0 for h in hashrates):
        raise ValueError("hashrates must be positive")
    rng = Random(seed)
    target = max(1, round(_SCALE / (interval * hashrates[0])))
    times: list[float] = []
    targets: list[int] = []
    for height, rate in enumerate(hashrates):
        targets.append(target)
        times.append(rng.expovariate(target * rate / _SCALE))
        if (height + 1) % window == 0:
            actual = max(1, round(sum(times[-window:])))
            target = retarget(target, actual, interval * window)
    return DifficultyRun(tuple(times), tuple(targets))
