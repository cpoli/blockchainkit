"""Plotting helpers for blockchainkit.crypto: small curve groups and hash avalanche."""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from blockchainkit.crypto.systems.curves import Curve, enumerate_points, multiply

__all__ = ["plot_curve_points", "plot_hamming_distances"]


def plot_curve_points(
    curve: Curve, *, label_multiples: bool = True, ax: Axes | None = None
) -> Axes:
    """Scatter every finite point of a small curve and label the multiples kG.

    Parameters
    ----------
    curve : Curve
        A curve with p <= 10,000
        (see :func:`~blockchainkit.crypto.systems.curves.enumerate_points`).
    label_multiples : bool
        Annotate each point kG of the generator's subgroup with its k, which
        shows that scalar multiplication jumps around the plane with no
        visible pattern: the discrete-log problem.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots()
    points = np.array(enumerate_points(curve))
    ax.scatter(points[:, 0], points[:, 1], s=40, color="#94a3b8", label="curve points")
    if label_multiples:
        for k in range(1, curve.order):
            point = multiply(k, curve.generator, curve)
            assert point is not None  # k < order, so kG is finite.
            ax.scatter(*point, s=55, color="#2563eb")
            ax.annotate(f"{k}G", point, xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlim(-1, curve.p)
    ax.set_ylim(-1, curve.p)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(f"y² = x³ + {curve.a}x + {curve.b} over F_{curve.p}: {len(points) + 1} points")
    return ax


def plot_hamming_distances(
    distances: Sequence[int], bits: int = 256, ax: Axes | None = None
) -> Axes:
    """Histogram of output-bit differences against the ideal Binomial(bits, 1/2).

    Parameters
    ----------
    distances : sequence of int
        Hamming distances between digests of related inputs, e.g. from
        :func:`~blockchainkit.crypto.systems.hashing.hamming_distance` after a one-bit flip.
    bits : int
        Digest length in bits.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots()
    values = np.asarray(distances)
    ax.hist(values, bins=18, density=True, color="#0d9488", edgecolor="white", label="observed")
    spread = 4 * np.sqrt(bits) / 2
    ks = np.arange(int(bits / 2 - spread), int(bits / 2 + spread) + 1)
    ideal = np.array([comb(bits, int(k)) for k in ks], dtype=float) / 2.0**bits
    ax.plot(ks, ideal, color="black", label=f"Binomial({bits}, 1/2)")
    ax.axvline(bits / 2, color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("differing output bits")
    ax.set_ylabel("probability")
    ax.set_title("Avalanche: about half the output bits change")
    ax.legend()
    return ax
