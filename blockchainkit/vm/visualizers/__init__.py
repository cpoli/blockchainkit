"""Plotting helpers for blockchainkit.vm.

Imports matplotlib, so ``import blockchainkit`` does not load this module;
import it explicitly: ``from blockchainkit.vm.visualizers import ...``.
"""

from blockchainkit.vm.visualizers.plots import plot_execution_trace

__all__ = ["plot_execution_trace"]
