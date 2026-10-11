"""Fee markets, priority gas auctions, sandwiches, and proposer-builder separation."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.economics import (
    amount_out,
    next_base_fee,
    priority_gas_auction,
    sandwich_attack,
    sandwich_profit,
    simulate_fee_market,
    simulate_pbs,
)

# EIP-1559 ---------------------------------------------------------------------


def test_base_fee_update_matches_the_specification():
    target = 15_000_000
    assert next_base_fee(10**9, target, target) == 10**9
    assert next_base_fee(10**9, 2 * target, target) == 1_125_000_000
    assert next_base_fee(10**9, 0, target) == 875_000_000
    assert next_base_fee(10**9, target + target // 2, target) == 1_062_500_000
    assert next_base_fee(7, target + 1, target) == 8  # Rounds down to 0, raised to 1.
    assert next_base_fee(0, 0, target) == 0
    with pytest.raises(ValueError, match="gas limit"):
        next_base_fee(10, 2 * target + 1, target)


@given(st.integers(1, 10**12), st.integers(0, 2_000), st.integers(1, 1_000))
def test_base_fee_moves_at_most_one_eighth(base, used, target):
    used = min(used, 2 * target)
    updated = next_base_fee(base, used, target)
    assert base * 7 / 8 - 1 <= updated <= base * 9 / 8 + 1
    assert (updated > base) == (used > target)


def test_the_base_fee_tracks_demand_and_burns():
    arrivals = [20] * 30 + [60] * 40 + [20] * 30
    run = simulate_fee_market(arrivals, seed=2)
    target = 20 * 21_000
    assert run.mechanism == "eip1559" and len(run.base_fees) == 100
    assert max(run.base_fees[30:70]) > 2 * run.base_fees[29]  # The surge prices itself in.
    assert sum(run.gas_used[50:70]) / 20 == pytest.approx(target, rel=0.15)  # Back to target.
    assert all(gas <= 2 * target for gas in run.gas_used)
    assert all(
        b == fee * gas for b, fee, gas in zip(run.burned, run.base_fees, run.gas_used, strict=True)
    )
    assert sum(run.producer_revenue) <= 2 * sum(run.gas_used)  # Tips only: 2 per gas.
    assert run.welfare > 0


def test_first_price_blocks_hold_the_target_and_pay_bids():
    run = simulate_fee_market([60] * 20, mechanism="first-price", seed=2)
    assert set(run.base_fees) == {0} and set(run.burned) == {0}
    assert all(gas == 20 * 21_000 for gas in run.gas_used)
    assert sum(run.producer_revenue) == pytest.approx(sum(p * 20 for p in run.mean_price) * 21_000)
    assert max(run.waiting) > 0


def test_impatient_users_leave_and_empty_blocks_cost_nothing():
    run = simulate_fee_market([200, 0, 0, 0], base_fee=10**6, patience=2, seed=1)
    assert run.gas_used == (0, 0, 0, 0) and run.mean_price == (0.0, 0.0, 0.0, 0.0)
    assert run.waiting == (200, 200, 0, 0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mechanism": "dutch"},
        {"gas_target": 1},
        {"values": (10, 5)},
        {"shading": 1.5},
        {"patience": 0},
        {"tip": -1},
    ],
)
def test_fee_market_validation(kwargs):
    with pytest.raises(ValueError):
        simulate_fee_market([1], **kwargs)
    with pytest.raises(TypeError):
        simulate_fee_market([1.5])


# Priority gas auctions --------------------------------------------------------


def test_bots_bid_away_the_opportunity():
    auction = priority_gas_auction(10_000, ["a", "b", "c"], seed=4)
    fees = [fee for _, fee in auction.bids]
    assert fees == sorted(fees) and fees[0] == 1
    assert all(100 * later >= 110 * earlier for earlier, later in zip(fees, fees[1:], strict=False))
    assert all(x[0] != y[0] for x, y in zip(auction.bids, auction.bids[1:], strict=False))
    assert auction.price + auction.profit == 10_000
    assert auction.profit < 10_000 * 0.1 + 1
    assert (auction.winner, auction.price) == auction.bids[-1]


def test_gas_auction_validation():
    with pytest.raises(ValueError, match="two"):
        priority_gas_auction(10, ["a", "a"])
    with pytest.raises(ValueError, match="two"):
        priority_gas_auction(10, ["a", ""])
    with pytest.raises(ValueError, match="start"):
        priority_gas_auction(10, ["a", "b"], start=11)
    assert priority_gas_auction(1, ["a", "b"]).bids == (
        priority_gas_auction(1, ["a", "b"]).bids[0],
    )


# Sandwiches -------------------------------------------------------------------


def test_sandwich_accounting():
    result = sandwich_profit(1_000_000, 1_000_000, 10_000, 50_000)
    assert result.victim_out < result.victim_out_alone == amount_out(1_000_000, 1_000_000, 10_000)
    assert result.victim_loss > 0 and result.profit > 0
    assert sandwich_profit(1_000_000, 1_000_000, 10_000, 0).victim_loss == 0


def test_the_attack_is_the_most_profitable_one_the_victim_tolerates():
    reserves = (1_000_000, 1_000_000)
    for slippage in (50, 100, 300):
        attack = sandwich_attack(*reserves, 10_000, slippage_bps=slippage)
        floor = attack.victim_out_alone * (10_000 - slippage) // 10_000
        assert attack.victim_out >= floor and attack.profit > 0
        for front_run in range(0, 3 * attack.front_run, max(1, attack.front_run // 50)):
            other = sandwich_profit(*reserves, 10_000, front_run)
            if other.victim_out >= floor:
                assert other.profit <= attack.profit
    capped = sandwich_attack(*reserves, 10_000, slippage_bps=300, budget=1_000)
    assert capped.front_run <= 1_000
    with pytest.raises(ValueError):
        sandwich_attack(10, 10, 1, slippage_bps=10_000)


def test_the_attacker_abstains_when_fees_exceed_the_price_impact():
    attack = sandwich_attack(10_000_000, 10_000_000, 10_000, slippage_bps=500)
    assert attack.front_run == 0 and attack.profit == 0 and attack.victim_loss == 0


# Proposer-builder separation --------------------------------------------------


def test_pbs_equalizes_revenue_per_stake():
    stakes = {"pro": 40, "solo": 10, "home": 10}
    options = {"sophisticated": {"pro"}, "builders": {"b1": 1.0, "b2": 0.95}, "slots": 5_000}
    alone = simulate_pbs(stakes, separated=False, seed=5, **options)
    boosted = simulate_pbs(stakes, seed=5, **options)
    assert alone.slots == boosted.slots and sum(alone.slots.values()) == 5_000
    ratio_alone = alone.revenue_per_stake("pro") / alone.revenue_per_stake("solo")
    ratio_boosted = boosted.revenue_per_stake("pro") / boosted.revenue_per_stake("solo")
    assert ratio_alone > 1.7 and ratio_boosted < 1.15
    assert not alone.separated and boosted.separated


def test_pbs_validation():
    with pytest.raises(ValueError, match="unknown"):
        simulate_pbs({"a": 1}, sophisticated={"b"}, builders={"x": 1, "y": 1}, slots=1)
    with pytest.raises(ValueError, match="two builders"):
        simulate_pbs({"a": 1}, sophisticated=(), builders={"x": 1}, slots=1)
    with pytest.raises(ValueError):
        simulate_pbs({"a": 1}, sophisticated=(), builders={"x": 2, "y": 1}, slots=1)
    lone = simulate_pbs({"a": 1}, sophisticated=(), builders={}, slots=3, separated=False)
    assert lone.revenue["a"] == 3.0
