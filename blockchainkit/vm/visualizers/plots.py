"""Plotting helpers for blockchainkit.vm: execution traces and stack heights."""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from blockchainkit.vm.core.base import TraceStep

__all__ = ["plot_execution_trace", "plot_stack_height"]


def plot_execution_trace(
    trace: Sequence[TraceStep], *, max_rows: int = 30, ax: Axes | None = None
) -> Axes:
    """Tabulate the stack, storage, and gas after each executed instruction.

    Parameters
    ----------
    trace : sequence of TraceStep
        ``ExecutionResult.trace`` or ``VMError.trace`` from
        ``execute(..., trace=True)``.
    max_rows : int
        Show at most this many steps (the first ones), so loops stay legible.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not trace:
        raise ValueError("empty trace: pass trace=True to execute")
    shown = list(trace[:max_rows])
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 0.35 * len(shown) + 1.4))
    rows = [
        [
            str(step.pc),
            step.opcode if step.operand is None else f"{step.opcode} {step.operand}",
            str(list(step.stack)),
            str(dict(step.storage)),
            str(step.gas_used),
        ]
        for step in shown
    ]
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=["pc", "instruction", "stack", "storage", "gas"],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)
    hidden = len(trace) - len(shown)
    suffix = f" (first {len(shown)} of {len(trace)} steps)" if hidden else ""
    ax.set_title("State after each instruction" + suffix)
    return ax


def plot_stack_height(
    trace: Sequence[TraceStep], *, label: str | None = None, ax: Axes | None = None
) -> Axes:
    """Plot the stack height after each executed instruction.

    The peak is the stack space the run needed: what a hardware stack must
    provide, and what static verification bounds in advance.

    Parameters
    ----------
    trace : sequence of TraceStep
        From ``execute(..., trace=True)``.
    label : str, optional
        Legend label, to compare several runs on one axes.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if not trace:
        raise ValueError("empty trace: pass trace=True to execute")
    if ax is None:
        _, ax = plt.subplots()
    heights = [len(step.stack) for step in trace]
    ax.step(range(1, len(heights) + 1), heights, where="post", label=label)
    ax.set_xlabel("instructions executed")
    ax.set_ylabel("stack height")
    ax.set_title(f"Stack height (peak {max(heights)})")
    if label is not None:
        ax.legend()
    return ax
