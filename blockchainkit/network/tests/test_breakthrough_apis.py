"""APIs behind the network history: topologies, logical clocks, epidemics,
reliable broadcast, CAP, Kademlia, eclipse attacks, relay, forks, and privacy."""

import itertools
import math
from random import Random

import pytest

import blockchainkit as bk

N = bk.network


# Random, small-world and scale-free graphs ---------------------------------


def test_erdos_renyi_connectivity_jumps_at_log_n_over_n():
    n = 200
    connected = {
        c: sum(N.erdos_renyi(n, c * math.log(n) / n, seed=s).is_connected() for s in range(20))
        for c in (0.5, 2.0)
    }
    assert connected == {0.5: 0, 2.0: 20}


def test_erdos_renyi_edge_count_is_binomial_in_mean():
    edges = [len(N.erdos_renyi(100, 0.1, seed=s).edges) for s in range(20)]
    assert sum(edges) / 20 == pytest.approx(0.1 * 100 * 99 / 2, rel=0.03)


def test_small_world_keeps_clustering_while_paths_shrink():
    lattice = N.watts_strogatz(400, 10, 0.0)
    assert lattice.edges == N.ring_lattice(400, 10).edges
    assert lattice.clustering() == pytest.approx(3 * (10 - 2) / (4 * (10 - 1)))  # 2/3
    rewired = N.watts_strogatz(400, 10, 0.01, seed=1)
    assert rewired.average_path_length() < 0.5 * lattice.average_path_length()
    assert rewired.clustering() > 0.9 * lattice.clustering()
    assert len(rewired.edges) == len(lattice.edges)


def test_scale_free_degrees_have_a_heavy_tail():
    g = N.barabasi_albert(2000, 2, seed=1)
    degrees = g.degrees()
    assert sum(degrees) == 2 * len(g.edges)
    assert min(degrees) == 2 and max(degrees) > 50  # An ER graph of equal density tops out near 12.
    random = N.erdos_renyi(2000, 4 / 1999, seed=1)
    assert max(random.degrees()) < 15


def test_graph_metrics_on_small_known_graphs():
    triangle_plus_tail = N.Graph(4, [(0, 1), (1, 2), (0, 2), (2, 3), (3, 2)])
    assert triangle_plus_tail.edges == ((0, 1), (0, 2), (1, 2), (2, 3))
    assert triangle_plus_tail.clustering() == pytest.approx((1 + 1 + 1 / 3 + 0) / 4)
    assert N.complete_graph(5).average_path_length() == 1.0
    two_parts = N.Graph(5, [(0, 1), (2, 3), (3, 4)])
    assert two_parts.components() == (frozenset({2, 3, 4}), frozenset({0, 1}))
    assert two_parts.distances(0) == (0, 1, None, None, None)
    assert not two_parts.is_connected()
    assert N.Graph(1, []).average_path_length() == 0.0
    assert repr(two_parts) == "Graph(n=5, edges=3)"


# Lamport and vector clocks -------------------------------------------------

HISTORY = [
    [("send", "m1"), ("local", "a"), ("receive", "m3")],
    [("receive", "m1"), ("send", "m2")],
    [("local", "b"), ("receive", "m2"), ("send", "m3")],
]


def test_lamport_clock_condition_and_its_missing_converse():
    stamps = N.lamport_timestamps(HISTORY)
    assert stamps == ((1, 2, 6), (2, 3), (1, 4, 5))
    vectors = N.vector_timestamps(HISTORY)
    # The clock condition: causality implies smaller Lamport time.
    for p, q in itertools.product(range(3), repeat=2):
        for i, j in itertools.product(range(len(HISTORY[p])), range(len(HISTORY[q]))):
            if N.happened_before(vectors[p][i], vectors[q][j]):
                assert stamps[p][i] < stamps[q][j]
    # The converse fails: "a" (time 2) and "b" (time 1) are concurrent.
    assert N.concurrent(vectors[0][1], vectors[2][0])
    assert stamps[2][0] < stamps[0][1]


def test_vector_clocks_characterize_causality():
    vectors = N.vector_timestamps(HISTORY)
    assert vectors[0][2] == (3, 2, 3)
    assert N.happened_before(vectors[0][0], vectors[0][2])  # m1 -> m2 -> m3 -> receive.
    assert not N.concurrent(vectors[1][1], vectors[1][1])


@pytest.mark.parametrize(
    "history,message",
    [
        ([[("shout", "x")]], "known kind"),
        ([["send"]], "known kind"),
        ([[("send", "m"), ("send", "m")]], "sent twice"),
        ([[("send", "m")], [("receive", "m"), ("receive", "m")]], "received twice"),
        ([[("receive", "m")]], "never sent"),
        ([[("receive", "x"), ("send", "y")], [("receive", "y"), ("send", "x")]], "cycle"),
    ],
)
def test_clocks_reject_malformed_histories(history, message):
    with pytest.raises(ValueError, match=message):
        N.lamport_timestamps(history)


def test_happened_before_needs_equal_lengths():
    with pytest.raises(ValueError, match="same length"):
        N.happened_before((1,), (1, 2))


# Epidemic dissemination ----------------------------------------------------


def test_push_needs_about_log2_n_plus_ln_n_rounds():
    for n in (256, 4096):
        rounds = [N.spread_rumor(n, seed=s).rounds for s in range(10)]
        assert abs(sum(rounds) / 10 - N.pittel_rounds(n)) < 2.5


def test_pull_squares_the_residue_and_push_pull_is_fastest():
    runs = {mode: N.spread_rumor(4096, mode=mode, seed=3) for mode in ("push", "pull", "push-pull")}
    assert all(run.complete for run in runs.values())
    assert runs["push-pull"].rounds < runs["pull"].rounds < runs["push"].rounds
    residue = [1 - c / 4096 for c in runs["pull"].informed]
    late = [r for r in range(1, len(residue)) if 0 < residue[r - 1] < 0.5]
    for r in late:  # Pull: an uninformed caller stays uninformed only by calling one.
        assert residue[r] == pytest.approx(residue[r - 1] ** 2, abs=0.02)


def test_rumor_on_a_graph_stops_at_the_component():
    graph = N.Graph(4, [(0, 1), (1, 2)])
    run = N.spread_rumor(graph, mode="push-pull", seed=1)
    assert run.informed[-1] == 3 and not run.complete
    assert N.spread_rumor(10, seed=1, max_rounds=1).informed == (1, 2)


# Byzantine reliable broadcast ----------------------------------------------


def test_bracha_broadcast_agreement_and_totality_within_the_bound():
    for n in range(4, 8):
        t = (n - 1) // 3
        for faulty in itertools.chain.from_iterable(
            itertools.combinations(range(n), f) for f in range(t + 1)
        ):
            for proposals in itertools.product("ab", repeat=n):
                correct = [p for p in range(n) if p not in faulty]
                if 0 not in faulty and len({proposals[p] for p in correct} | {proposals[0]}) > 1:
                    continue
                result = N.reliable_broadcast(n, faulty, list(proposals))
                assert result.agreement and result.totality
                if 0 not in faulty:  # Validity: a correct sender's value is delivered.
                    assert set(result.delivered.values()) == {proposals[0]}


def test_bracha_broadcast_fails_beyond_n_over_three():
    result = N.reliable_broadcast(4, {0, 3}, ["a", "a", "b", "b"])
    assert result.delivered == {1: "a", 2: "b"} and not result.agreement


def test_an_equivocating_sender_can_also_be_ignored_by_everyone():
    result = N.reliable_broadcast(7, {0}, ["a", "a", "a", "a", "b", "b", "b"])
    assert result.totality and set(result.delivered.values()) == {None}
    assert result.messages == 6 * 7  # Only the echoes: no value reached a quorum.


# CAP on a replicated register ----------------------------------------------


def test_consistent_register_refuses_the_minority_side():
    register = N.ReplicatedRegister(5, mode="consistent", initial="v0")
    register.partition([0, 1], [2, 3, 4])
    assert not register.write(0, "left").ok and not register.read(1).ok
    assert register.write(2, "right").ok and register.read(4).value == "right"
    register.heal()
    assert register.read(0).value == "right"
    assert register.values() == ("right",) * 5


def test_available_register_answers_stale_and_loses_a_write():
    register = N.ReplicatedRegister(4, mode="available", initial="v0")
    register.partition([0, 1], [2, 3])
    assert register.write(0, "left").ok
    assert register.read(2).value == "v0"  # Stale.
    register.write(3, "right-1")
    register.write(3, "right-2")
    register.heal()
    assert register.values() == ("right-2",) * 4  # "left" is lost.
    assert [op.kind for op in register.history] == ["write", "read", "write", "write"]


# Kademlia and Sybils ---------------------------------------------------------


def test_kademlia_lookup_always_reaches_the_closest_node_in_few_hops():
    random = Random(1)
    for n in (64, 1024):
        ids = random.sample(range(2**32), n)
        network = N.KademliaNetwork(ids, bits=32, k=2, seed=1)
        hops = []
        for _ in range(100):
            target = random.randrange(2**32)
            result = network.lookup(random.choice(ids), target)
            assert result.found == network.closest(target, 1)[0]
            hops.append(result.hops)
        assert max(hops) <= math.log2(n)


def test_buckets_partition_contacts_by_the_first_differing_bit():
    network = N.KademliaNetwork(range(16), bits=4, k=8)
    for i, bucket in enumerate(network.buckets(5)):
        assert all(2**i <= N.xor_distance(5, c) < 2 ** (i + 1) for c in bucket)
        assert len(bucket) == 2**i


def test_sybils_with_chosen_ids_capture_a_key():
    honest = Random(2).sample(range(2**20), 200)
    key = N.node_id(b"block 7", 20)
    sybils = [key ^ i for i in range(1, 9) if key ^ i not in honest]
    network = N.KademliaNetwork(honest + sybils, bits=20, k=4, seed=1)
    assert set(network.closest(key, len(sybils))) == set(sybils)
    assert network.lookup(honest[0], key).found in sybils


# Eclipse attacks -------------------------------------------------------------


def test_bucketing_by_group_caps_an_attackers_share_of_the_table():
    shares = {}
    for per_group in (None, 4):
        table = N.AddressManager(buckets=64, bucket_size=16, buckets_per_group=per_group, seed=1)
        for i in range(1000):
            table.add(f"h{i}", f"group-{i}")
        for i in range(5000):
            table.add(f"a{i}", f"attacker-{i % 4}")
        addresses = table.addresses
        shares[per_group] = sum(a.startswith("a") for a in addresses) / len(addresses)
        reached = {table.bucket_of(f"a{i}", f"attacker-{i % 4}") for i in range(5000)}
    assert shares[None] > 0.9
    assert len(reached) <= 4 * 4  # Four groups reach at most 16 of 64 buckets.
    assert shares[4] < 0.35
    assert N.eclipse_probability(shares[None], 8) > 0.4
    assert N.eclipse_probability(shares[4], 8) < 1e-3


# Relay ---------------------------------------------------------------------


def test_relay_count_matches_the_simulator_and_announcing_saves_bytes():
    graph = N.erdos_renyi(60, 0.1, seed=2)
    network = N.SimulatedNetwork.from_graph(graph)
    network.broadcast("0", b"block")
    network.run()
    flood = N.relay_cost(graph, size=1_000_000)
    assert flood.messages == network.messages_sent
    assert flood.completion == max(d.time for d in network.deliveries)
    announce = N.relay_cost(graph, size=1_000_000, mode="announce")
    reached = len(network.deliveries)
    assert announce.bytes == flood.messages * 61 + (reached - 1) * (61 + 1_000_000)
    assert announce.bytes < flood.bytes / 4 and announce.completion == 3 * flood.completion


def test_compact_blocks_cost_a_few_bytes_per_known_transaction():
    block = [Random(i).randbytes(250) for i in range(2000)]
    full_mempool = N.compact_block_relay(block, block + [b"other"])
    assert full_mempool.missing == 0 and full_mempool.round_trips == 1
    assert full_mempool.compact_bytes == 80 + 8 + 6 * 2000
    assert full_mempool.full_bytes == 80 + 250 * 2000
    tiny_ids = N.compact_block_relay(block, block, short_id_size=1)
    assert tiny_ids.missing > 1000  # 256 possible IDs cannot name 2000 transactions.


# Propagation and forks -------------------------------------------------------


def test_simulated_fork_rate_matches_the_poisson_formula():
    for delay, interval in ((12.6, 600), (12.6, 15), (2, 10)):
        expected = N.fork_rate(delay, interval)
        measured = N.simulate_fork_rate(delay, interval, blocks=50_000, seed=1)
        assert measured == pytest.approx(expected, abs=0.006)
    assert N.fork_rate(0, 600) == 0.0


# Dandelion -------------------------------------------------------------------


def test_dandelion_hides_the_origin_better_than_diffusion():
    graph = N.watts_strogatz(200, 8, 0.2, seed=4)
    spies = set(Random(5).sample(range(200), 20))
    diffusion = N.first_spy_precision(graph, spies, trials=400, seed=1)
    dandelion = N.first_spy_precision(graph, spies, mode="dandelion", trials=400, seed=1)
    assert dandelion < 0.7 * diffusion
    assert dandelion > 0.05  # A spy next to the origin still catches the first stem hop.
