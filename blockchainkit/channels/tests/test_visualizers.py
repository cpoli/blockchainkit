"""Smoke tests for blockchainkit.channels.visualizers."""

import matplotlib.pyplot as plt
import pytest

from blockchainkit.channels import ChannelNetwork, extend
from blockchainkit.channels.visualizers import plot_detection, plot_route, plot_shares
from blockchainkit.network import Graph


def test_plot_shares_marks_data_parity_and_withheld():
    block = extend([3, 1, 4, 1])
    ax = plot_shares(block, withheld=[5, 6])
    labels = [text.get_text() for text in ax.get_legend().get_texts()]
    assert sorted(labels) == ["data", "parity", "withheld"] and "4 data shares" in ax.get_title()
    assert len(plot_shares(block).get_legend().get_texts()) == 2
    _, given = plt.subplots()
    assert plot_shares(extend([7]), withheld=[1], ax=given) is given  # No parity left to draw.


def test_plot_route_draws_amounts_and_expiries():
    network = ChannelNetwork.random(Graph(3, [(0, 1), (1, 2)]), capacity=1_000, seed=1)
    route = network.route((0, 1, 2), 100, height=10)
    ax = plot_route(route)
    assert len(ax.patches) == 2 and f"fee {route.fee}" in ax.get_title()
    _, given = plt.subplots()
    assert plot_route(route, ax=given) is given


def test_plot_detection_draws_one_curve_per_fraction():
    ax = plot_detection(range(1, 11), withheld=(0.25, 0.5))
    assert len(ax.lines) == 3  # Two curves and the 99% line.
    _, given = plt.subplots()
    assert plot_detection([1], ax=given) is given
    with pytest.raises(ValueError, match="no sample"):
        plot_detection([])
