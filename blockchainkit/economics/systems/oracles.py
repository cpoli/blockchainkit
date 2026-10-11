"""SchellingCoin (Buterin 2014): a decentralized oracle built on a focal point.

A contract cannot see the outside world, so someone must report facts to it,
such as the price of ether in dollars. SchellingCoin asks many reporters,
each with a deposit, publishes the median, and rewards everyone whose report
fell between the lower and upper quartile; the others lose their deposit.
No reporter can tell what the others will say, so each reports what it
expects them to report, and the truth is the focal answer.

The scheme is only as honest as its majority: a cartel controlling more than
half the reports moves the median, and an attacker who credibly promises
to pay voters for a false answer (the P + epsilon attack) can make lying
the focal point without paying anything if it succeeds.
"""

from collections.abc import Mapping
from statistics import median, quantiles
from types import MappingProxyType

from blockchainkit._validation import positive
from blockchainkit.economics.core.base import OracleRound


def schelling_round(
    reports: Mapping[str, float], *, reward: float = 1.0, deposit: float = 1.0
) -> OracleRound:
    """Publish the median report and pay the reporters between the quartiles.

    Parameters
    ----------
    reports : Mapping
        Each reporter's value; at least two.
    reward : float
        Paid to each reporter within the interquartile range.
    deposit : float
        Lost by each reporter outside it.

    Returns
    -------
    OracleRound

    Examples
    --------
    >>> from blockchainkit.economics import schelling_round
    >>> round_ = schelling_round({"a": 100, "b": 101, "c": 100, "d": 100, "e": 250})
    >>> round_.answer, round_.penalized
    (100, ('e',))
    """
    if len(reports) < 2:
        raise ValueError("a round needs at least two reports")
    for value in reports.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("reports must be real numbers")
    positive(reward, "reward")
    positive(deposit, "deposit")
    values = sorted(reports.values())
    lower, _, upper = quantiles(values, n=4, method="inclusive")
    names = sorted(reports)
    rewarded = tuple(name for name in names if lower <= reports[name] <= upper)
    penalized = tuple(name for name in names if name not in rewarded)
    payouts = {name: reward if name in rewarded else -deposit for name in names}
    return OracleRound(median(values), rewarded, penalized, MappingProxyType(payouts))
