"""Smoke tests for blockchainkit.privacy.visualizers."""

import matplotlib.pyplot as plt
import pytest

from blockchainkit.privacy import RingInput, cluster_addresses, simulate_payments
from blockchainkit.privacy.visualizers import (
    plot_anonymity_sets,
    plot_cluster_sizes,
    plot_ring_positions,
)


def test_plot_cluster_sizes():
    history = simulate_payments(10, 40, seed=1)
    clusters = cluster_addresses(history.transactions, change=True)
    ax = plot_cluster_sizes(clusters, label="change")
    assert "clusters" in ax.get_title() and len(ax.lines) == 1
    _, given = plt.subplots()
    assert plot_cluster_sizes(clusters, ax=given) is given
    with pytest.raises(ValueError, match="no clusters"):
        plot_cluster_sizes([])


def test_plot_ring_positions_ranks_the_real_output():
    rings = [RingInput((1, 2, 3), 3, 5), RingInput((1, 2, 3), 1, 5), RingInput((4,), 4, 6)]
    ax = plot_ring_positions(rings)
    assert len(ax.patches) == 3 and "67%" in ax.get_title()
    assert [p.get_height() for p in ax.patches] == pytest.approx([2 / 3, 0, 1 / 3])
    _, given = plt.subplots()
    assert plot_ring_positions(rings, ax=given) is given
    with pytest.raises(ValueError, match="no rings"):
        plot_ring_positions([])


def test_plot_anonymity_sets():
    ax = plot_anonymity_sets([3, 2, 5])
    assert "Smallest anonymity set: 2" in ax.get_title()
    _, given = plt.subplots()
    assert plot_anonymity_sets([1], ax=given) is given
    with pytest.raises(ValueError, match="no withdrawals"):
        plot_anonymity_sets([])
