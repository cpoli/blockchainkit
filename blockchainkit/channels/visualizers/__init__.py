"""Plotting helpers for blockchainkit.channels.

Imports matplotlib, so ``import blockchainkit`` does not load this module;
import it explicitly: ``from blockchainkit.channels.visualizers import ...``.
"""

from blockchainkit.channels.visualizers.plots import plot_detection, plot_route, plot_shares

__all__ = ["plot_detection", "plot_route", "plot_shares"]
