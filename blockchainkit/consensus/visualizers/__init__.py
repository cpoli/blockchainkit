"""Plotting helpers for blockchainkit.consensus.

Imports matplotlib, so ``import blockchainkit`` does not load this module;
import it explicitly: ``from blockchainkit.consensus.visualizers import ...``.
"""

from blockchainkit.consensus.visualizers.plots import plot_mining_trials, plot_stake_shares

__all__ = ["plot_mining_trials", "plot_stake_shares"]
