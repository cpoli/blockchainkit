"""Plotting helpers for blockchainkit.proofs: polynomials over a field, proof sizes, and wiring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from blockchainkit.proofs.core.base import PlonkKey
from blockchainkit.proofs.utils.polynomials import poly_eval

__all__ = ["plot_copy_constraints", "plot_field_polynomials", "plot_proof_sizes"]

_COLORS = ("#2563eb", "#dc2626", "#16a34a", "#9333ea", "#d97706", "#0d9488")


def plot_field_polynomials(
    polynomials: Mapping[str, Sequence[int]], prime: int, *, ax: Axes | None = None
) -> Axes:
    """Scatter each polynomial's value at every point of a small field, and ring where they agree.

    Parameters
    ----------
    polynomials : mapping of str to sequence of int
        Labelled coefficient lists, constant term first.
    prime : int
        A field small enough to plot point by point (at most 2000).
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not polynomials:
        raise ValueError("need at least one polynomial")
    if not 2 <= prime <= 2000:
        raise ValueError("prime must be between 2 and 2000 to plot every point")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))
    xs = range(prime)
    columns = []
    for color, (label, poly) in zip(_COLORS * len(polynomials), polynomials.items(), strict=False):
        ys = [poly_eval(poly, x, prime) for x in xs]
        columns.append(ys)
        ax.scatter(xs, ys, s=8, color=color, label=label)
    if len(columns) > 1:
        agree = [x for x in xs if len({column[x] for column in columns}) == 1]
        ax.scatter(
            agree,
            [columns[0][x] for x in agree],
            s=80,
            facecolors="none",
            edgecolors="black",
            label=f"agree at {len(agree)} of {prime} points",
        )
    ax.set_xlabel("x")
    ax.set_ylabel(f"value mod {prime}")
    ax.legend(loc="upper right")
    return ax


def plot_proof_sizes(
    series: Mapping[str, Sequence[tuple[float, float]]],
    *,
    xlabel: str = "statement size",
    ylabel: str = "bytes",
    ax: Axes | None = None,
) -> Axes:
    """Draw how proof sizes grow, on log-log axes, one line per series.

    Parameters
    ----------
    series : mapping of str to sequence of tuple
        Labelled ``(x, y)`` points, for example ``(trace length, proof bytes)``.
    xlabel, ylabel : str
        Axis labels.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not series or any(not points for points in series.values()):
        raise ValueError("need at least one non-empty series")
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4.5))
    for color, (label, points) in zip(_COLORS * len(series), series.items(), strict=False):
        xs, ys = zip(*points, strict=True)
        ax.plot(xs, ys, "o-", color=color, label=label)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    return ax


def plot_copy_constraints(key: PlonkKey, *, ax: Axes | None = None) -> Axes:
    """Draw a PLONK circuit's wire grid and the cycles of its copy-constraint permutation.

    Each row is a gate and each column a wire (a, b, c); positions joined by
    a line must carry the same value.

    Parameters
    ----------
    key : PlonkKey
        From :func:`~blockchainkit.proofs.systems.plonk.plonk_setup`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(4, 1 + 0.5 * key.n))
    cycles: dict[int, list[tuple[int, int]]] = {}
    for row, wires in enumerate(key.wiring):
        for column, variable in enumerate(wires):
            cycles.setdefault(variable, []).append((column, row))
    for color, cycle in zip(_COLORS * len(cycles), cycles.values(), strict=False):
        columns, rows = zip(*cycle, strict=True)
        ax.scatter(columns, rows, color=color, s=60, zorder=3)
        if len(cycle) > 1:
            ax.plot(columns, rows, color=color, alpha=0.6)
    ax.set_xticks([0, 1, 2], ["a (left)", "b (right)", "c (output)"])
    ax.set_yticks(range(key.n))
    ax.set_ylabel("gate")
    ax.invert_yaxis()
    ax.set_title(f"{len(cycles)} variables on {3 * key.n} wire positions")
    return ax
