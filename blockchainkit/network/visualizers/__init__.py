"""Plotting helpers for blockchainkit.network.

Imports matplotlib, so ``import blockchainkit`` does not load this module;
import it explicitly: ``from blockchainkit.network.visualizers import ...``.
"""

from blockchainkit.network.visualizers.plots import plot_gossip_timeline

__all__ = ["plot_gossip_timeline"]
