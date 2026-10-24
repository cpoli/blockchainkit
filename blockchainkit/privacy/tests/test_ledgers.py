"""Tests for address clustering, CoinJoin, and Monero traceability."""

import pytest

from blockchainkit.privacy import (
    RingInput,
    TransactionRecord,
    chain_reaction,
    cluster_addresses,
    coinjoin,
    fresh_address,
    guess_newest,
    link_change,
    score_clusters,
    simulate_payments,
    simulate_rings,
    trace_rings,
)


def test_transaction_fee():
    assert TransactionRecord((), (("a", 5),)).fee == 0
    assert TransactionRecord((("a", 5),), (("b", 3),)).fee == 2


def test_fresh_addresses_are_short_and_distinct():
    assert len(fresh_address("x")) == 16 and fresh_address("x") != fresh_address("y")


def test_common_input_ownership_and_change():
    mint = TransactionRecord((), (("a", 5), ("b", 5), ("shop", 1)))
    pay = TransactionRecord((("a", 5), ("b", 5)), (("shop", 7), ("change", 3)))
    clusters = cluster_addresses([mint, pay])
    assert {"a", "b"} in clusters and {"change"} in clusters
    clusters = cluster_addresses([mint, pay], change=True)
    assert clusters[0] == {"a", "b", "change"}
    # Two fresh outputs, or a self-change output, are ambiguous: no change link.
    two_new = TransactionRecord((("a", 5),), (("x", 2), ("y", 3)))
    self_change = TransactionRecord((("a", 5),), (("a", 2), ("z", 3)))
    for tx in (two_new, self_change):
        assert {"a"} in cluster_addresses([tx], change=True)


def test_change_heuristic_beats_inputs_alone_without_false_merges():
    history = simulate_payments(60, 400, reuse=0.9, seed=4)
    plain = score_clusters(cluster_addresses(history.transactions), history.owners)
    change = score_clusters(cluster_addresses(history.transactions, change=True), history.owners)
    assert plain.addresses == change.addresses == len(history.owners)
    assert change.clusters < plain.clusters and change.identified > plain.identified
    assert plain.users == change.users == 60 and change.false_merges == 0


def test_simulated_payments_conserve_value():
    history = simulate_payments(5, 50, reuse=0.0, seed=1)
    assert all(tx.fee == 0 for tx in history.transactions)
    assert sum(len(tx.inputs) == 0 for tx in history.transactions) == 5


def test_poor_payers_skip_their_turn():
    # A payer that spent its last coin without change has nothing left to pay with.
    history = simulate_payments(3, 40, coins=1, seed=2)
    assert len(history.transactions) < 3 + 40


def test_score_clusters_counts_merges_and_identifications():
    owners = {"a": "ann", "b": "ann", "c": "bob", "d": "cat", "e": "cat"}
    score = score_clusters([frozenset("ab"), frozenset("cd"), frozenset("e")], owners)
    assert (score.users, score.clusters, score.false_merges, score.identified) == (3, 3, 1, 1)
    assert score.largest == 2 and score_clusters([], {}).largest == 0


def test_coinjoin_hides_equal_outputs_but_not_change():
    round_ = coinjoin([("ann", "a1", 10), ("bob", "b1", 13), ("cat", "c1", 17)], 10, seed=1)
    tx = round_.transaction
    assert round_.anonymity_set == 3 and tx.fee == 0 and len(tx.outputs) == 5
    links = link_change(tx, 10)
    assert {round_.owners[c] for c in links} == {"bob", "cat"}
    assert all(round_.owners[c] == round_.owners[i] for c, i in links.items())
    merged = score_clusters(cluster_addresses([tx]), round_.owners)
    assert merged.false_merges == 1
    same = coinjoin([("ann", "a1", 13), ("bob", "b1", 13)], 10)
    assert link_change(same.transaction, 10) == {}
    with pytest.raises(ValueError, match="joins once"):
        coinjoin([("ann", "a1", 10), ("ann", "a2", 10)], 10)
    with pytest.raises(ValueError, match="amount"):
        coinjoin([("ann", "a1", 9)], 10)


def test_zero_mixin_rings_trigger_a_chain_reaction():
    rings = [
        RingInput((5,), 5, 10),
        RingInput((5, 7), 7, 11),
        RingInput((7, 8, 9), 9, 12),
        RingInput((1, 2), 2, 13),
    ]
    assert chain_reaction(rings) == {0: 5, 1: 7}
    assert guess_newest(rings) == (5, 7, 9, 2)
    report = trace_rings(rings)
    assert (report.rings, report.zero_mixin, report.deduced, report.newest_correct) == (4, 1, 2, 4)


def test_simulated_rings():
    rings = simulate_rings(2_000, 900, ring_size=2, zero_mixin=0.6, seed=5)
    report = trace_rings(rings)
    assert report.deduced > report.zero_mixin
    assert all(ring.real in ring.members and max(ring.members) < ring.height for ring in rings)
    assert len({ring.real for ring in rings}) == len(rings)
    uniform = trace_rings(simulate_rings(2_000, 500, ring_size=5, seed=1))
    recent = trace_rings(simulate_rings(2_000, 500, ring_size=5, sampling="recent", seed=1))
    assert uniform.newest_correct > 0.8 * 500 and recent.newest_correct < 0.5 * 500
    assert all(len(r.members) == 5 for r in simulate_rings(100, 40, seed=2))
    with pytest.raises(ValueError, match="sampling"):
        simulate_rings(100, 10, sampling="gamma")
    with pytest.raises(ValueError, match="2 \\* inputs"):
        simulate_rings(100, 50)
