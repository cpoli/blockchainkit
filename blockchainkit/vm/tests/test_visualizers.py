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
    with pytest.raises(ValueError, match="empty trace"):
        plot_execution_trace(())
