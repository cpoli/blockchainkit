"""Plotting helpers for blockchainkit.wallets.

Imports matplotlib, so ``import blockchainkit`` does not load this module;
import it explicitly: ``from blockchainkit.wallets.visualizers import ...``.
"""

from blockchainkit.wallets.visualizers.plots import (
    plot_detection_rates,
    plot_memory_tradeoff,
    plot_recovery_risk,
)

__all__ = ["plot_detection_rates", "plot_memory_tradeoff", "plot_recovery_risk"]
