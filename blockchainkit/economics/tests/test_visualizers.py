"""Smoke tests for blockchainkit.economics.visualizers."""

import matplotlib.pyplot as plt
import pytest

from blockchainkit.economics import (
    FeeMarketRun,
    GasAuction,
    priority_gas_auction,
    simulate_fee_market,
)
from blockchainkit.economics.visualizers import (
    plot_constant_product,
    plot_fee_market,
    plot_gas_auction,
)


@pytest.mark.parametrize(
    ("mechanism", "label"), [("eip1559", "base fee"), ("first-price", "mean fee paid")]
)
def test_plot_fee_market_draws_fullness_and_price(mechanism, label):
    run = simulate_fee_market([30] * 5, mechanism=mechanism)
    ax = plot_fee_market(run, gas_target=20 * 21_000)
    assert len(ax.patches) == 5 and mechanism in ax.get_title()
    assert label in [text.get_text() for text in ax.get_legend().get_texts()]
    _, given = plt.subplots()
    assert plot_fee_market(run, gas_target=1, ax=given) is given


def test_plot_fee_market_validation():
    empty = FeeMarketRun("eip1559", (), (), (), (), (), (), 0)
    with pytest.raises(ValueError, match="no blocks"):
        plot_fee_market(empty, gas_target=1)
    with pytest.raises(ValueError, match="gas_target"):
        plot_fee_market(simulate_fee_market([1]), gas_target=0)


def test_plot_constant_product_draws_the_curve_and_trades():
    ax = plot_constant_product(100, 400, states=[(120, 334), (90, 445)])
    assert len(ax.lines) == 1 and "40,000" in ax.get_legend().get_texts()[0].get_text()
    _, given = plt.subplots()
    assert plot_constant_product(10, 10, ax=given) is given
    with pytest.raises(ValueError, match="positive"):
        plot_constant_product(0, 10)


def test_plot_gas_auction_marks_each_bot():
    auction = priority_gas_auction(1_000, ["a", "b", "c"])
    ax = plot_gas_auction(auction, opportunity=1_000)
    assert auction.winner in ax.get_title() and len(ax.collections) == 3
    _, given = plt.subplots()
    assert plot_gas_auction(auction, opportunity=1_000, ax=given) is given
    with pytest.raises(ValueError, match="no bids"):
        plot_gas_auction(GasAuction((), "a", 0, 0), opportunity=1)
