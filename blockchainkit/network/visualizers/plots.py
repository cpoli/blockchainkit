"""Plotting helpers for blockchainkit.network: propagation timelines."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from blockchainkit.network.core.base import Delivery

__all__ = ["plot_gossip_timeline"]


def plot_gossip_timeline(
    deliveries: Sequence[Delivery], *, payload: bytes | None = None, ax: Axes | None = None
) -> Axes:
    """Show when each peer first accepted a payload, earliest at the top.

    Parameters
    ----------
    deliveries : sequence of Delivery
        Usually ``SimulatedNetwork.deliveries``.
    payload : bytes, optional
        Payload to plot; required when deliveries contain several payloads.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    payloads = {d.payload for d in deliveries}
    if payload is None:
        if len(payloads) != 1:
            raise ValueError("deliveries hold several payloads; choose one with payload=")
        (payload,) = payloads
    chosen = sorted(
        (d for d in deliveries if d.payload == payload), key=lambda d: (d.time, d.recipient)
    )
    if not chosen:
        raise ValueError("no deliveries of that payload")
    if ax is None:
        _, ax = plt.subplots()
    ordered = chosen[::-1]  # barh draws bottom-up; keep the earliest peer on top.
    rows = range(len(ordered))
    ax.barh(rows, [d.time for d in ordered], color="#2563eb")
    ax.set_yticks(rows, [d.recipient for d in ordered])
    for row, d in zip(rows, ordered, strict=True):
        source = "origin" if d.sender == d.recipient else f"from {d.sender}"
        ax.text(d.time, row, f" t={d.time} ({source})", va="center", fontsize=8)
    ax.set_xlabel("simulation time of first acceptance")
    ax.set_title(f"Gossip reached {len(chosen)} peers by t={chosen[-1].time}")
    return ax
