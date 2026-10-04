"""Smoke tests for blockchainkit.consensus.visualizers."""

import matplotlib.axes
import pytest

import blockchainkit as bk
from blockchainkit.consensus.visualizers import plot_mining_trials, plot_stake_shares


def test_plot_mining_trials_draws_the_expected_curve():
    difficulties = [2, 3, 4, 5]
    attempts = [bk.consensus.mine(bk.structures.Block(difficulty=d)).attempts for d in difficulties]
    ax = plot_mining_trials(difficulties, attempts)
    assert isinstance(ax, matplotlib.axes.Axes)
    assert list(ax.lines[0].get_ydata()) == [4, 8, 16, 32]
    with pytest.raises(ValueError, match="same length"):
        plot_mining_trials([1], [])


def test_plot_stake_shares_compares_fractions():
    stakes = {"a": 1, "b": 3}
    proposers = bk.consensus.StakeSampler(stakes, seed=1).sample(200)
    ax = plot_stake_shares(stakes, proposers)
    heights = [patch.get_height() for patch in ax.patches]
    assert heights[:2] == [0.25, 0.75] and sum(heights[2:]) == pytest.approx(1)
    with pytest.raises(ValueError, match="at least one"):
        plot_stake_shares(stakes, [])
