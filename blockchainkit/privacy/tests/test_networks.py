"""Tests for mix-nets, onion routing, anonymity sets, and the group helpers."""

from math import log2
from random import Random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.crypto import TEACHING_GROUP as G
from blockchainkit.privacy import (
    MixNode,
    MixRun,
    circuit_compromise_rate,
    effective_anonymity_set,
    entropy_bits,
    equivalence_classes,
    hash_to_group,
    hash_to_scalar,
    k_anonymity,
    keystream_xor,
    match_flows,
    mix_cascade,
    seal,
    simulate_flows,
    wrap,
)


@given(st.binary(max_size=100), st.integers(0, 2**64))
def test_keystream_is_its_own_inverse(data, key):
    assert keystream_xor(key, keystream_xor(key, data, b"t"), b"t") == data


def test_hashes_land_in_the_group_and_depend_on_framing():
    element = hash_to_group(b"t", 1, 2)
    assert 1 < element < G.p and pow(element, G.q, G.p) == 1
    assert hash_to_group(b"t", 1, 2) == element != hash_to_group(b"t", 12)
    assert 0 <= hash_to_scalar(b"t", "x") < G.q


def test_hash_to_group_skips_degenerate_candidates():
    from blockchainkit.crypto import DHGroup

    # In the order-2 subgroup modulo 5, squaring sends half the residues to 1.
    tiny = DHGroup(5, 2, 4)
    assert hash_to_group(b"t", 0, group=tiny) == 4
    assert {hash_to_group(b"t", i, group=tiny) for i in range(20)} == {4}


def test_layers_open_only_for_their_node():
    node, other = MixNode("m", 1234), MixNode("n", 999)
    sealed = seal(b"secret", node.public, 77)
    assert node.open(sealed) == b"secret" and other.open(sealed) != b"secret"
    with pytest.raises(ValueError, match="malformed"):
        node.open(b"\x00" * 8 + b"junk")
    with pytest.raises(ValueError, match="non-empty"):
        MixNode("", 5)


def test_onions_peel_hop_by_hop():
    route = [MixNode(f"m{i}", 100 + i) for i in range(3)]
    onion = wrap(b"hello", route, "bob", Random(1))
    hops = []
    for node in route:
        hop, onion = node.peel(onion)
        hops.append(hop)
    assert hops == ["m1", "m2", "bob"] and onion == b"hello"
    with pytest.raises(ValueError, match="at least one node"):
        wrap(b"x", [], "bob", Random(0))


def test_cascade_delivers_and_shuffles():
    mixes = [MixNode(f"m{i}", 10 + i) for i in range(3)]
    rng = Random(2)
    onions = [wrap(f"msg{i}".encode(), mixes, f"r{i}", rng) for i in range(6)]
    run = mix_cascade(onions, mixes, seed=3)
    assert sorted(run.delivered) == sorted((f"r{i}", f"msg{i}".encode()) for i in range(6))
    for sender in range(6):
        assert run.delivered[run.output_of(sender)] == (f"r{sender}", f"msg{sender}".encode())
        assert run.candidates(sender, frozenset({0, 1, 2})) == {run.output_of(sender)}
        assert run.candidates(sender, frozenset({0, 2})) == set(range(6))
    assert len(run.batches) == 4 and set(run.batches[0]).isdisjoint(run.batches[1])
    with pytest.raises(ValueError, match="at least one mix"):
        mix_cascade(onions, [])
    stray = wrap(b"x", [mixes[0], MixNode("elsewhere", 5)], "r", rng)
    with pytest.raises(ValueError, match="not addressed to the next mix"):
        mix_cascade([stray], mixes)


def test_mix_run_traces_through_corrupt_mixes():
    run = MixRun(((b"a", b"b"), (b"b", b"a")), ((1, 0),), (("x", b"b"), ("y", b"a")))
    assert run.output_of(0) == 1 and run.candidates(0, frozenset({0})) == {1}


def test_circuit_compromise_rate_is_about_f_squared():
    assert circuit_compromise_rate(100, range(20), 20_000, seed=1) == pytest.approx(0.04, abs=0.01)
    assert circuit_compromise_rate(3, {0, 1, 2}, 5) == 1.0
    with pytest.raises(ValueError, match="relay indices"):
        circuit_compromise_rate(5, {7}, 5)


def test_timing_correlation_matches_flows():
    obs = simulate_flows(30, 20, seed=4)
    assert match_flows(obs.entering, obs.leaving) == obs.truth
    assert sorted(obs.truth) == list(range(30))
    with pytest.raises(ValueError, match="no leaving flows"):
        match_flows(obs.entering, [])
    assert match_flows([(0.0, 1.0)], [(0.0, 1.0, 2.0), (5.0, 6.0)]) == (1,)


def test_k_anonymity_and_classes():
    rows = [{"zip": "021*", "age": "30s"}] * 3 + [{"zip": "022*", "age": "40s"}] * 2
    assert equivalence_classes(rows, ["zip", "age"]) == {("021*", "30s"): 3, ("022*", "40s"): 2}
    assert k_anonymity(rows, ["zip"]) == 2
    with pytest.raises(ValueError, match="quasi-identifier"):
        equivalence_classes(rows, [])
    with pytest.raises(ValueError, match="empty"):
        k_anonymity([], ["zip"])


@given(st.integers(1, 64))
def test_uniform_anonymity_set_is_its_size(n):
    assert entropy_bits([1 / n] * n) == pytest.approx(log2(n), abs=1e-9)
    assert effective_anonymity_set([1 / n] * n) == pytest.approx(n)


def test_entropy_rejects_non_distributions():
    assert effective_anonymity_set([1.0, 0.0]) == 1.0
    for bad in ([0.5, 0.6], [-0.5, 1.5]):
        with pytest.raises(ValueError, match="add up to 1"):
            entropy_bits(bad)
