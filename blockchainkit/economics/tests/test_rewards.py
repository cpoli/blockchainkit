"""Block rewards, the halving, fee-only mining, and mining games."""

import statistics

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.consensus import attacker_success_probability, selfish_mining_revenue
from blockchainkit.economics import (
    block_reward,
    block_subsidy,
    double_spend_incentive,
    honest_mining_is_equilibrium,
    issued_supply,
    mining_gap,
    optimal_mining_revenue,
    simulate_block_rewards,
    undercutting_payoffs,
)
from blockchainkit.economics.systems.rewards import COIN, HALVING_INTERVAL

# Subsidy and supply -----------------------------------------------------------


def test_subsidy_halves_and_stops():
    assert block_subsidy(HALVING_INTERVAL - 1) == 50 * COIN
    assert block_subsidy(4 * HALVING_INTERVAL) == 312_500_000  # The 2024 halving.
    assert block_subsidy(33 * HALVING_INTERVAL - 1) == 1  # 50 BTC >> 32 is 1 satoshi.
    assert block_subsidy(33 * HALVING_INTERVAL) == 0
    assert block_subsidy(64 * HALVING_INTERVAL) == 0
    assert block_reward(0, 1_000) == 50 * COIN + 1_000
    with pytest.raises(ValueError):
        block_reward(0, -1)


def test_issued_supply_converges_below_21_million():
    assert issued_supply(0) == 0
    assert issued_supply(HALVING_INTERVAL) == HALVING_INTERVAL * 50 * COIN
    cap = 2_099_999_997_690_000
    assert issued_supply(33 * HALVING_INTERVAL) == cap
    assert issued_supply(100 * HALVING_INTERVAL) == cap


@given(st.integers(0, 40 * HALVING_INTERVAL))
def test_issued_supply_is_the_sum_of_subsidies(blocks):
    era, offset = divmod(blocks, HALVING_INTERVAL)
    expected = sum(HALVING_INTERVAL * block_subsidy(e * HALVING_INTERVAL) for e in range(era))
    assert issued_supply(blocks) == expected + offset * block_subsidy(blocks)


def test_double_spend_incentive_follows_nakamoto():
    result = double_spend_incentive(0.3, reward=50, payment=100, confirmations=6)
    p = attacker_success_probability(0.3, 6)
    assert result.success_probability == p
    assert result.honest == 350 and result.attack == pytest.approx(p * 450)
    assert not result.attack_pays
    assert double_spend_incentive(0.3, reward=50, payment=10**6, confirmations=6).attack_pays
    majority = double_spend_incentive(0.6, reward=50, payment=100, confirmations=6, devaluation=0.5)
    assert majority.attack == pytest.approx(100 + 175) and not majority.attack_pays
    with pytest.raises(ValueError):
        double_spend_incentive(0.3, reward=0, payment=1, confirmations=1)
    with pytest.raises(ValueError):
        double_spend_incentive(0.3, reward=1, payment=1, confirmations=1, devaluation=2)


# Fee-only mining --------------------------------------------------------------


def test_fee_only_rewards_vary_with_block_intervals():
    subsidized = simulate_block_rewards(6.25, 0.0005, blocks=2_000, seed=1)
    fees_only = simulate_block_rewards(0.0, 0.0005, blocks=2_000, seed=1)
    cv = [statistics.pstdev(r) / statistics.mean(r) for r in (subsidized, fees_only)]
    assert cv[0] < 0.1 < 0.9 < cv[1] < 1.1  # Exponential intervals: coefficient of variation 1.
    assert statistics.mean(fees_only) == pytest.approx(0.3, rel=0.05)


def test_mining_gap_appears_without_a_subsidy():
    assert mining_gap(6.25, 0.0005, 0.3) == 0.0
    assert mining_gap(0.0, 0.0005, 0.3) == pytest.approx(600)
    assert mining_gap(0.1, 0.0005, 0.3) == pytest.approx(400)


def test_undercutting_pays_against_a_whale_block():
    small_tip = undercutting_payoffs(0.2, 1.0, 1.0, kept=0.4)
    assert small_tip["undercut"] < small_tip["honest"]  # Too little to steal.
    stingy = undercutting_payoffs(0.2, 0.5, 1.0, kept=0.5)
    assert stingy["undercut"] == pytest.approx(0.04 * 1.5)  # No one follows: two blocks needed.
    whale = undercutting_payoffs(0.2, 9.0, 1.0, kept=0.8)
    assert whale == pytest.approx({"honest": 0.2, "undercut": 1.6})
    subsidized = undercutting_payoffs(0.2, 9.0, 1.0, kept=0.8, subsidy=100)
    gain = subsidized["undercut"] / subsidized["honest"] - 1
    assert gain < 0.07 < whale["undercut"] / whale["honest"] - 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tip_fees": -1.0},
        {"tip_fees": "1"},
        {"tip_fees": float("inf")},
        {"kept": 1.5},
        {"subsidy": -1.0},
    ],
)
def test_undercutting_validation(kwargs):
    arguments = {"tip_fees": 1.0, "kept": 0.5} | kwargs
    with pytest.raises((ValueError, TypeError)):
        undercutting_payoffs(0.2, arguments.pop("tip_fees"), 1.0, **arguments)


def test_fee_only_validation():
    with pytest.raises(ValueError):
        mining_gap(0.0, 0.0, 1.0)
    with pytest.raises(ValueError):
        simulate_block_rewards(0.0, 1.0, blocks=0)
    with pytest.raises(TypeError):
        simulate_block_rewards(0.0, 1.0, blocks=1, seed=1.0)


# Mining games -----------------------------------------------------------------


def test_small_miners_mine_honestly():
    assert optimal_mining_revenue(0.1, 0.0, max_lead=6) == 0.1
    assert honest_mining_is_equilibrium(0.2, 0.5, max_lead=6)
    assert honest_mining_is_equilibrium(0.3, 0.0, max_lead=6)


def test_large_miners_deviate_and_beat_selfish_mining_eventually():
    assert not honest_mining_is_equilibrium(0.35, 0.0, max_lead=8)
    assert not honest_mining_is_equilibrium(0.3, 0.5, max_lead=8)
    optimal = optimal_mining_revenue(0.3, 0.5, max_lead=10, tolerance=1e-5)
    assert optimal >= selfish_mining_revenue(0.3, 0.5) - 1e-3


def test_a_longer_lead_bound_never_lowers_the_revenue():
    short = optimal_mining_revenue(0.4, 0.0, max_lead=6)
    long = optimal_mining_revenue(0.4, 0.0, max_lead=10)
    assert 0.4 < short <= long + 1e-4


def test_mining_game_validation():
    with pytest.raises(ValueError):
        optimal_mining_revenue(0.5, 0.0)
    with pytest.raises(ValueError):
        optimal_mining_revenue(0.2, 1.5)
    with pytest.raises(ValueError):
        optimal_mining_revenue(0.2, 0.0, max_lead=1)
    with pytest.raises(ValueError):
        optimal_mining_revenue(0.2, 0.0, tolerance=0)
