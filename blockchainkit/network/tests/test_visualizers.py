"""Smoke tests for blockchainkit.network.visualizers."""

import matplotlib.axes
import pytest

from blockchainkit.network import SimulatedNetwork
from blockchainkit.network.visualizers import plot_gossip_timeline


def _line_network():
    network = SimulatedNetwork(["a", "b", "c"])
    network.connect("a", "b", latency=(2, 2))
    network.connect("b", "c", latency=(3, 3))
    return network


def test_plot_gossip_timeline_orders_peers_by_first_receipt():
    network = _line_network()
    network.broadcast("a", b"block")
    network.run()
    ax = plot_gossip_timeline(network.deliveries)
    assert isinstance(ax, matplotlib.axes.Axes)
    assert [label.get_text() for label in ax.get_yticklabels()] == ["c", "b", "a"]
    assert [patch.get_width() for patch in ax.patches] == [5, 2, 0]


def test_plot_gossip_timeline_requires_a_payload_choice_when_ambiguous():
    network = _line_network()
    network.broadcast("a", b"one")
    network.broadcast("c", b"two")
    network.run()
    with pytest.raises(ValueError, match="several payloads"):
        plot_gossip_timeline(network.deliveries)
    assert plot_gossip_timeline(network.deliveries, payload=b"two")
    with pytest.raises(ValueError, match="no deliveries"):
        plot_gossip_timeline(network.deliveries, payload=b"three")
