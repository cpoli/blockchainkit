"""Smoke tests for blockchainkit.network.visualizers."""

import matplotlib.axes
import matplotlib.pyplot as plt
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
    _, ax = plt.subplots()
    assert plot_gossip_timeline(network.deliveries, payload=b"two", ax=ax) is ax
    with pytest.raises(ValueError, match="no deliveries"):
        plot_gossip_timeline(network.deliveries, payload=b"three")


def test_plot_graph_draws_every_edge_and_highlights():
    from blockchainkit.network import ring_lattice
    from blockchainkit.network.visualizers import plot_graph

    _, ax = plt.subplots()
    assert plot_graph(ring_lattice(10, 4), highlight={0, 5}, ax=ax) is ax
    assert isinstance(plot_graph(ring_lattice(4, 2)), matplotlib.axes.Axes)
    assert len(ax.lines) == 20
    colors = ax.collections[0].get_facecolors()
    assert (colors[0] != colors[1]).any() and (colors[0] == colors[5]).all()


def test_plot_space_time_places_events_at_lamport_time():
    from blockchainkit.network.visualizers import plot_space_time

    history = [[("send", "m")], [("local", "x"), ("receive", "m")]]
    _, ax = plt.subplots()
    assert plot_space_time(history, ax=ax) is ax
    assert isinstance(plot_space_time(history), matplotlib.axes.Axes)
    points = sorted(tuple(c.get_offsets()[0]) for c in ax.collections)
    assert points == [(1, 0), (1, 1), (2, 1)]
    assert [label.get_text() for label in ax.get_yticklabels()] == ["P0", "P1"]


def test_plot_rumor_spread_plots_the_residue():
    from blockchainkit.network import spread_rumor
    from blockchainkit.network.visualizers import plot_rumor_spread

    run = spread_rumor(64, seed=1)
    _, ax = plt.subplots()
    assert plot_rumor_spread({"push": run}, ax=ax) is ax
    assert isinstance(plot_rumor_spread({"push": run}), matplotlib.axes.Axes)
    assert ax.lines[0].get_ydata()[0] == pytest.approx(63 / 64)
    assert len(ax.lines[0].get_xdata()) == run.rounds  # The final, zero residue is dropped.
    with pytest.raises(ValueError, match="at least one"):
        plot_rumor_spread({})
