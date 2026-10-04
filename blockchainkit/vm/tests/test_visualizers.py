"""Smoke tests for blockchainkit.vm.visualizers."""

import matplotlib.axes
import pytest

from blockchainkit.vm import VMError, execute
from blockchainkit.vm.visualizers import plot_execution_trace


def test_plot_execution_trace_has_one_row_per_step():
    result = execute([("PUSH", 7), ("PUSH", 2), ("SUB", None)], trace=True)
    ax = plot_execution_trace(result.trace)
    assert isinstance(ax, matplotlib.axes.Axes)
    rows = {row for row, _ in ax.tables[0].get_celld()}
    assert len(rows) == 1 + 3


def test_plot_execution_trace_truncates_long_loops():
    with pytest.raises(VMError) as caught:
        execute([("JMP", 0)], gas_limit=50, trace=True)
    ax = plot_execution_trace(caught.value.trace, max_rows=10)
    assert "first 10 of 50" in ax.get_title()
    import matplotlib.pyplot as plt

    _, given = plt.subplots()
    assert plot_execution_trace(caught.value.trace, ax=given) is given
    with pytest.raises(ValueError, match="empty trace"):
        plot_execution_trace(())


def test_plot_stack_height_steps_through_the_trace():
    import matplotlib.pyplot as plt

    from blockchainkit.vm.visualizers import plot_stack_height

    trace = execute([("PUSH", 1), ("PUSH", 2), ("ADD", None)], trace=True).trace
    ax = plot_stack_height(trace)
    assert list(ax.lines[0].get_ydata()) == [1, 2, 1]
    _, other = plt.subplots()
    assert plot_stack_height(trace, label="sum", ax=other) is other
    assert other.get_legend() is not None
    with pytest.raises(ValueError, match="empty"):
        plot_stack_height(())
