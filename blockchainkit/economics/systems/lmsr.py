"""Hanson's logarithmic market scoring rule (2003): a market maker for predictions.

A prediction market pays 1 per share of the outcome that happens. With few
traders, an order book stays empty; Hanson's automated market maker always
quotes a price instead. It tracks the shares ``q_i`` sold of each outcome
and charges for a trade the change in the cost function

.. math::

   C(q) = b \\ln \\sum_i e^{q_i / b},

so the price of outcome ``i`` is the softmax :math:`e^{q_i/b} / \\sum_j e^{q_j/b}`,
and prices always sum to 1: they read as probabilities. The liquidity
parameter ``b`` sets how far a trade moves the price, and bounds the market
maker's worst-case loss by :math:`b \\ln n`: the subsidy it pays for
information. Gnosis's prediction markets used it, and Uniswap's
constant-product pool is a later automated market maker of the same kind:
a formula, not an order book, sets the price.
"""

from collections.abc import Sequence
from math import exp, log

from blockchainkit._validation import integer, positive


def _check(quantities: Sequence[float], liquidity: float) -> None:
    if len(quantities) < 2:
        raise ValueError("a market needs at least two outcomes")
    for q in quantities:
        if isinstance(q, bool) or not isinstance(q, (int, float)):
            raise TypeError("quantities must be real numbers")
    positive(liquidity, "liquidity")


def lmsr_cost(quantities: Sequence[float], liquidity: float) -> float:
    """The cost function :math:`C(q) = b \\ln \\sum_i e^{q_i/b}`, computed without overflow.

    Examples
    --------
    >>> from blockchainkit.economics import lmsr_cost
    >>> round(lmsr_cost([0, 0], 100), 4)  # b ln 2
    69.3147
    """
    _check(quantities, liquidity)
    top = max(quantities)
    return float(top + liquidity * log(sum(exp((q - top) / liquidity) for q in quantities)))


def lmsr_prices(quantities: Sequence[float], liquidity: float) -> tuple[float, ...]:
    """The price of each outcome: the softmax of ``quantities / liquidity``; they sum to 1.

    Examples
    --------
    >>> from blockchainkit.economics import lmsr_prices
    >>> lmsr_prices([0, 0], 100)
    (0.5, 0.5)
    """
    _check(quantities, liquidity)
    top = max(quantities)
    weights = [exp((q - top) / liquidity) for q in quantities]
    total = sum(weights)
    return tuple(w / total for w in weights)


def lmsr_trade(quantities: Sequence[float], outcome: int, shares: float, liquidity: float) -> float:
    """What buying ``shares`` of ``outcome`` costs (negative ``shares`` sell, for a refund).

    Examples
    --------
    >>> from blockchainkit.economics import lmsr_trade
    >>> 50 < lmsr_trade([0, 0], 0, 100, 100) < 100  # Between the old and new price.
    True
    """
    _check(quantities, liquidity)
    integer(outcome, "outcome")
    if outcome >= len(quantities):
        raise ValueError("outcome out of range")
    if isinstance(shares, bool) or not isinstance(shares, (int, float)):
        raise TypeError("shares must be a real number")
    after = list(quantities)
    after[outcome] += shares
    return lmsr_cost(after, liquidity) - lmsr_cost(quantities, liquidity)


def lmsr_max_loss(outcomes: int, liquidity: float) -> float:
    """The market maker's worst-case loss, :math:`b \\ln n`, once the winner is bought up.

    Examples
    --------
    >>> from blockchainkit.economics import lmsr_max_loss
    >>> round(lmsr_max_loss(2, 100), 4)
    69.3147
    """
    integer(outcomes, "outcomes", 2)
    positive(liquidity, "liquidity")
    return float(liquidity * log(outcomes))
