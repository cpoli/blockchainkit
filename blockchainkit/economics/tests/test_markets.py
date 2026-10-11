"""Auctions, focal points, oracles, and the logarithmic market scoring rule."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.economics import (
    coordination_probability,
    equilibrium_bid,
    expected_revenue,
    first_price_auction,
    lmsr_cost,
    lmsr_max_loss,
    lmsr_prices,
    lmsr_trade,
    optimal_reserve,
    play_coordination,
    schelling_round,
    second_price_auction,
    simulate_revenue,
    virtual_value,
)

# Focal points ---------------------------------------------------------------


def test_coordination_without_salience_is_chance():
    assert coordination_probability(2, 4, 0.0) == pytest.approx(0.25)
    assert coordination_probability(3, 4, 0.0) == pytest.approx(1 / 16)
    assert coordination_probability(5, 1, 0.3) == pytest.approx(1.0)


@given(st.integers(2, 6), st.integers(1, 8), st.floats(0, 1))
def test_coordination_probability_is_a_probability_increasing_in_salience(k, n, s):
    p = coordination_probability(k, n, s)
    assert 0 <= p <= 1 + 1e-12
    assert coordination_probability(k, n, min(1.0, s + 0.1)) >= p - 1e-12


def test_simulated_coordination_matches_the_formula():
    measured = play_coordination(3, 5, 0.5, rounds=20_000, seed=3)
    assert measured == pytest.approx(coordination_probability(3, 5, 0.5), abs=0.01)
    assert play_coordination(2, 3, 0.0, rounds=10, seed=1) == play_coordination(
        2, 3, 0.0, rounds=10, seed=1
    )


@pytest.mark.parametrize(
    ("args", "error"),
    [((1, 3, 0.5), ValueError), ((2, 0, 0.5), ValueError), ((2, 3, 1.5), ValueError)],
)
def test_coordination_rejects_bad_arguments(args, error):
    with pytest.raises(error):
        coordination_probability(*args)
    with pytest.raises(error):
        play_coordination(*args, rounds=1)


def test_play_coordination_validates_rounds_and_seed():
    with pytest.raises(ValueError):
        play_coordination(2, 2, 0.5, rounds=0)
    with pytest.raises(TypeError):
        play_coordination(2, 2, 0.5, rounds=1, seed="x")


# SchellingCoin ----------------------------------------------------------------


def test_schelling_round_rewards_the_interquartile_range():
    reports = {f"honest{i}": 100 + (i % 3) for i in range(9)} | {"liar": 400, "lowball": 10}
    result = schelling_round(reports, reward=2, deposit=5)
    assert result.answer == 101
    assert set(result.penalized) == {"liar", "lowball"}
    assert result.payouts["liar"] == -5 and result.payouts["honest0"] == 2
    assert len(result.rewarded) + len(result.penalized) == len(reports)


def test_a_majority_cartel_moves_the_answer():
    majority = schelling_round({f"h{i}": 100 for i in range(4)} | {f"c{i}": 150 for i in range(5)})
    assert majority.answer == 150 and majority.penalized == ()
    # Above three quarters, the cartel also takes the honest reporters' deposits.
    dominant = schelling_round({f"h{i}": 100 for i in range(2)} | {f"c{i}": 150 for i in range(7)})
    assert dominant.answer == 150 and dominant.penalized == ("h0", "h1")


def test_schelling_round_validation():
    with pytest.raises(ValueError, match="two reports"):
        schelling_round({"a": 1})
    with pytest.raises(TypeError):
        schelling_round({"a": 1, "b": True})
    with pytest.raises(ValueError):
        schelling_round({"a": 1, "b": 2}, reward=0)
    with pytest.raises(ValueError):
        schelling_round({"a": 1, "b": 2}, deposit=-1)


# Auctions ---------------------------------------------------------------------


def test_first_and_second_price_auctions():
    bids = {"alice": 7, "bob": 5, "carol": 3}
    first, second = first_price_auction(bids), second_price_auction(bids)
    assert (first.winner, first.price) == ("alice", 7.0)
    assert (second.winner, second.price) == ("alice", 5.0)
    assert second.utility("bob", 5) == 0.0
    assert dict(second.bids) == bids


def test_ties_go_to_the_first_name_and_reserves_bind():
    assert first_price_auction({"b": 4, "a": 4}).winner == "a"
    assert second_price_auction({"a": 4}).price == 0.0
    assert second_price_auction({"a": 4}, reserve=2.5).price == 2.5
    assert second_price_auction({"a": 4, "b": 3}, reserve=3.5).price == 3.5
    unsold = first_price_auction({"a": 1}, reserve=2)
    assert unsold.winner is None and unsold.price == 0.0


@given(
    st.dictionaries(st.sampled_from("abcde"), st.integers(0, 100), min_size=2),
    st.integers(0, 100),
)
def test_truthful_bidding_is_dominant_in_a_second_price_auction(others, value):
    others = {f"x{name}": bid for name, bid in others.items()}
    truthful = second_price_auction(others | {"me": value}).utility("me", value)
    for deviation in range(0, 101, 7):
        assert second_price_auction(others | {"me": deviation}).utility("me", value) <= truthful


@pytest.mark.parametrize(
    "bids", [{}, {"": 1}, {"a": -1}, {"a": float("inf")}, {"a": True}, {"a": "1"}]
)
def test_auction_rejects_bad_bids(bids):
    with pytest.raises((ValueError, TypeError)):
        second_price_auction(bids)


def test_virtual_value_and_reserve():
    assert virtual_value(0.75) == 0.5 and virtual_value(0.25) == -0.5
    assert optimal_reserve() == 0.5 and optimal_reserve(high=8) == 4
    with pytest.raises(ValueError):
        virtual_value(2.0)
    with pytest.raises(ValueError):
        optimal_reserve(high=0)


def test_equilibrium_bid_shades_and_respects_the_reserve():
    assert equilibrium_bid(0.6, 2) == pytest.approx(0.3)
    assert equilibrium_bid(6, 2, high=10) == pytest.approx(3)
    assert equilibrium_bid(0.5, 2, reserve=0.5) == pytest.approx(0.5)
    assert equilibrium_bid(0.4, 2, reserve=0.5) == 0.0
    assert equilibrium_bid(0.0, 3) == 0.0
    assert equilibrium_bid(0.8, 1) == 0.0  # Alone, a bidder offers the reserve.
    with pytest.raises(ValueError):
        equilibrium_bid(1.5, 2)
    with pytest.raises(ValueError):
        equilibrium_bid(0.5, 2, reserve=2)


def test_expected_revenue_closed_forms():
    for n in range(1, 6):
        assert expected_revenue(n) == pytest.approx((n - 1) / (n + 1))
    assert expected_revenue(1, reserve=0.5) == pytest.approx(0.25)
    assert expected_revenue(3, reserve=5, high=10) == pytest.approx(
        10 * expected_revenue(3, reserve=0.5)
    )
    best = max((expected_revenue(2, reserve=r / 100), r) for r in range(101))
    assert best[1] == 50  # Myerson's reserve maximizes revenue.
    with pytest.raises(ValueError):
        expected_revenue(2, reserve=2)


@pytest.mark.parametrize("reserve", [0.0, 0.5])
def test_revenue_equivalence(reserve):
    theory = expected_revenue(3, reserve=reserve)
    for auction in ("first-price", "second-price"):
        measured = simulate_revenue(auction, 3, rounds=20_000, reserve=reserve, seed=1)
        assert measured == pytest.approx(theory, abs=0.01)


def test_simulate_revenue_rejects_unknown_formats():
    with pytest.raises(ValueError, match="auction"):
        simulate_revenue("dutch", 2, rounds=1)


# LMSR -------------------------------------------------------------------------


@given(st.lists(st.floats(-500, 500), min_size=2, max_size=5), st.floats(1, 200))
def test_lmsr_prices_are_a_distribution_and_the_gradient_of_cost(quantities, b):
    prices = lmsr_prices(quantities, b)
    assert sum(prices) == pytest.approx(1)
    h = 1e-4
    for i, price in enumerate(prices):
        bumped = list(quantities)
        bumped[i] += h
        assert (lmsr_cost(bumped, b) - lmsr_cost(quantities, b)) / h == pytest.approx(
            price, abs=1e-3
        )


def test_lmsr_trades_and_worst_case_loss():
    assert lmsr_cost([0, 0, 0], 50) == pytest.approx(50 * math.log(3))
    assert lmsr_trade([0, 0], 0, 100, 100) == pytest.approx(100 * math.log((1 + math.e) / 2))
    assert lmsr_trade([100, 0], 0, -100, 100) == pytest.approx(-lmsr_trade([0, 0], 0, 100, 100))
    # Buying the winning outcome without limit costs the market maker at most b ln n.
    paid = lmsr_trade([0, 0, 0], 2, 5_000, 100)
    assert 5_000 - paid == pytest.approx(lmsr_max_loss(3, 100), rel=1e-6)
    assert lmsr_cost([10_000, 0], 1) == pytest.approx(10_000)  # No overflow.


def test_lmsr_validation():
    with pytest.raises(ValueError):
        lmsr_prices([1], 10)
    with pytest.raises(TypeError):
        lmsr_cost([1, "2"], 10)
    with pytest.raises(ValueError):
        lmsr_cost([1, 2], 0)
    with pytest.raises(ValueError):
        lmsr_trade([0, 0], 2, 1, 10)
    with pytest.raises(TypeError):
        lmsr_trade([0, 0], 0, None, 10)
    with pytest.raises(ValueError):
        lmsr_max_loss(1, 10)
