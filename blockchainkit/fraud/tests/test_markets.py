"""Wash trading and address poisoning."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.fraud import (
    Flow,
    Trade,
    candidate_address,
    find_wash_trades,
    grind_lookalike,
    looks_alike,
    matched_characters,
    poisoning_suspects,
    simulate_nft_market,
)

# Wash trading -----------------------------------------------------------------


def test_the_ring_is_found_and_dominates_the_volume():
    history = simulate_nft_market(seed=4)
    report = find_wash_trades(history.trades)
    assert set(report.suspicious) == history.wash
    assert frozenset({"ring0", "ring1", "ring2"}) in report.rings
    assert report.volume_share > 0.8


@given(st.integers(0, 50))
def test_every_wash_trade_is_flagged(seed):
    history = simulate_nft_market(honest_trades=100, wash_rounds=3, seed=seed)
    report = find_wash_trades(history.trades)
    assert history.wash <= set(report.suspicious)


def test_cycle_length_bounds_what_counts():
    loop = [Trade(1, "a", "b", 1.0), Trade(1, "b", "c", 1.0), Trade(1, "c", "a", 1.0)]
    assert find_wash_trades(loop, max_length=2).suspicious == ()
    pair = [Trade(2, "x", "y", 3.0), Trade(2, "y", "x", 1.0)]
    report = find_wash_trades(pair + [Trade(3, "p", "q", 4.0)])
    assert report.suspicious == (0, 1) and report.volume_share == 0.5
    assert report.rings == (frozenset({"x", "y"}),)
    empty = find_wash_trades([])
    assert empty.suspicious == () and empty.rings == () and empty.volume_share == 0.0
    with pytest.raises(TypeError):
        find_wash_trades([("t", "a", "b", 1.0)])
    with pytest.raises(ValueError):
        find_wash_trades(loop, max_length=1)


def test_simulated_market_shape():
    history = simulate_nft_market(honest_trades=10, ring_size=2, wash_rounds=2, seed=1)
    assert len(history.trades) == 14 and len(history.wash) == 4
    assert all(history.trades[i].token == 50 for i in history.wash)
    with pytest.raises(ValueError):
        simulate_nft_market(ring_size=1)


# Address poisoning ------------------------------------------------------------


def test_matching_counts_from_each_end():
    a = "0x" + "ab12" + "0" * 32 + "cd34"
    assert matched_characters(a, a) == 8 and not looks_alike(a, a)
    b = "0x" + "ab12" + "1" * 32 + "cd34"
    assert looks_alike(a, b) and looks_alike(a, b[2:])
    c = "0x" + "fb12" + "0" * 32 + "cd30"
    assert matched_characters(a, c) == 0 and matched_characters(a, c, 0, 0) == 0
    with pytest.raises(ValueError, match="cover"):
        matched_characters(a, b, 30, 30)
    for bad in ("0x12", "0x" + "G" * 40):
        with pytest.raises(ValueError, match="40"):
            looks_alike(bad, a)
    with pytest.raises(TypeError):
        looks_alike(5, a)


def test_grinding_finds_a_lookalike_in_about_16_to_the_k_trials():
    target = candidate_address(99, 0)
    found = grind_lookalike(target, prefix=1, suffix=1, seed=5)
    assert looks_alike(found.address, target, 1, 1) and found.matched == 2
    assert found.address == candidate_address(5, found.trials - 1)
    trials = [grind_lookalike(target, prefix=1, suffix=1, seed=s).trials for s in range(200)]
    assert sum(trials) / len(trials) == pytest.approx(256, rel=0.25)
    with pytest.raises(RuntimeError, match="no look-alike"):
        grind_lookalike(target, prefix=4, suffix=4, max_trials=10)


def test_poisoning_suspects_are_dust_senders_resembling_a_payee():
    payee = candidate_address(1, 0)
    lookalike = grind_lookalike(payee, prefix=1, suffix=1).address
    stranger = candidate_address(2, 0)
    flows = [
        Flow(lookalike, "victim", 0, 0),  # Before the victim paid: ignored.
        Flow("victim", payee, 500, 1),
        Flow(lookalike, "victim", 0, 2),
        Flow(lookalike, "victim", 0, 3),
        Flow(stranger, "victim", 0, 4),
        Flow(payee, "victim", 900, 5),
    ]
    assert poisoning_suspects(flows, "victim", prefix=1, suffix=1) == (lookalike,)
    assert poisoning_suspects(flows, "victim", prefix=1, suffix=1, dust=-1) == ()
