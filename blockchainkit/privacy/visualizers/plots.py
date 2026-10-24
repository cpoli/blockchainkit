"""Plotting helpers for blockchainkit.privacy: clusters, ring members, and anonymity sets."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from blockchainkit.privacy.core.base import RingInput

__all__ = ["plot_anonymity_sets", "plot_cluster_sizes", "plot_ring_positions"]


def plot_cluster_sizes(
    clusters: Iterable[frozenset[str]], *, ax: Axes | None = None, label: str = "clusters"
) -> Axes:
    """Draw how many clusters have each size, on logarithmic axes.

    Parameters
    ----------
    clusters : iterable of frozenset of str
        From :func:`~blockchainkit.privacy.systems.clustering.cluster_addresses`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.
    label : str
        Legend label of the points.

    Returns
    -------
    matplotlib.axes.Axes
    """
    sizes = [len(c) for c in clusters]
    if not sizes:
        raise ValueError("no clusters to plot")
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    values, counts = np.unique(sizes, return_counts=True)
    ax.loglog(values, counts, marker="o", linestyle="none", label=label)
    ax.set(xlabel="cluster size (addresses)", ylabel="number of clusters")
    ax.set_title(f"{len(sizes)} clusters, largest {max(sizes)}")
    ax.legend()
    return ax


def plot_ring_positions(rings: Sequence[RingInput], *, ax: Axes | None = None) -> Axes:
    """Draw how often the real output is the newest ring member, the second newest, and so on.

    Parameters
    ----------
    rings : sequence of RingInput
        From :func:`~blockchainkit.privacy.systems.traceability.simulate_rings`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not rings:
        raise ValueError("no rings to plot")
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    size = max(len(ring.members) for ring in rings)
    counts = np.zeros(size)
    for ring in rings:
        counts[len(ring.members) - 1 - ring.members.index(ring.real)] += 1
    ax.bar(np.arange(1, size + 1), counts / len(rings), color="#2563eb")
    ax.axhline(1 / size, color="#64748b", linestyle="--", label=f"blind guess, 1/{size}")
    ax.set(xlabel="rank of the real output (1 = newest member)", ylabel="fraction of rings")
    ax.set_title(f"Newest member is the real one in {counts[0] / len(rings):.0%} of rings")
    ax.legend()
    return ax


def plot_anonymity_sets(sizes: Sequence[int], *, ax: Axes | None = None) -> Axes:
    """Draw each withdrawal's anonymity set, in order.

    Parameters
    ----------
    sizes : sequence of int
        From :attr:`~blockchainkit.privacy.core.base.MixerReport.anonymity_sets`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not sizes:
        raise ValueError("no withdrawals to plot")
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    ax.step(np.arange(1, len(sizes) + 1), sizes, where="mid", color="#16a34a")
    ax.axhline(1, color="#dc2626", linestyle=":", label="fully linked")
    ax.set(xlabel="withdrawal", ylabel="anonymity set (deposits)", ylim=(0, None))
    ax.set_title(f"Smallest anonymity set: {min(sizes)}")
    ax.legend()
    return ax
