"""Plotting helpers for blockchainkit.network: graphs, space-time diagrams, and spreading."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from blockchainkit.network.core.base import Delivery, RumorRun
from blockchainkit.network.systems.clocks import Event, lamport_timestamps
from blockchainkit.network.systems.topology import Graph

__all__ = ["plot_gossip_timeline", "plot_graph", "plot_rumor_spread", "plot_space_time"]


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


def plot_graph(graph: Graph, *, highlight: Iterable[int] = (), ax: Axes | None = None) -> Axes:
    """Draw a peer graph with its nodes on a circle.

    A circle shows the structure of ring lattices and small worlds directly:
    lattice links hug the rim and rewired shortcuts cut across it.

    Parameters
    ----------
    graph : Graph
        The graph to draw.
    highlight : iterable of int
        Nodes to draw in a contrasting color, such as spies or hubs.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots()
    angles = 2 * np.pi * np.arange(graph.n) / graph.n
    x, y = np.cos(angles), np.sin(angles)
    for u, v in graph.edges:
        ax.plot([x[u], x[v]], [y[u], y[v]], color="#94a3b8", linewidth=0.6, zorder=1)
    marked = set(highlight)
    colors = ["#dc2626" if node in marked else "#2563eb" for node in range(graph.n)]
    ax.scatter(x, y, s=18, c=colors, zorder=2)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{graph.n} peers, {len(graph.edges)} links")
    return ax


def plot_space_time(processes: Sequence[Sequence[Event]], *, ax: Axes | None = None) -> Axes:
    """Draw Lamport's space-time diagram, labeling each event with its Lamport clock.

    Each process is a horizontal line, time runs left to right, and each
    message is an arrow from its send to its receive. An event is placed at
    its Lamport timestamp, so every arrow points forward in time.

    Parameters
    ----------
    processes : sequence of sequence of Event
        A history as accepted by
        :func:`~blockchainkit.network.systems.clocks.lamport_timestamps`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    stamps = lamport_timestamps(processes)
    if ax is None:
        _, ax = plt.subplots()
    sends: dict[str, tuple[int, int]] = {}
    for p, events in enumerate(processes):
        ax.axhline(p, color="#cbd5e1", linewidth=1, zorder=0)
        for i, (kind, label) in enumerate(events):
            if kind == "send":
                sends[label] = (stamps[p][i], p)
    for p, events in enumerate(processes):
        for i, (kind, label) in enumerate(events):
            clock = stamps[p][i]
            if kind == "receive":
                start = sends[label]
                ax.annotate(
                    "",
                    xy=(clock, p),
                    xytext=start,
                    arrowprops={"arrowstyle": "->", "color": "#2563eb"},
                )
            ax.scatter(clock, p, s=30, color="black", zorder=2)
            ax.annotate(
                f"{label} ({clock})",
                (clock, p),
                xytext=(3, 6),
                textcoords="offset points",
                fontsize=8,
            )
    ax.set_yticks(range(len(processes)), [f"P{p}" for p in range(len(processes))])
    ax.set_xlabel("Lamport time")
    ax.set_title("Space-time diagram")
    return ax


def plot_rumor_spread(runs: Mapping[str, RumorRun], *, ax: Axes | None = None) -> Axes:
    """Plot the fraction of peers still uninformed after each round, on a log scale.

    On a log scale, push's slow final phase shows as a straight line
    (the residue shrinks by a constant factor per round), while pull's
    accelerating fall shows the residue squaring each round.

    Parameters
    ----------
    runs : mapping of str to RumorRun
        Runs to compare, keyed by their legend label.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not runs:
        raise ValueError("provide at least one run")
    if ax is None:
        _, ax = plt.subplots()
    for label, run in runs.items():
        residue = [1 - count / run.n for count in run.informed]
        rounds = [r for r, value in enumerate(residue) if value > 0]
        ax.semilogy(rounds, [residue[r] for r in rounds], marker="o", markersize=3, label=label)
    ax.set_xlabel("round")
    ax.set_ylabel("fraction still uninformed")
    ax.set_title("Rumor spreading")
    ax.legend()
    return ax
