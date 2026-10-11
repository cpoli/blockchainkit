"""Multi-hop payments over a network of channels, with hash time-locked contracts.

Poon and Dryja's paper (2016) also made channels a network. To pay Carol
through Bob, Alice offers Bob an HTLC for the amount plus Bob's fee, and
Bob offers Carol an HTLC for the amount, both locked to the same payment
hash. Carol claims with the preimage, which lets Bob claim from Alice: the
payment completes on every hop or on none. Each hop's expiry must exceed
the next one's by a margin, the ``cltv_delta``, so that a node that learns
the preimage downstream has time to claim upstream.

A sender knows every channel's capacity, which is announced, but not how
it is split between the two sides. It picks a route by capacity and learns
only from failures whether a hop could forward the amount.
"""

from collections import deque
from collections.abc import Mapping
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.channels.core.base import PaymentAttempt, Route
from blockchainkit.network.systems.topology import Graph


class ChannelNetwork:
    """Payment channels on the edges of a :class:`~blockchainkit.network.systems.topology.Graph`.

    Parameters
    ----------
    graph : Graph
        One channel per edge.
    balances : Mapping
        ``balances[u, v]`` is what ``u`` can send to ``v``; both directions of
        every edge are required.
    base_fee : int
        Fee every intermediate node charges per forwarded payment.
    fee_rate : int
        Proportional fee, in millionths of the amount forwarded.
    cltv_delta : int
        Blocks each intermediate node adds to the expiry it is offered.

    Examples
    --------
    >>> from blockchainkit.channels import ChannelNetwork
    >>> from blockchainkit.network import Graph
    >>> line = Graph(3, [(0, 1), (1, 2)])
    >>> network = ChannelNetwork(line, {(0, 1): 500, (1, 0): 500, (1, 2): 500, (2, 1): 500})
    >>> attempt = network.pay(0, 2, 100)
    >>> attempt.success, attempt.route.amounts, attempt.route.expiries
    (True, (101, 100), (49, 9))
    >>> network.balance(1, 2), network.balance(0, 1)
    (400, 399)
    """

    def __init__(
        self,
        graph: Graph,
        balances: Mapping[tuple[int, int], int],
        *,
        base_fee: int = 1,
        fee_rate: int = 1_000,
        cltv_delta: int = 40,
        final_cltv: int = 9,
    ) -> None:
        integer(base_fee, "base_fee")
        integer(fee_rate, "fee_rate")
        integer(cltv_delta, "cltv_delta", 1)
        integer(final_cltv, "final_cltv", 1)
        self.graph = graph
        self.base_fee, self.fee_rate = base_fee, fee_rate
        self.cltv_delta, self.final_cltv = cltv_delta, final_cltv
        self._balances: dict[tuple[int, int], int] = {}
        for u, v in graph.edges:
            for side in ((u, v), (v, u)):
                if side not in balances:
                    raise ValueError(f"missing the balance of {side}")
                integer(balances[side], "balance")
                self._balances[side] = balances[side]
        if len(balances) != len(self._balances):
            raise ValueError("balances given for a pair that is not a channel")

    @classmethod
    def random(
        cls, graph: Graph, *, capacity: int, seed: int = 0, **policy: int
    ) -> "ChannelNetwork":
        """Channels of equal ``capacity``, each split uniformly at random between its two sides."""
        integer(capacity, "capacity", 1)
        check_seed(seed)
        rng = Random(seed)
        balances = {}
        for u, v in graph.edges:
            share = rng.randint(0, capacity)
            balances[u, v], balances[v, u] = share, capacity - share
        return cls(graph, balances, **policy)

    def balance(self, u: int, v: int) -> int:
        """What ``u`` can currently send to ``v``."""
        return self._balances[u, v]

    def capacity(self, u: int, v: int) -> int:
        """The channel's announced capacity: both sides' balances together."""
        return self._balances[u, v] + self._balances[v, u]

    def fee(self, amount: int) -> int:
        """What an intermediate node charges to forward ``amount``."""
        return self.base_fee + amount * self.fee_rate // 1_000_000

    def route(self, nodes: tuple[int, ...], amount: int, *, height: int = 0) -> Route:
        """The amounts and expiries of a payment of ``amount`` along ``nodes``.

        They are computed backwards from the recipient: each intermediate
        node is offered what it forwards plus its fee, and an expiry
        ``cltv_delta`` blocks later than the one it offers.
        """
        integer(amount, "amount", 1)
        integer(height, "height")
        if len(nodes) < 2:
            raise ValueError("a route needs a sender and a recipient")
        for u, v in zip(nodes, nodes[1:], strict=False):
            if (u, v) not in self._balances:
                raise ValueError(f"no channel between {u} and {v}")
        amounts, expiries = [amount], [height + self.final_cltv]
        for _ in nodes[2:]:
            amounts.append(amounts[-1] + self.fee(amounts[-1]))
            expiries.append(expiries[-1] + self.cltv_delta)
        return Route(tuple(nodes), tuple(reversed(amounts)), tuple(reversed(expiries)))

    def find_route(self, source: int, target: int, amount: int, *, height: int = 0) -> Route:
        """The fewest-hop route whose every channel has the capacity for ``amount``.

        Raises
        ------
        ValueError
            No such route exists.
        """
        integer(amount, "amount", 1)
        previous: dict[int, int | None] = {source: None}
        queue = deque([source])
        while queue and target not in previous:
            node = queue.popleft()
            for neighbor in self.graph.neighbors(node):
                if neighbor not in previous and self.capacity(node, neighbor) >= amount:
                    previous[neighbor] = node
                    queue.append(neighbor)
        if target not in previous or source == target:
            raise ValueError(f"no route from {source} to {target} for {amount}")
        path = [target]
        while (step := previous[path[-1]]) is not None:
            path.append(step)
        return self.route(tuple(reversed(path)), amount, height=height)

    def send(self, route: Route, *, known_hash: bool = True) -> PaymentAttempt:
        """Offer the HTLCs hop by hop; settle them all, or fail them all back.

        Parameters
        ----------
        route : Route
            From :meth:`route` or :meth:`find_route`.
        known_hash : bool
            False if the recipient does not know the preimage, as for a probe.
        """
        hops = list(zip(route.nodes, route.nodes[1:], strict=False))
        for (u, v), amount in zip(hops, route.amounts, strict=True):
            if self._balances[u, v] < amount:
                return PaymentAttempt(False, route, (u, v), "temporary_channel_failure")
        if not known_hash:
            return PaymentAttempt(False, route, None, "unknown_payment_hash")
        for (u, v), amount in zip(hops, route.amounts, strict=True):
            self._balances[u, v] -= amount
            self._balances[v, u] += amount
        return PaymentAttempt(True, route, None, None)

    def pay(self, source: int, target: int, amount: int, *, height: int = 0) -> PaymentAttempt:
        """Find a route by capacity and send the payment along it."""
        return self.send(self.find_route(source, target, amount, height=height))
