"""Plotting helpers for blockchainkit.economics: fee markets, market makers, and gas auctions."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from blockchainkit.economics.core.base import FeeMarketRun, GasAuction

__all__ = ["plot_constant_product", "plot_fee_market", "plot_gas_auction"]

_COLORS = ("#2563eb", "#dc2626", "#16a34a", "#9333ea", "#d97706", "#0d9488")


def plot_fee_market(run: FeeMarketRun, *, gas_target: int, ax: Axes | None = None) -> Axes:
    """Draw how full each block was and the fee per gas paid in it.

    Bars show gas used as a multiple of ``gas_target``; the line shows the
    base fee under EIP-1559, or the mean fee paid in a first-price auction.

    Parameters
    ----------
    run : FeeMarketRun
        From :func:`~blockchainkit.economics.systems.fee_market.simulate_fee_market`.
    gas_target : int
        The target the run used.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
        The axes holding the fullness bars; the fee line is on a twin axis.
    """
    if not run.gas_used:
        raise ValueError("the run has no blocks")
    if gas_target <= 0:
        raise ValueError("gas_target must be positive")
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4))
    blocks = np.arange(len(run.gas_used))
    ax.bar(blocks, np.array(run.gas_used) / gas_target, color="#cbd5e1", label="gas used / target")
    ax.axhline(1, color="#64748b", linestyle="--", linewidth=1)
    ax.set_xlabel("block")
    ax.set_ylabel("gas used / target")
    fees = ax.twinx()
    if run.mechanism == "eip1559":
        fees.plot(blocks, run.base_fees, color="#dc2626", label="base fee")
    else:
        fees.plot(blocks, run.mean_price, color="#2563eb", label="mean fee paid")
    fees.set_ylabel("fee per gas")
    fees.set_ylim(bottom=0)
    ax.set_title(f"{run.mechanism}: block fullness and price")
    handles = ax.get_legend_handles_labels()[0] + fees.get_legend_handles_labels()[0]
    ax.legend(handles=handles, loc="upper left")
    return ax


def plot_constant_product(
    reserve0: int,
    reserve1: int,
    *,
    states: Sequence[tuple[int, int]] = (),
    ax: Axes | None = None,
) -> Axes:
    """Draw the curve ``x y = k`` through a pool's reserves, and the states it passed through.

    Parameters
    ----------
    reserve0, reserve1 : int
        The reserves defining ``k``.
    states : sequence of tuple of int
        Reserves after successive trades, joined by arrows.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if reserve0 <= 0 or reserve1 <= 0:
        raise ValueError("reserves must be positive")
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    k = reserve0 * reserve1
    points = [(reserve0, reserve1), *states]
    xs = [x for x, _ in points]
    x = np.linspace(min(xs) * 0.5, max(xs) * 1.6, 200)
    ax.plot(x, k / x, color="#64748b", label=f"x y = {k:,}")
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        ax.annotate("", (x1, y1), (x0, y0), arrowprops={"arrowstyle": "->", "color": "#dc2626"})
    ax.scatter(xs, [y for _, y in points], color="#2563eb", zorder=3)
    ax.set_xlabel("reserve of token0")
    ax.set_ylabel("reserve of token1")
    ax.set_title("A constant-product pool")
    ax.legend()
    return ax


def plot_gas_auction(auction: GasAuction, *, opportunity: int, ax: Axes | None = None) -> Axes:
    """Draw each bot's successive bids in a priority gas auction.

    Parameters
    ----------
    auction : GasAuction
        From :func:`~blockchainkit.economics.systems.ordering.priority_gas_auction`.
    opportunity : int
        The value competed for, drawn as a ceiling.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not auction.bids:
        raise ValueError("the auction has no bids")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))
    fees = [fee for _, fee in auction.bids]
    ax.step(range(len(fees)), fees, color="#64748b", where="post")
    bots = sorted({bot for bot, _ in auction.bids})
    for color, bot in zip(_COLORS * len(bots), bots, strict=False):
        steps = [(i, fee) for i, (name, fee) in enumerate(auction.bids) if name == bot]
        ax.scatter(*zip(*steps, strict=True), color=color, label=bot, zorder=3)
    ax.axhline(opportunity, color="black", linestyle="--", label="opportunity")
    ax.set_yscale("log")
    ax.set_xlabel("replacement")
    ax.set_ylabel("fee bid")
    ax.set_title(f"{auction.winner} wins, paying {auction.price:,} of {opportunity:,}")
    ax.legend()
    return ax
