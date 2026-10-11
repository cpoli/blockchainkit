"""Price manipulation: the Willy bot (Gandal et al., 2018) and pump-and-dumps (Xu, Livshits 2019).

Thin markets move when someone buys, so whoever can buy without paying,
or can get others to buy at a signal, can move the price.

From February to November 2013, two accounts on Mt. Gox, later known as
the Markus and Willy bots, bought about 600,000 bitcoins without paying for
them. Gandal, Hamrick, Moore and Oberman compared the price on days the
bots traded with the other days and found that they drove much of the rise
from 150 to over 1,000 dollars. :func:`simulate_bot_market` runs such a
market, and :func:`return_by_activity` makes Gandal et al.'s comparison.

In a pump-and-dump, organizers buy a thin coin quietly, then announce it
to a crowd who buy at once; the organizers sell into the rush, and the
crowd is left with the coin as its price collapses. Xu and Livshits studied
hundreds of such pumps organized on Telegram. :func:`simulate_pump_and_dump`
runs one on a constant-product market, and :func:`detect_pumps` flags the
volume and price spike it leaves.
"""

import math
from collections.abc import Collection, Sequence
from random import Random

from blockchainkit._validation import integer, positive
from blockchainkit._validation import seed as check_seed
from blockchainkit.fraud.core.base import MarketRun, PumpRun


def simulate_bot_market(
    days: int,
    bot_days: Collection[int],
    *,
    bot_volume: float = 1.0,
    impact: float = 0.04,
    volatility: float = 0.03,
    opening: float = 100.0,
    seed: int = 0,
) -> MarketRun:
    """Simulate a daily price moved by noise and by a trader buying with money it does not have.

    The log price follows a random walk with daily standard deviation
    ``volatility``; on each day in ``bot_days`` the bot buys a volume drawn
    around ``bot_volume``, which raises the log price by ``impact`` per
    unit of volume (Kyle's linear price impact).

    Returns
    -------
    MarketRun
    """
    integer(days, "days", 1)
    positive(bot_volume, "bot_volume")
    positive(impact, "impact")
    positive(volatility, "volatility")
    positive(opening, "opening")
    check_seed(seed)
    flagged = tuple(sorted(set(bot_days)))
    if any(type(day) is not int or not 0 <= day < days for day in flagged):
        raise ValueError("bot_days must be days in range(days)")
    rng = Random(seed)
    prices, volumes = [float(opening)], []
    for day in range(days):
        volume = bot_volume * rng.uniform(0.5, 1.5) if day in bot_days else 0.0
        volumes.append(volume)
        prices.append(prices[-1] * math.exp(rng.gauss(0.0, volatility) + impact * volume))
    return MarketRun(tuple(prices), tuple(volumes), flagged)


def return_by_activity(prices: Sequence[float], flagged: Collection[int]) -> tuple[float, float]:
    """Mean daily log return on the ``flagged`` days and on the other days.

    Day ``t``'s return is :math:`\\log(p_{t+1}/p_t)`. Each group must have
    at least one day.

    Examples
    --------
    >>> from blockchainkit.fraud import return_by_activity
    >>> import math
    >>> flagged, other = return_by_activity([1, 2, 2, 4], {0, 2})
    >>> round(flagged, 4) == round(math.log(2), 4), other
    (True, 0.0)
    """
    if len(prices) < 2:
        raise ValueError("need at least two prices")
    returns = [math.log(b / a) for a, b in zip(prices, prices[1:], strict=False)]
    marked = [r for day, r in enumerate(returns) if day in flagged]
    other = [r for day, r in enumerate(returns) if day not in flagged]
    if not marked or not other:
        raise ValueError("both groups of days must be non-empty")
    return sum(marked) / len(marked), sum(other) / len(other)


class _Market:
    """A constant-product market between a coin and a quote currency, without fees."""

    def __init__(self, coins: float, quote: float) -> None:
        self.coins, self.quote, self.volume = coins, quote, 0.0

    @property
    def price(self) -> float:
        return self.quote / self.coins

    def buy(self, spend: float) -> float:
        got = self.coins * spend / (self.quote + spend)
        self.coins, self.quote = self.coins - got, self.quote + spend
        self.volume += spend
        return got

    def sell(self, amount: float) -> float:
        got = self.quote * amount / (self.coins + amount)
        self.coins, self.quote = self.coins + amount, self.quote - got
        self.volume += got
        return got


def simulate_pump_and_dump(
    *,
    hours: int = 48,
    pump_hour: int = 24,
    liquidity: float = 10.0,
    organizer_budget: float = 2.0,
    participants: int = 40,
    participant_budget: float = 0.25,
    dump_after: float = 0.4,
    background: float = 0.05,
    seed: int = 0,
) -> PumpRun:
    """Run a pump-and-dump on a constant-product market, one step per hour.

    Every hour a few background traders buy or sell small amounts. In the
    three hours before ``pump_hour`` the organizers buy with
    ``organizer_budget``. At ``pump_hour`` the participants buy in random
    order, each with about ``participant_budget``; once a fraction
    ``dump_after`` of them has bought, the organizers sell everything. In
    the next hour the participants sell, in random order.

    Parameters
    ----------
    hours : int
        Length of the run.
    pump_hour : int
        Hour of the announcement, at least 3 and at most ``hours - 2``.
    liquidity : float
        The market's initial reserve of the quote currency; it starts with
        a million coins.
    organizer_budget, participant_budget : float
        Quote currency each side spends.
    participants : int
        Size of the crowd.
    dump_after : float
        Fraction of the crowd that buys before the organizers sell.
    background : float
        Typical size of a background trade.
    seed : int
        Seeds the background trades and the crowd's order.

    Returns
    -------
    PumpRun
    """
    integer(hours, "hours", 6)
    integer(pump_hour, "pump_hour", 3)
    if pump_hour > hours - 2:
        raise ValueError("pump_hour must leave two hours after it")
    for value, name in (
        (liquidity, "liquidity"),
        (organizer_budget, "organizer_budget"),
        (participant_budget, "participant_budget"),
        (background, "background"),
    ):
        positive(value, name)
    integer(participants, "participants", 1)
    if isinstance(dump_after, bool) or not 0 <= dump_after <= 1:
        raise ValueError("dump_after must be in [0, 1]")
    check_seed(seed)
    rng = Random(seed)
    market = _Market(1_000_000.0, float(liquidity))
    budgets = [participant_budget * rng.uniform(0.5, 1.5) for _ in range(participants)]
    holdings = [0.0] * participants
    proceeds = [0.0] * participants
    organizer_coins = organizer_spent = organizer_got = 0.0
    prices, volumes = [], []
    for hour in range(hours):
        market.volume = 0.0
        for _ in range(3):
            size = background * rng.random()
            if rng.random() < 0.5:
                market.buy(size)
            else:
                market.sell(size / market.price)
        if pump_hour - 3 <= hour < pump_hour:
            organizer_coins += market.buy(organizer_budget / 3)
            organizer_spent += organizer_budget / 3
        if hour == pump_hour:
            order = rng.sample(range(participants), participants)
            dump_at = round(dump_after * participants)
            for buyer in order[:dump_at]:
                holdings[buyer] = market.buy(budgets[buyer])
            organizer_got = market.sell(organizer_coins)
            for buyer in order[dump_at:]:
                holdings[buyer] = market.buy(budgets[buyer])
        if hour == pump_hour + 1:
            for seller in rng.sample(range(participants), participants):
                proceeds[seller] = market.sell(holdings[seller])
        prices.append(market.price)
        volumes.append(market.volume)
    return PumpRun(
        tuple(prices),
        tuple(volumes),
        pump_hour,
        organizer_got - organizer_spent,
        tuple(got - spent for got, spent in zip(proceeds, budgets, strict=True)),
    )


def detect_pumps(
    prices: Sequence[float],
    volumes: Sequence[float],
    *,
    window: int = 12,
    price_jump: float = 0.25,
    volume_ratio: float = 5.0,
) -> tuple[int, ...]:
    """Hours whose volume and price both spike above their recent average.

    Hour ``t`` is flagged if its volume exceeds ``volume_ratio`` times the
    mean of the previous ``window`` hours, and its price exceeds that
    window's mean price by more than ``price_jump``: the anomaly rule of
    Kamps and Kleinberg (2018), applied to closing prices.

    Examples
    --------
    >>> from blockchainkit.fraud import detect_pumps
    >>> detect_pumps([1.0] * 5 + [2.0, 1.0], [1.0] * 5 + [9.0, 1.0], window=3)
    (5,)
    """
    if len(prices) != len(volumes):
        raise ValueError("prices and volumes must have the same length")
    integer(window, "window", 1)
    positive(price_jump, "price_jump")
    positive(volume_ratio, "volume_ratio")
    flagged = []
    for t in range(window, len(prices)):
        mean_volume = sum(volumes[t - window : t]) / window
        mean_price = sum(prices[t - window : t]) / window
        if volumes[t] > volume_ratio * mean_volume and prices[t] > (1 + price_jump) * mean_price:
            flagged.append(t)
    return tuple(flagged)
