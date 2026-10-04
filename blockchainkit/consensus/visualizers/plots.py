"""Plotting helpers for blockchainkit.consensus: mining effort and stake weighting."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

__all__ = ["plot_mining_trials", "plot_stake_shares"]


def plot_mining_trials(
    difficulties: Sequence[int], attempts: Sequence[int], ax: Axes | None = None
) -> Axes:
    """Compare measured hash attempts with the expected 2**difficulty.

    Parameters
    ----------
    difficulties : sequence of int
        Difficulty of each mined block.
    attempts : sequence of int
        Hash attempts each search needed (``MiningResult.attempts``).
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if len(difficulties) != len(attempts):
        raise ValueError("difficulties and attempts must have the same length")
    if ax is None:
        _, ax = plt.subplots()
    ax.scatter(difficulties, attempts, color="#2563eb", alpha=0.6, label="measured")
    grid = np.arange(min(difficulties), max(difficulties) + 1)
    ax.plot(grid, 2.0**grid, color="black", label="expected 2^d")
    ax.set_yscale("log", base=2)
    ax.set_xlabel("difficulty d (leading zero bits)")
    ax.set_ylabel("hash attempts")
    ax.set_title("Each extra zero bit doubles the expected work")
    ax.legend()
    return ax


def plot_stake_shares(
    stakes: Mapping[str, int], proposers: Sequence[str], ax: Axes | None = None
) -> Axes:
    """Compare each validator's stake fraction with its observed proposer fraction.

    Parameters
    ----------
    stakes : Mapping
        Validator weights, as given to :class:`~blockchainkit.consensus.StakeSampler`.
    proposers : sequence of str
        Sampled proposers, e.g. from ``StakeSampler.sample``.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not proposers:
        raise ValueError("need at least one sampled proposer")
    if ax is None:
        _, ax = plt.subplots()
    names = sorted(stakes)
    total = sum(stakes.values())
    counts = Counter(proposers)
    xs = np.arange(len(names))
    ax.bar(xs - 0.18, [stakes[n] / total for n in names], 0.36, label="stake fraction")
    ax.bar(xs + 0.18, [counts[n] / len(proposers) for n in names], 0.36, label="proposer fraction")
    ax.set_xticks(xs, names)
    ax.set_ylabel("fraction")
    ax.set_title(f"Stake-weighted selection over {len(proposers)} rounds")
    ax.legend()
    return ax
