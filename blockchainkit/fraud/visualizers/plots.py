"""Plotting helpers for blockchainkit.fraud: Ponzi schemes, first digits, and price spikes."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from blockchainkit.fraud.core.base import BenfordTest, PonziRun

__all__ = ["plot_benford", "plot_ponzi", "plot_price_spikes"]


def plot_ponzi(run: PonziRun, *, ax: Axes | None = None) -> Axes:
    """Draw a Ponzi scheme's deposits and payouts per period, and the cash it holds.

    Parameters
    ----------
    run : PonziRun
        From :func:`~blockchainkit.fraud.systems.ponzi.simulate_ponzi` or
        :func:`~blockchainkit.fraud.systems.ponzi.simulate_lending_ponzi`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not run.deposits:
        raise ValueError("the run has no periods")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))
    periods = np.arange(len(run.deposits))
    ax.bar(periods - 0.2, run.deposits, width=0.4, color="#2563eb", label="new deposits")
    ax.bar(periods + 0.2, run.paid, width=0.4, color="#dc2626", label="paid out")
    ax.plot(periods, run.cash, color="black", marker=".", label="cash held")
    if run.collapse is not None:
        ax.axvline(run.collapse, color="#64748b", linestyle="--", label="collapse")
    ax.set(xlabel="period", ylabel="money")
    verdict = "survived" if run.survived else f"collapsed in period {run.collapse}"
    ax.set_title(f"Ponzi scheme: {verdict}")
    ax.legend()
    return ax


def plot_benford(test: BenfordTest, *, ax: Axes | None = None, label: str = "observed") -> Axes:
    """Draw the observed first-digit proportions against Benford's law.

    Parameters
    ----------
    test : BenfordTest
        From :func:`~blockchainkit.fraud.systems.benford.benford_test`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.
    label : str
        Legend label of the observed bars.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    digits = np.arange(1, 10)
    ax.bar(digits, test.proportions, color="#cbd5e1", edgecolor="#475569", label=label)
    ax.plot(digits, test.expected, "o-", color="#dc2626", label="Benford: log10(1 + 1/d)")
    ax.set(xlabel="first digit", ylabel="proportion", xticks=digits)
    ax.set_title(f"n = {test.n}, MAD = {test.mad:.4f} ({test.conformity})")
    ax.legend()
    return ax


def plot_price_spikes(
    prices: Sequence[float], flagged: Sequence[int] = (), *, ax: Axes | None = None
) -> Axes:
    """Draw a price series and mark the flagged steps.

    Parameters
    ----------
    prices : sequence of float
        One price per step.
    flagged : sequence of int
        Steps to mark, such as the output of
        :func:`~blockchainkit.fraud.systems.manipulation.detect_pumps`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not prices:
        raise ValueError("prices must not be empty")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(len(prices)), prices, color="#2563eb", label="price")
    marks = [t for t in flagged if 0 <= t < len(prices)]
    if marks:
        ax.scatter(marks, [prices[t] for t in marks], color="#dc2626", zorder=3, label="flagged")
    ax.set(xlabel="step", ylabel="price")
    ax.legend()
    return ax
