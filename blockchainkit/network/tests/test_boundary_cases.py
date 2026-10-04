"""Validation and edge cases for the network APIs added with the history pages."""

import pytest

import blockchainkit as bk
from blockchainkit import _validation

N = bk.network


def test_shared_real_number_validators():
    for check in (_validation.probability, _validation.positive):
        with pytest.raises(TypeError):
            check(True, "x")
        with pytest.raises(TypeError):
            check("0.5", "x")
    with pytest.raises(ValueError):
        _validation.probability(1.5, "x")
    with pytest.raises(ValueError):
        _validation.positive(0, "x")
    with pytest.raises(ValueError):
        _validation.positive(float("inf"), "x")


@pytest.mark.parametrize(
    "edges,error",
    [([(0, 0)], ValueError), ([(0, 3)], ValueError), ([(0, True)], TypeError)],
)
def test_graph_rejects_bad_edges(edges, error):
    with pytest.raises(error):
        N.Graph(3, edges)


def test_generator_validation():
    with pytest.raises(ValueError, match="even"):
        N.ring_lattice(6, 3)
    with pytest.raises(ValueError, match="even"):
        N.ring_lattice(4, 4)
    with pytest.raises(ValueError):
        N.erdos_renyi(5, 1.5)
    with pytest.raises(ValueError):
        N.barabasi_albert(2, 2)
    assert N.erdos_renyi(5, 0.0).edges == ()
    # With k = n - 1 the lattice is complete: there is nowhere to rewire to.
    assert N.watts_strogatz(5, 4, 1.0).edges == N.complete_graph(5).edges


def test_rumor_validation():
    with pytest.raises(ValueError, match="mode"):
        N.spread_rumor(10, mode="shout")
    with pytest.raises(ValueError, match="source"):
        N.spread_rumor(10, source=10)
    assert N.spread_rumor(1).informed == (1,)
    isolated = N.Graph(2, [])
    assert N.spread_rumor(isolated).informed == (1,)
    assert N.spread_rumor(N.Graph(3, [(0, 1)]), source=0).informed == (1, 2)


def test_broadcast_validation():
    with pytest.raises(ValueError, match="range"):
        N.reliable_broadcast(4, {4}, ["a"] * 4)
    with pytest.raises(ValueError, match="one str"):
        N.reliable_broadcast(4, set(), ["a"] * 3)
    with pytest.raises(ValueError, match="same value"):
        N.reliable_broadcast(4, set(), ["a", "a", "b", "a"])
    with pytest.raises(TypeError):
        N.reliable_broadcast(4, set(), ["a"] * 4, tolerance=1.0)  # type: ignore[arg-type]
    quiet = N.reliable_broadcast(4, set(), ["a"] * 4, tolerance=0)
    assert set(quiet.delivered.values()) == {"a"}


def test_register_validation():
    with pytest.raises(ValueError, match="mode"):
        N.ReplicatedRegister(3, mode="eventual")
    register = N.ReplicatedRegister(3)
    assert repr(register) == "ReplicatedRegister(replicas=3, mode='consistent')"
    with pytest.raises(ValueError, match="cover"):
        register.partition([0], [1])
    with pytest.raises(ValueError, match="unknown"):
        register.read(3)
    with pytest.raises(TypeError):
        register.write(0, 5)  # type: ignore[arg-type]


def test_kademlia_validation():
    with pytest.raises(TypeError):
        N.node_id("alice", 8)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="256"):
        N.node_id(b"alice", 257)
    with pytest.raises(ValueError, match="at least one"):
        N.KademliaNetwork([], bits=4)
    with pytest.raises(ValueError, match="below"):
        N.KademliaNetwork([16], bits=4)
    with pytest.raises(ValueError, match="distinct"):
        N.KademliaNetwork([1, 1], bits=4)
    lonely = N.KademliaNetwork([3], bits=4)
    assert repr(lonely) == "KademliaNetwork(nodes=1, bits=4, k=8)"
    assert lonely.ids == (3,)
    assert lonely.lookup(3, 12).path == (3,)
    with pytest.raises(ValueError, match="unknown"):
        lonely.buckets(4)


def test_address_manager_edges():
    with pytest.raises(ValueError):
        N.AddressManager(buckets_per_group=0)
    table = N.AddressManager(buckets=1, bucket_size=2, seed=3)
    with pytest.raises(TypeError):
        table.add(b"1.2.3.4", "1.2")  # type: ignore[arg-type]
    for address in ("a", "b", "b", "c"):
        table.add(address, "g")
    assert len(table.addresses) == 2 and "c" in table.addresses  # "c" evicted one entry.
    assert repr(table) == "AddressManager(buckets=1, addresses=2)"
    for _ in range(5):  # Repeated draws of one address are retried.
        assert sorted(table.select(2)) == sorted(table.addresses)
    with pytest.raises(ValueError, match="not enough"):
        table.select(3)
    grouped = N.AddressManager(buckets=8, buckets_per_group=1, seed=3)
    assert len({grouped.bucket_of(f"10.0.0.{i}", "10.0") for i in range(20)}) == 1


def test_relay_and_short_id_validation():
    with pytest.raises(ValueError, match="mode"):
        N.relay_cost(N.complete_graph(3), size=10, mode="push")
    assert N.relay_cost(N.complete_graph(3), size=10, mode="announce") == N.RelayCost(
        4 + 2 * 2, 4 * 61 + 2 * 71, 3
    )
    with pytest.raises(TypeError):
        N.short_id("tx", 0)  # type: ignore[arg-type]
    assert N.short_id(b"tx", 1) != N.short_id(b"tx", 2)  # Salted per block.


def test_fork_rate_validation():
    with pytest.raises(TypeError):
        N.fork_rate("1", 600)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        N.fork_rate(-1, 600)
    with pytest.raises(ValueError):
        N.fork_rate(1, 0)


def test_privacy_validation_and_unreachable_spies():
    graph = N.Graph(4, [(0, 1)])
    with pytest.raises(ValueError, match="proper subset"):
        N.first_spy_precision(graph, set())
    with pytest.raises(ValueError, match="proper subset"):
        N.first_spy_precision(graph, {7})
    with pytest.raises(ValueError, match="mode"):
        N.first_spy_precision(graph, {1}, mode="tor")
    # Peers 2 and 3 cannot reach the spy, so they are never identified.
    assert N.first_spy_precision(graph, {1}, trials=300, seed=1) == pytest.approx(1 / 3, abs=0.1)
    stem = N.first_spy_precision(graph, {1}, mode="dandelion", trials=300, seed=1)
    assert stem == pytest.approx(1 / 3, abs=0.1)  # The stem from 0 always lands on the spy.


def test_from_graph_names_peers_by_node():
    network = N.SimulatedNetwork.from_graph(N.Graph(3, [(0, 2)]), latency=(2, 2))
    network.broadcast("0", b"x")
    network.run()
    assert [(d.recipient, d.time) for d in network.deliveries] == [("0", 0), ("2", 2)]
    assert network.messages_sent == 1
