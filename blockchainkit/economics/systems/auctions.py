"""Sealed-bid auctions: Vickrey (1961) and Myerson (1981).

Vickrey showed that in a *second-price* auction, where the highest bidder
wins but pays the second-highest bid, bidding one's true value is a dominant
strategy: the bid decides only whether one wins, never what one pays. In a
first-price auction, bidders shade their bids below their values, by an
amount that depends on what they believe about the others.

Myerson characterized the auction that maximizes the seller's expected
revenue. Each bidder's value ``v`` is replaced by its *virtual value*
``phi(v) = v - (1 - F(v)) / f(v)``; the item goes to the highest
nonnegative virtual value. For identical bidders this is a second-price
auction with a reserve price ``phi^{-1}(0)``. Myerson also proved *revenue
equivalence*: any two auctions that allocate the item the same way earn the
same expected revenue, so first-price and second-price auctions, without
or with the same reserve, raise the same amount on average.

Values here are drawn independently and uniformly from ``[0, high]``, the
textbook case in which everything has a closed form: ``phi(v) = 2v - high``
and the optimal reserve is ``high / 2``, whatever the number of bidders.
"""

from collections.abc import Mapping
from random import Random
from types import MappingProxyType

from blockchainkit._validation import integer, positive
from blockchainkit._validation import seed as check_seed
from blockchainkit.economics.core.base import AuctionResult


def _real(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    if not 0 <= value < float("inf"):
        raise ValueError(f"{name} must be non-negative and finite")


def _auction(bids: Mapping[str, float], reserve: float, second: bool) -> AuctionResult:
    if not bids:
        raise ValueError("an auction needs at least one bid")
    for name, bid in bids.items():
        if not isinstance(name, str) or not name:
            raise ValueError("bidders must be non-empty names")
        _real(bid, "bid")
    _real(reserve, "reserve")
    ranked = sorted(bids.items(), key=lambda item: (-item[1], item[0]))
    frozen = MappingProxyType(dict(bids))
    winner, top = ranked[0]
    if top < reserve:
        return AuctionResult(None, 0.0, frozen)
    if not second:
        return AuctionResult(winner, float(top), frozen)
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    return AuctionResult(winner, float(max(runner_up, reserve)), frozen)


def first_price_auction(bids: Mapping[str, float], *, reserve: float = 0.0) -> AuctionResult:
    """Sell to the highest bid at or above ``reserve``; the winner pays its own bid.

    Ties go to the alphabetically first bidder.

    Examples
    --------
    >>> from blockchainkit.economics import first_price_auction
    >>> first_price_auction({"alice": 7, "bob": 5}).price
    7.0
    """
    return _auction(bids, reserve, second=False)


def second_price_auction(bids: Mapping[str, float], *, reserve: float = 0.0) -> AuctionResult:
    """Sell to the highest bid at or above ``reserve``, at the larger of the second bid and reserve.

    This is Vickrey's auction; with a reserve, Myerson's optimal one.

    Examples
    --------
    >>> from blockchainkit.economics import second_price_auction
    >>> result = second_price_auction({"alice": 7, "bob": 5})
    >>> result.winner, result.price, result.utility("alice", 7)
    ('alice', 5.0, 2.0)
    """
    return _auction(bids, reserve, second=True)


def virtual_value(value: float, *, high: float = 1.0) -> float:
    """Myerson's virtual value of ``value`` for values uniform on ``[0, high]``: ``2 value - high``.

    It is the marginal revenue of selling to this bidder; a seller gains
    nothing from selling to a bidder whose virtual value is negative.
    """
    positive(high, "high")
    _real(value, "value")
    if value > high:
        raise ValueError("value must not exceed high")
    return float(2 * value - high)


def optimal_reserve(*, high: float = 1.0) -> float:
    """The reserve price of Myerson's optimal auction: the zero of the virtual value, ``high / 2``.

    Examples
    --------
    >>> from blockchainkit.economics import optimal_reserve, virtual_value
    >>> virtual_value(optimal_reserve(high=10), high=10)
    0.0
    """
    positive(high, "high")
    return high / 2


def equilibrium_bid(
    value: float, bidders: int, *, reserve: float = 0.0, high: float = 1.0
) -> float:
    """The symmetric equilibrium bid in a first-price auction with values uniform on ``[0, high]``.

    For ``high = 1``, a bidder with value :math:`v \\ge r` among ``n`` bids
    :math:`v - (v^n - r^n) / (n v^{n-1})`: the expected second-highest value
    given that it wins, so that it pays on average what a second-price
    auction would charge. Below the reserve it does not bid (0 is returned).

    Examples
    --------
    >>> from blockchainkit.economics import equilibrium_bid
    >>> round(equilibrium_bid(0.9, 3), 6)
    0.6
    """
    integer(bidders, "bidders", 1)
    positive(high, "high")
    _real(value, "value")
    _real(reserve, "reserve")
    if value > high or reserve > high:
        raise ValueError("value and reserve must not exceed high")
    v, r, n = value / high, reserve / high, bidders
    if v < r or v == 0:
        return 0.0
    return float(high * (v - (v**n - r**n) / (n * v ** (n - 1))))


def expected_revenue(bidders: int, *, reserve: float = 0.0, high: float = 1.0) -> float:
    """Expected revenue of a first- or second-price auction with values uniform on ``[0, high]``.

    By revenue equivalence both formats earn, for ``high = 1``,
    :math:`n \\left[\\frac{2(1 - r^{n+1})}{n+1} - \\frac{1 - r^n}{n}\\right]`, the
    expected highest nonnegative virtual value; without a reserve this is
    :math:`(n - 1)/(n + 1)`.

    Examples
    --------
    >>> from blockchainkit.economics import expected_revenue
    >>> round(expected_revenue(2), 4), round(expected_revenue(2, reserve=0.5), 4)
    (0.3333, 0.4167)
    """
    integer(bidders, "bidders", 1)
    positive(high, "high")
    _real(reserve, "reserve")
    if reserve > high:
        raise ValueError("reserve must not exceed high")
    n, r = bidders, reserve / high
    return float(high * n * (2 * (1 - r ** (n + 1)) / (n + 1) - (1 - r**n) / n))


def simulate_revenue(
    auction: str,
    bidders: int,
    *,
    rounds: int,
    reserve: float = 0.0,
    high: float = 1.0,
    seed: int = 0,
) -> float:
    """Average revenue over ``rounds`` auctions with values drawn uniformly from ``[0, high]``.

    Parameters
    ----------
    auction : str
        ``"first-price"``, in which everyone bids :func:`equilibrium_bid`, or
        ``"second-price"``, in which everyone bids its value.
    bidders : int
        Bidders per auction.
    rounds : int
        Auctions to simulate.
    reserve : float
        The reserve price.
    high : float
        The highest possible value.
    seed : int
        Simulation seed.

    Returns
    -------
    float
    """
    if auction not in ("first-price", "second-price"):
        raise ValueError('auction must be "first-price" or "second-price"')
    integer(bidders, "bidders", 1)
    integer(rounds, "rounds", 1)
    positive(high, "high")
    _real(reserve, "reserve")
    check_seed(seed)
    rng = Random(seed)
    total = 0.0
    for _ in range(rounds):
        values = [rng.uniform(0, high) for _ in range(bidders)]
        if auction == "first-price":
            bids = {
                f"b{i}": equilibrium_bid(v, bidders, reserve=reserve, high=high)
                for i, v in enumerate(values)
            }
            total += first_price_auction(bids, reserve=reserve).price
        else:
            bids = {f"b{i}": v for i, v in enumerate(values)}
            total += second_price_auction(bids, reserve=reserve).price
    return total / rounds
