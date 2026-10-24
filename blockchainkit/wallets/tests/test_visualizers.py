"""Smoke tests for blockchainkit.wallets.visualizers."""

import matplotlib.pyplot as plt
import pytest

from blockchainkit.wallets import detection_rates, romix
from blockchainkit.wallets.visualizers import (
    plot_detection_rates,
    plot_memory_tradeoff,
    plot_recovery_risk,
)


def test_plot_detection_rates_draws_two_bars_per_scheme():
    rates = [detection_rates(s, 2) for s in ("sum", "luhn", "verhoeff")]
    ax = plot_detection_rates(rates)
    assert len(ax.patches) == 6
    assert [t.get_text() for t in ax.get_xticklabels()] == ["sum", "luhn", "verhoeff"]
    _, given = plt.subplots()
    assert plot_detection_rates(rates, ax=given) is given
    with pytest.raises(ValueError, match="no schemes"):
        plot_detection_rates([])


def test_plot_memory_tradeoff_draws_runs_and_the_curve():
    costs = [romix(bytes(range(128)), 16, keep_every=k)[1] for k in (1, 2, 4)]
    ax = plot_memory_tradeoff(costs)
    assert len(ax.lines) == 2 and "N = 16" in ax.get_title()
    _, given = plt.subplots()
    assert plot_memory_tradeoff(costs, ax=given) is given
    with pytest.raises(ValueError, match="no runs"):
        plot_memory_tradeoff([])


def test_plot_recovery_risk_marks_the_single_seed_baseline():
    ax = plot_recovery_risk(5, 0.1, 0.05)
    assert len(ax.lines) == 4 and "5 guardians" in ax.get_title()
    _, given = plt.subplots()
    assert plot_recovery_risk(3, 0.1, 0.05, ax=given) is given
