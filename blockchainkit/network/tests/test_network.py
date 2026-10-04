"""Propagation timing, partitions, duplicate handling, and event budgets."""

import pytest

from blockchainkit.network import SimulatedNetwork


def test_line_propagation_and_duplicates():
    network = SimulatedNetwork(["a", "b", "c"])
    network.connect("a", "b", latency=(2, 2))
    network.connect("b", "c", latency=(3, 3))
    network.broadcast("a", b"hello")
    network.run(until=3)
    assert [(d.recipient, d.time) for d in network.deliveries] == [("a", 0), ("b", 2)]
    assert network.pending == 1 and network.time == 3
    network.run()
    assert network.deliveries[-1].time == 5
    network.broadcast("a", b"hello")
    network.run()
    assert len(network.deliveries) == 3


def test_partition_drops_inflight_even_after_reconnect():
    network = SimulatedNetwork(["a", "b"])
    network.connect("a", "b", latency=(5, 5))
    network.broadcast("a", b"block")
    network.disconnect("a", "b")
    network.connect("a", "b", latency=(1, 1))
    network.run()
    assert len(network.deliveries) == 1
    network.broadcast("a", b"block")
    network.run()
    assert [d.recipient for d in network.deliveries] == ["a", "b"]


def test_seed_order_independence_and_budget():
    def simulate(peers):
        network = SimulatedNetwork(peers, seed=17)
        network.connect("a", "b", latency=(1, 5))
        network.connect("a", "c", latency=(1, 5))
        network.connect("b", "c", latency=(1, 5))
        network.broadcast("a", b"hello")
        assert network.run(until=100, max_events=1) == 1
        assert network.time < 100
        network.run(until=100)
        assert network.time == 100
        return network.deliveries

    assert simulate(["a", "b", "c"]) == simulate(["c", "b", "a"])


def test_callback_rejection_stops_forwarding():
    network = SimulatedNetwork(["a", "b", "c"], on_receive=lambda d: d.recipient != "b")
    network.connect("a", "b")
    network.connect("b", "c")
    network.broadcast("a", b"invalid at b")
    network.run()
    network.broadcast("b", b"invalid at b")
    network.run()
    assert [d.recipient for d in network.deliveries] == ["a"]


def test_gossip_has_no_global_knowledge_of_neighbors_seen_sets():
    network = SimulatedNetwork(["a", "b", "c"])
    network.connect("a", "b", latency=(3, 3))
    network.connect("a", "c")
    network.connect("b", "c")
    network.broadcast("a", b"update")
    # b receives via c before a's slower direct send. Its forward toward a
    # still consumes a network event, even though a already knows the message.
    assert network.run() == 4
    assert [(d.recipient, d.time) for d in network.deliveries] == [("a", 0), ("c", 1), ("b", 2)]


def test_invalid_network_inputs():
    for names in ([], ["a", "a"], [""]):
        with pytest.raises(ValueError):
            SimulatedNetwork(names)
    network = SimulatedNetwork(["a", "b"])
    for endpoints in (("a", "a"), ("a", "x")):
        with pytest.raises(ValueError):
            network.connect(*endpoints)
    with pytest.raises(ValueError):
        network.connect("a", "b", latency=(0, 1))
    with pytest.raises(ValueError):
        network.broadcast("x", b"hi")
    with pytest.raises(TypeError):
        network.broadcast("a", "hi")
    network.run(until=3)
    with pytest.raises(ValueError):
        network.run(until=2)


def test_a_failing_receive_callback_does_not_mark_the_payload_seen():
    failures = iter([RuntimeError("callback crashed")])

    def flaky(delivery):
        error = next(failures, None)
        if error is not None:
            raise error

    network = SimulatedNetwork(["a"], on_receive=flaky)
    with pytest.raises(RuntimeError):
        network.broadcast("a", b"payload")
    network.broadcast("a", b"payload")
    assert [d.payload for d in network.deliveries] == [b"payload"]


@pytest.mark.parametrize("seed", ["seed", 1.5, True])
def test_network_requires_an_integer_seed(seed):
    with pytest.raises(TypeError, match="seed"):
        SimulatedNetwork(["a"], seed=seed)


def test_network_repr_summarizes_the_simulation():
    network = SimulatedNetwork(["a", "b", "c"])
    network.connect("a", "b")
    network.broadcast("a", b"x")
    assert repr(network) == "SimulatedNetwork(peers=3, links=1, time=0, pending=1)"
