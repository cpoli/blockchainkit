"""Plotting helpers for blockchainkit.economics.

Imports matplotlib, so ``import blockchainkit`` does not load this module;
import it explicitly: ``from blockchainkit.economics.visualizers import ...``.
"""

from blockchainkit.economics.visualizers.plots import (
    plot_constant_product,
    plot_fee_market,
    plot_gas_auction,
)

__all__ = ["plot_constant_product", "plot_fee_market", "plot_gas_auction"]
