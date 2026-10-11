"""Wash trading in NFT markets (von Wachter, Jensen, Regner and Ross, 2022).

A wash trade is a sale between parties who are really one: nothing changes
hands except the appearance of demand. On NFT markets it inflates a token's
price history, or earns the trading rewards that some markets paid in
proportion to volume, as LooksRare did in early 2022.

Because every sale is public, wash trading leaves a shape: a token that
passes through a group of accounts and comes back to one that held it
before. Von Wachter et al. flagged such closed cycles in the graph of each
token's trades. :func:`find_wash_trades` flags every trade on a cycle, and
groups the accounts involved into rings, the connected components of a
:class:`~blockchainkit.network.systems.topology.Graph` of who traded with
whom on a cycle.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer, positive
from blockchainkit._validation import seed as check_seed
from blockchainkit.fraud.core.base import Trade, TradeHistory, WashReport
from blockchainkit.network.systems.topology import Graph


def find_wash_trades(trades: Sequence[Trade], *, max_length: int = 4) -> WashReport:
    """Flag every trade on a short cycle that returns a token to an account that held it.

    For each token, trades are taken in order. When the buyer sold the same
    token before, the trades from its latest sale up to this one form a
    cycle; it is flagged if it has at most ``max_length`` trades. Honest
    collectors do sometimes buy back a token, but rarely after only a few
    sales; wash traders pass it around within a small ring.

    Examples
    --------
    >>> from blockchainkit.fraud import Trade, find_wash_trades
    >>> report = find_wash_trades(
    ...     [Trade(1, "a", "b", 5.0), Trade(1, "b", "c", 5.0), Trade(1, "c", "a", 5.0)]
    ... )
    >>> report.suspicious, sorted(report.rings[0])
    ((0, 1, 2), ['a', 'b', 'c'])
    """
    integer(max_length, "max_length", 2)
    history: dict[int, list[int]] = {}
    flagged: set[int] = set()
    for index, trade in enumerate(trades):
        if not isinstance(trade, Trade):
            raise TypeError("trades must be Trade instances")
        earlier = history.setdefault(trade.token, [])
        for position in reversed(range(len(earlier))):
            if trades[earlier[position]].seller == trade.buyer:
                if len(earlier) - position + 1 <= max_length:
                    flagged.update(earlier[position:])
                    flagged.add(index)
                break
        earlier.append(index)
    suspicious = tuple(sorted(flagged))
    accounts = sorted({name for i in suspicious for name in (trades[i].seller, trades[i].buyer)})
    node = {name: n for n, name in enumerate(accounts)}
    graph = Graph(
        max(len(accounts), 1),
        [(node[trades[i].seller], node[trades[i].buyer]) for i in suspicious],
    )
    rings = tuple(
        frozenset(accounts[n] for n in component)
        for component in graph.components()
        if len(component) > 1
    )
    total = sum(trade.price for trade in trades)
    washed = sum(trades[i].price for i in suspicious)
    return WashReport(suspicious, rings, washed / total if total else 0.0)


def simulate_nft_market(
    *,
    tokens: int = 50,
    traders: int = 1_000,
    honest_trades: int = 400,
    ring_size: int = 3,
    wash_rounds: int = 20,
    wash_price: float = 50.0,
    seed: int = 0,
) -> TradeHistory:
    """A market of honest sales with one ring of accounts washing a token among themselves.

    Honest sales move a random token from its owner to a random trader at a
    price around 1. The ring passes its own token around in a cycle,
    ``wash_rounds`` times, at about ``wash_price``, interleaved at random
    with the honest sales.

    Returns
    -------
    TradeHistory
        The trades and which of them are wash trades.
    """
    integer(tokens, "tokens", 1)
    integer(traders, "traders", 2)
    integer(honest_trades, "honest_trades")
    integer(ring_size, "ring_size", 2)
    integer(wash_rounds, "wash_rounds")
    positive(wash_price, "wash_price")
    check_seed(seed)
    rng = Random(seed)
    owners = {token: f"trader{rng.randrange(traders)}" for token in range(tokens)}
    ring = [f"ring{k}" for k in range(ring_size)]
    kinds = ["honest"] * honest_trades + ["wash"] * (wash_rounds * ring_size)
    rng.shuffle(kinds)
    trades: list[Trade] = []
    wash: set[int] = set()
    holder = 0
    for kind in kinds:
        if kind == "wash":
            buyer = (holder + 1) % ring_size
            wash.add(len(trades))
            trades.append(
                Trade(tokens, ring[holder], ring[buyer], wash_price * rng.uniform(0.9, 1.1))
            )
            holder = buyer
        else:
            token = rng.randrange(tokens)
            buyer_name = f"trader{rng.randrange(traders)}"
            while buyer_name == owners[token]:
                buyer_name = f"trader{rng.randrange(traders)}"
            trades.append(Trade(token, owners[token], buyer_name, rng.uniform(0.5, 1.5)))
            owners[token] = buyer_name
    return TradeHistory(tuple(trades), frozenset(wash))
