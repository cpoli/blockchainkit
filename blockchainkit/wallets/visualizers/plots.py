"""Plotting helpers for blockchainkit.wallets: error detection, memory-hardness, and recovery."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from blockchainkit.wallets.core.base import DetectionRates, RomixCost
from blockchainkit.wallets.systems.social_recovery import recovery_risk

__all__ = ["plot_detection_rates", "plot_memory_tradeoff", "plot_recovery_risk"]


def plot_detection_rates(rates: Sequence[DetectionRates], *, ax: Axes | None = None) -> Axes:
    """Draw the share of single errors and adjacent swaps each check-digit scheme catches.

    Parameters
    ----------
    rates : sequence of DetectionRates
        From :func:`~blockchainkit.wallets.systems.check_digits.detection_rates`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not rates:
        raise ValueError("no schemes to plot")
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(rates))
    ax.bar(x - 0.2, [r.single_errors for r in rates], 0.4, color="#2563eb", label="single errors")
    ax.bar(x + 0.2, [r.transpositions for r in rates], 0.4, color="#dc2626", label="adjacent swaps")
    ax.set_xticks(x, [r.scheme for r in rates])
    ax.set(ylabel="share detected", ylim=(0, 1.25), yticks=[0, 0.25, 0.5, 0.75, 1])
    ax.set_title("What a check digit catches")
    ax.legend(loc="upper center", ncol=2)
    return ax


def plot_memory_tradeoff(costs: Sequence[RomixCost], *, ax: Axes | None = None) -> Axes:
    """Draw ROMix's time against the memory kept, with the curve of constant memory times time.

    Parameters
    ----------
    costs : sequence of RomixCost
        From :func:`~blockchainkit.wallets.systems.scrypt.romix` with
        different ``keep_every``, the same ``n`` and ``r``.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not costs:
        raise ValueError("no runs to plot")
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    memory = np.array([c.memory for c in costs], dtype=float)
    time = np.array([c.block_mixes for c in costs], dtype=float)
    ax.loglog(memory, time, "o", color="#2563eb", label="ROMix runs")
    best = min(costs, key=lambda c: c.memory * c.block_mixes)
    span = np.geomspace(memory.min(), memory.max(), 50)
    ax.loglog(
        span,
        best.memory * best.block_mixes / span,
        color="#64748b",
        linestyle="--",
        label="memory x time constant",
    )
    ax.set(xlabel="memory kept (bytes)", ylabel="BlockMix calls")
    ax.set_title(f"scrypt's trade-off, N = {best.n}")
    ax.legend()
    return ax


def plot_recovery_risk(
    guardians: int, lost: float, corrupt: float, *, ax: Axes | None = None
) -> Axes:
    """Draw lockout and theft probabilities against the guardian threshold m.

    Parameters
    ----------
    guardians : int
        n, the number of guardians.
    lost, corrupt : float
        Each guardian's probability of being unreachable or corrupt.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    thresholds = np.arange(1, guardians + 1)
    risks = [recovery_risk(guardians, int(m), lost, corrupt) for m in thresholds]
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(thresholds, [r.lockout for r in risks], "o-", color="#2563eb", label="lockout")
    ax.semilogy(thresholds, [r.theft for r in risks], "o-", color="#dc2626", label="theft")
    ax.axhline(lost, color="#2563eb", linestyle=":", label="one seed phrase: lost")
    ax.axhline(corrupt, color="#dc2626", linestyle=":", label="one seed phrase: stolen")
    ax.set(xlabel="threshold m", ylabel="probability", xticks=thresholds)
    ax.set_title(f"{guardians} guardians")
    ax.legend()
    return ax
