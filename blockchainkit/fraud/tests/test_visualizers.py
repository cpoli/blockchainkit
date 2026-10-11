"""Smoke tests for blockchainkit.fraud.visualizers."""

import matplotlib.pyplot as plt
import pytest

from blockchainkit.fraud import PonziRun, benford_test, simulate_ponzi
from blockchainkit.fraud.visualizers import plot_benford, plot_ponzi, plot_price_spikes


def test_plot_ponzi_marks_the_collapse():
    ax = plot_ponzi(simulate_ponzi([100, 150, 225, 100]))
    assert "collapsed in period 3" in ax.get_title() and len(ax.patches) == 8
    assert "collapse" in [t.get_text() for t in ax.get_legend().get_texts()]
    _, given = plt.subplots()
    survived = plot_ponzi(simulate_ponzi([10, 20]), ax=given)
    assert survived is given and "survived" in given.get_title()
    with pytest.raises(ValueError, match="no periods"):
        plot_ponzi(PonziRun((), (), (), (), None))


def test_plot_benford_compares_with_the_law():
    test = benford_test(2**k for k in range(1, 200))
    ax = plot_benford(test, label="powers of two")
    assert len(ax.patches) == 9 and "n = 199" in ax.get_title()
    assert "powers of two" in [t.get_text() for t in ax.get_legend().get_texts()]
    _, given = plt.subplots()
    assert plot_benford(test, ax=given) is given


def test_plot_price_spikes_marks_flagged_steps():
    ax = plot_price_spikes([1.0, 2.0, 1.5], [1, 7])
    assert len(ax.collections) == 1 and len(ax.lines) == 1
    _, given = plt.subplots()
    assert plot_price_spikes([1.0], ax=given) is given and not given.collections
    with pytest.raises(ValueError, match="empty"):
        plot_price_spikes([])
