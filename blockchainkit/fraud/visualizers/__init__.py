"""Plotting helpers for blockchainkit.fraud.

Imports matplotlib, so ``import blockchainkit`` does not load this module;
import it explicitly: ``from blockchainkit.fraud.visualizers import ...``.
"""

from blockchainkit.fraud.visualizers.plots import plot_benford, plot_ponzi, plot_price_spikes

__all__ = ["plot_benford", "plot_ponzi", "plot_price_spikes"]
