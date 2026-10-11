"""Ponzi schemes, Benford's law, and price manipulation."""

import math
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.contracts import World
from blockchainkit.contracts.core.base import CallRecord, Receipt
from blockchainkit.fraud import (
    ChainPonzi,
    Flow,
    PonziFeatures,
    benford_probability,
    benford_test,
    breakeven_growth,
    chi_square_survival,
    detect_pumps,
    first_digit,
    ponzi_features,
    referral_commissions,
    return_by_activity,
    simulate_bot_market,
    simulate_lending_ponzi,
    simulate_ponzi,
    simulate_pump_and_dump,
    value_flows,
)

# Ponzi's scheme ---------------------------------------------------------------


def test_breakeven_growth_solves_the_survival_condition():
    assert breakeven_growth(0.5) == pytest.approx(0.5)
    g = breakeven_growth(0.5, term=2, skim=0.1)
    assert 0.9 * (1 + g) ** 2 == pytest.approx(1.5)
    with pytest.raises(ValueError, match="keeps everything"):
        breakeven_growth(0.5, skim=1.0)
    with pytest.raises(TypeError):
        breakeven_growth(True)
    with pytest.raises(ValueError):
        breakeven_growth(-0.1)


@given(st.floats(0.0, 1.0), st.integers(1, 4))
def test_growth_above_breakeven_survives_and_below_collapses(r, term):
    g = breakeven_growth(r, term)
    fast = [100 * (1 + g + 0.05) ** t for t in range(30)]
    assert simulate_ponzi(fast, promised_return=r, term=term).survived
    slow = [100 * (1 + g - 0.05) ** t for t in range(80)]
    if g > 0.05:
        assert not simulate_ponzi(slow, promised_return=r, term=term).survived


def test_simulate_ponzi_accounts_for_every_unit():
    run = simulate_ponzi([100, 150, 225, 100], skim=0.0)
    assert run.collapse == 3 and not run.survived
    assert run.raised == 575 and run.repaid == 575 and run.cash[-1] == 0
    assert run.owed[-1] == pytest.approx(1.5 * 575 - 575)
    survived = simulate_ponzi([10, 20, 40], promised_return=1.0)
    assert survived.survived and survived.collapse is None and survived.cash == (10, 10, 10)
    skimmed = simulate_ponzi([100, 200], promised_return=0.5, skim=0.3)
    assert skimmed.cash[0] == pytest.approx(70)


def test_simulate_ponzi_validation():
    with pytest.raises(TypeError):
        simulate_ponzi(["a"])
    with pytest.raises(TypeError):
        simulate_ponzi([True])
    with pytest.raises(ValueError):
        simulate_ponzi([-1])
    with pytest.raises(ValueError):
        simulate_ponzi([math.inf])
    with pytest.raises(ValueError):
        simulate_ponzi([1], term=0)


def test_lending_ponzi_collapses_when_deposits_stop():
    steady = simulate_lending_ponzi([100] * 30)
    assert steady.survived and steady.owed[-1] > 0
    stalled = simulate_lending_ponzi([100] * 30 + [0] * 30)
    assert stalled.collapse == 45 and stalled.cash[-1] == 0
    assert stalled.paid[-1] < 0.05 * stalled.owed[-2] * 1.01 + 1e-9
    no_referrals = simulate_lending_ponzi([100] * 30 + [0] * 30, referral_rates=())
    assert no_referrals.collapse > stalled.collapse
    with pytest.raises(ValueError, match="exceed"):
        simulate_lending_ponzi([1], referral_rates=(0.6, 0.6))
    with pytest.raises(ValueError):
        simulate_lending_ponzi([1], withdrawal_rate=2.0)


def test_referral_commissions_climb_the_tree():
    sponsors = {"b": "a", "c": "b", "d": "c", "e": None}
    earned = referral_commissions(sponsors, {"d": 1000, "e": 50}, rates=(0.1, 0.05, 0.01, 0.5))
    assert earned == pytest.approx({"c": 100, "b": 50, "a": 10})
    assert referral_commissions({}, {"x": 10}) == {}
    assert referral_commissions(sponsors, {"d": 100}, rates=(0.1,)) == pytest.approx({"c": 10})
    with pytest.raises(ValueError):
        referral_commissions({}, {"x": -1})


# Ponzi contracts --------------------------------------------------------------


def _ponzi(investors=10, fee=10):
    world = World()
    for k in range(investors):
        world.fund(f"i{k}", 1_000)
    scheme = world.deploy("owner", ChainPonzi, 200, fee)
    receipts = [world.transact(f"i{k}", scheme, value=100) for k in range(investors)]
    return world, scheme, receipts


def test_chain_ponzi_pays_the_early_from_the_late():
    world, scheme, receipts = _ponzi()
    assert all(r.success for r in receipts)
    assert world.view(scheme, "investors") == 10 and world.view(scheme, "paid") == 4
    assert [world.balance(f"i{k}") for k in range(10)] == [1_100] * 4 + [900] * 6
    assert world.balance("owner") == 100
    assert not world.transact("i0", scheme, "invest").success


def test_chain_ponzi_rejects_bad_parameters():
    world = World()
    from blockchainkit.contracts import ContractError

    for args in ((100, 10), (200, 100), (True, 10)):
        with pytest.raises(ContractError):
            world.deploy("owner", ChainPonzi, *args)


def test_ponzi_features_flag_the_scheme():
    world, scheme, receipts = _ponzi()
    flows = value_flows(receipts)
    features = ponzi_features(flows, scheme, "owner")
    assert features.investors == 10 and features.in_profit == 4
    assert features.paid_from_deposits == 1.0 and features.profit_fraction == 0.4
    assert features.owner_share == pytest.approx(100 / 900)
    assert features.looks_like_ponzi
    assert ponzi_features(flows, scheme).owner_share == 0.0


def test_ponzi_features_of_a_bank_paying_from_its_own_funds():
    flows = [
        Flow("a", "bank", 10, 0),
        Flow("b", "bank", 10, 1),
        Flow("bank", "a", 11, 2),
        Flow("bank", "b", 11, 3),
        Flow("a", "b", 1, 4),  # Not through the bank: ignored.
    ]
    features = ponzi_features(flows, "bank")
    assert features.paid_from_deposits == 0.0 and features.in_profit == 2
    assert not features.looks_like_ponzi
    empty = ponzi_features([], "bank")
    assert empty == PonziFeatures(0, 0, 0.0, 0.0) and empty.profit_fraction == 0.0


def test_value_flows_skip_failed_calls_and_what_they_contained():
    def record(depth, value, error=None, kind="call", sender="s", to="t"):
        return CallRecord(depth, kind, sender, to, to, None, value, 0, error)

    calls = (
        record(0, 5),
        record(1, 7, error="boom"),
        record(2, 9),  # Inside the failed call: undone.
        record(1, 3),
        record(1, 4, kind="delegatecall"),
        record(1, 0),
    )
    good = Receipt(True, None, None, 0, calls, ())
    bad = Receipt(False, None, "x", 0, (record(0, 8),), ())
    assert [f.amount for f in value_flows([bad, good])] == [5, 3]
    assert value_flows([bad, good])[0].transaction == 1


# Benford's law ----------------------------------------------------------------


def test_benford_probabilities_sum_to_one():
    assert sum(benford_probability(d) for d in range(1, 10)) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        benford_probability(10)
    with pytest.raises(ValueError):
        benford_probability(0)


@given(st.floats(1e-300, 1e300))
def test_first_digit_matches_the_decimal_expansion(x):
    assert first_digit(x) == int(f"{x:e}"[0]) or f"{x:e}"[0] == "9"


def test_first_digit_validation_and_rounding():
    assert first_digit(9.9999999999999999) == 1  # Rounds to 10.0.
    assert first_digit(5) == 5
    for bad in (0, -1.0, math.inf, math.nan):
        with pytest.raises(ValueError):
            first_digit(bad)
    with pytest.raises(TypeError):
        first_digit(True)


def test_chi_square_survival_matches_known_quantiles():
    assert chi_square_survival(0.0, 8) == 1.0
    assert chi_square_survival(15.507, 8) == pytest.approx(0.05, abs=1e-4)
    assert chi_square_survival(5.991, 2) == pytest.approx(0.05, abs=1e-4)
    with pytest.raises(ValueError, match="even"):
        chi_square_survival(1.0, 3)
    with pytest.raises(ValueError):
        chi_square_survival(-1.0, 2)


def test_benford_test_separates_natural_from_invented_figures():
    rng = random.Random(1)
    natural = benford_test(rng.lognormvariate(5, 2) for _ in range(5_000))
    invented = benford_test(rng.uniform(1, 9_999) for _ in range(5_000))
    assert natural.conformity in ("close", "acceptable") and natural.p_value > 0.01
    assert invented.conformity == "nonconformity" and invented.p_value < 1e-10
    assert natural.n == 5_000 and sum(natural.proportions) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="empty"):
        benford_test([])


@pytest.mark.parametrize(
    ("mad", "verdict"),
    [(0.004, "close"), (0.01, "acceptable"), (0.014, "marginal"), (0.02, "nonconformity")],
)
def test_nigrini_verdicts(mad, verdict):
    test = benford_test([1.0])
    from dataclasses import replace

    assert replace(test, mad=mad).conformity == verdict


# Manipulation -----------------------------------------------------------------


def test_bot_days_carry_the_rise():
    run = simulate_bot_market(300, set(range(0, 300, 3)), seed=2)
    flagged, other = return_by_activity(run.prices, run.flagged)
    assert flagged > 0.02 > abs(other)
    assert len(run.prices) == 301 and run.volumes[1] == 0.0 < run.volumes[0]
    quiet = simulate_bot_market(10, [], seed=2)
    assert quiet.flagged == () and set(quiet.volumes) == {0.0}
    with pytest.raises(ValueError, match="bot_days"):
        simulate_bot_market(5, [5])
    with pytest.raises(ValueError, match="bot_days"):
        simulate_bot_market(5, [True])


def test_return_by_activity_validation():
    with pytest.raises(ValueError, match="two prices"):
        return_by_activity([1.0], [])
    with pytest.raises(ValueError, match="non-empty"):
        return_by_activity([1.0, 2.0], [])


def test_pump_and_dump_enriches_the_organizers():
    run = simulate_pump_and_dump(seed=1)
    assert run.organizer_profit > 0 and run.losing_participants > len(run.participant_profits) / 2
    assert detect_pumps(run.prices, run.volumes) == (run.pump_hour,)
    total = run.organizer_profit + sum(run.participant_profits)
    assert total < 0.5  # Close to zero-sum: the pool and background traders net the rest.


@pytest.mark.parametrize("dump_after", [0.0, 1.0])
def test_pump_timing_decides_who_wins(dump_after):
    run = simulate_pump_and_dump(dump_after=dump_after, seed=3)
    if dump_after == 0.0:
        assert run.organizer_profit < 0.5  # Selling before the crowd buys gains little.
    else:
        assert run.organizer_profit > simulate_pump_and_dump(seed=3).organizer_profit


def test_pump_and_dump_validation():
    with pytest.raises(ValueError, match="two hours"):
        simulate_pump_and_dump(hours=10, pump_hour=9)
    with pytest.raises(ValueError, match="dump_after"):
        simulate_pump_and_dump(dump_after=1.5)
    with pytest.raises(ValueError, match="dump_after"):
        simulate_pump_and_dump(dump_after=True)
    with pytest.raises(ValueError):
        simulate_pump_and_dump(liquidity=0)


def test_detect_pumps_needs_both_spikes():
    prices = [1.0] * 5 + [2.0, 1.0]
    assert detect_pumps(prices, [1.0] * 7, window=3) == ()
    assert detect_pumps([1.0] * 7, [1.0] * 5 + [9.0, 1.0], window=3) == ()
    with pytest.raises(ValueError, match="same length"):
        detect_pumps([1.0], [1.0, 2.0])
