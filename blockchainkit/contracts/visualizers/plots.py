"""Plotting helpers for blockchainkit.contracts: call trees, symbolic paths, and storage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from blockchainkit.contracts.core.base import Receipt, SymbolicResult

__all__ = ["plot_call_tree", "plot_storage", "plot_symbolic_paths"]

_KIND_COLORS = {"call": "#2563eb", "delegatecall": "#9333ea", "create": "#0d9488"}
_OUTCOME_COLORS = {
    "ok": "#16a34a",
    "stop": "#16a34a",
    "reverted": "#64748b",
    "revert": "#64748b",
    "assertion": "#dc2626",
    "error": "#dc2626",
    "bound": "#d97706",
}


def plot_call_tree(
    receipt: Receipt,
    *,
    names: Callable[[str], str] | None = None,
    ax: Axes | None = None,
) -> Axes:
    """Draw a transaction's calls in the order they began, indented by depth.

    Reverted calls are struck through in red, so a failure deep in the tree
    and the calls it undid are visible at once.

    Parameters
    ----------
    receipt : Receipt
        From :meth:`~blockchainkit.contracts.systems.world.World.transact`.
    names : callable, optional
        Maps an address to a label, such as ``world.name``.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    calls = receipt.calls
    if not calls:
        raise ValueError("the receipt has no calls")
    label = names or (lambda address: address)
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 0.45 * len(calls) + 1))
    for row, record in enumerate(calls):
        y = -row
        function = "receive" if record.function is None else record.function
        value = f" {{value: {record.value}}}" if record.value else ""
        text = f"{record.kind}  {label(record.sender)} -> {label(record.to)}.{function}{value}"
        if record.kind == "delegatecall":
            text += f"  [storage of {label(record.context)}]"
        color = _KIND_COLORS.get(record.kind, "#334155") if record.ok else "#dc2626"
        ax.plot([record.depth], [y], "s", color=color, markersize=7)
        if record.depth:
            ax.plot(
                [record.depth - 1, record.depth - 1, record.depth],
                [y + 0.5, y, y],
                color="#94a3b8",
                linewidth=1,
            )
        suffix = "" if record.ok else f"   reverted: {record.error}"
        ax.text(record.depth + 0.15, y, text + suffix, va="center", fontsize=8.5, color=color)
    depth = max(record.depth for record in calls)
    ax.set_xlim(-0.3, depth + 6)
    ax.set_ylim(-len(calls) + 0.5, 0.8)
    ax.axis("off")
    status = "succeeded" if receipt.success else f"reverted ({receipt.error})"
    ax.set_title(f"Call tree: {len(calls)} calls, {receipt.gas_used:,} gas, {status}")
    return ax


def plot_symbolic_paths(result: SymbolicResult, *, ax: Axes | None = None) -> Axes:
    """Draw the execution tree of a symbolic run, each leaf colored by its outcome.

    Each fork is a branch decision on a symbolic condition; each leaf is one
    path, labelled by its outcome.

    Parameters
    ----------
    result : SymbolicResult
        From :func:`~blockchainkit.contracts.systems.symbolic.symbolic_execute`
        or :func:`~blockchainkit.contracts.systems.symbolic.symbolic_bytecode`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    paths = result.paths
    if not paths:
        raise ValueError("no paths to draw")
    if ax is None:
        _, ax = plt.subplots(figsize=(max(4, 1.3 * len(paths)), 4))
    # Each tree node is a prefix of decisions; place it over the mean of its leaves.
    leaves: dict[tuple[bool, ...], list[int]] = {}
    for index, path in enumerate(paths):
        for depth in range(len(path.decisions) + 1):
            leaves.setdefault(path.decisions[:depth], []).append(index)
    position = {prefix: sum(members) / len(members) for prefix, members in leaves.items()}
    for prefix in position:
        if prefix:
            parent = prefix[:-1]
            style = "-" if prefix[-1] else "--"
            ax.plot(
                [position[parent], position[prefix]],
                [-len(parent), -len(prefix)],
                style,
                color="#94a3b8",
                linewidth=1.2,
            )
    seen = set()
    for index, path in enumerate(paths):
        depth = -len(path.decisions)
        color = _OUTCOME_COLORS.get(path.outcome, "#334155")
        ax.plot(
            [index],
            [depth],
            "o",
            color=color,
            markersize=11,
            label=None if path.outcome in seen else path.outcome,
        )
        seen.add(path.outcome)
        ax.annotate(
            path.outcome,
            (index, depth),
            textcoords="offset points",
            xytext=(0, -16),
            ha="center",
            fontsize=8,
        )
    ax.plot([position[()]], [0], "o", color="#334155", markersize=8)
    ax.set_ylim(-max(len(p.decisions) for p in paths) - 0.8, 0.5)
    ax.set_xlim(-0.6, len(paths) - 0.4)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_ylabel("branch decisions (solid: condition true)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title(f"{len(paths)} paths over {', '.join(result.variables) or 'no inputs'}")
    return ax


def plot_storage(
    storage: Mapping[Any, Any],
    *,
    fields: Mapping[Any, str] | None = None,
    title: str = "Storage",
    ax: Axes | None = None,
) -> Axes:
    """Tabulate storage slots and their values, optionally naming each slot.

    Parameters
    ----------
    storage : mapping
        Slot to value, such as ``world.storage(address)``.
    fields : mapping, optional
        Slot to a field name, to show what a layout calls each slot.
    title : str
        Axes title.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    names = fields or {}
    slots = sorted(storage, key=repr)
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 0.4 * max(len(slots), 1) + 1))
    rows = [[_short(slot), names.get(slot, ""), _short(storage[slot])] for slot in slots]
    ax.axis("off")
    if rows:
        table = ax.table(
            cellText=rows, colLabels=["slot", "field", "value"], cellLoc="center", loc="center"
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.3)
    else:
        ax.text(0.5, 0.5, "empty", ha="center", va="center")
    ax.set_title(title)
    return ax


def _short(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 24 else text[:10] + "..." + text[-8:]
