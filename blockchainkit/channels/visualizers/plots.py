"""Plotting helpers for blockchainkit.channels: erasure-coded shares, routes, and sampling."""

from __future__ import annotations

from collections.abc import Collection, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from blockchainkit.channels.core.base import ErasureCodedData, Route
from blockchainkit.channels.systems.data_availability import detection_probability

__all__ = ["plot_detection", "plot_route", "plot_shares"]


def plot_shares(
    block: ErasureCodedData, *, withheld: Collection[int] = (), ax: Axes | None = None
) -> Axes:
    """Draw a block's shares as stems: data, parity, and any withheld by the producer.

    Parameters
    ----------
    block : ErasureCodedData
        From :func:`~blockchainkit.channels.systems.data_availability.extend`.
    withheld : collection of int
        Positions drawn as missing.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3.5))
    hidden = set(withheld)
    positions = np.arange(len(block.shares))
    for label, color, chosen in (
        ("data", "#2563eb", [p for p in positions if p < block.k and p not in hidden]),
        ("parity", "#16a34a", [p for p in positions if p >= block.k and p not in hidden]),
    ):
        if chosen:
            markers = ax.stem(chosen, [block.shares[p] for p in chosen], label=label)
            plt.setp(markers.markerline, color=color)
            plt.setp(markers.stemlines, color=color)
    if hidden:
        ax.scatter(sorted(hidden), [0] * len(hidden), marker="x", color="#dc2626", label="withheld")
    ax.axvline(block.k - 0.5, color="#64748b", linestyle="--", linewidth=1)
    ax.set_xlabel("share position")
    ax.set_ylabel("value in the field")
    ax.set_title(f"{block.k} data shares extended to {len(block.shares)}")
    ax.legend(loc="upper left")
    return ax


def plot_route(route: Route, *, ax: Axes | None = None) -> Axes:
    """Draw the HTLC amount and expiry offered on each hop of a route.

    Parameters
    ----------
    route : Route
        From :meth:`~blockchainkit.channels.systems.routing.ChannelNetwork.route`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
        The axes holding the amount bars; the expiries are on a twin axis.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 3.5))
    hops = [f"{u}->{v}" for u, v in zip(route.nodes, route.nodes[1:], strict=False)]
    ax.bar(hops, route.amounts, color="#cbd5e1", label="HTLC amount")
    ax.set_ylim(min(route.amounts) * 0.99, max(route.amounts) * 1.005)
    ax.set_xlabel("hop")
    ax.set_ylabel("amount offered")
    expiries = ax.twinx()
    expiries.plot(hops, route.expiries, "o-", color="#dc2626", label="expiry")
    expiries.set_ylabel("expiry (block height)")
    ax.set_title(f"A {len(hops)}-hop route: fee {route.fee}")
    handles = ax.get_legend_handles_labels()[0] + expiries.get_legend_handles_labels()[0]
    ax.legend(handles=handles, loc="upper right")
    return ax


def plot_detection(
    samples: Sequence[int],
    withheld: Sequence[float] = (0.1, 0.25, 0.5),
    *,
    ax: Axes | None = None,
) -> Axes:
    """Draw the chance a light client notices withholding, against how many shares it samples.

    Parameters
    ----------
    samples : sequence of int
        Sample counts on the horizontal axis.
    withheld : sequence of float
        Fractions of shares withheld, one curve each.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not samples:
        raise ValueError("no sample counts to plot")
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    for fraction in withheld:
        chances = [detection_probability(fraction, s) for s in samples]
        ax.plot(samples, chances, "o-", label=f"{fraction:.0%} withheld")
    ax.axhline(0.99, color="#64748b", linestyle="--", linewidth=1)
    ax.set_xlabel("shares sampled")
    ax.set_ylabel("probability of detecting withholding")
    ax.set_ylim(0, 1.02)
    ax.set_title("Data-availability sampling")
    ax.legend(loc="lower right")
    return ax
