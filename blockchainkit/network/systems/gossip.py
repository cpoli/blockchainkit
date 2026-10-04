"""Deterministic discrete-event gossip; no sockets, wall clock, or background threads."""

import heapq
from collections.abc import Callable, Iterable
from random import Random
from typing import TYPE_CHECKING

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.crypto import sha256
from blockchainkit.network.core.base import Delivery

if TYPE_CHECKING:
    from blockchainkit.network.systems.topology import Graph


class SimulatedNetwork:
    """An undirected peer graph with seeded link delays and duplicate suppression.

    Parameters
    ----------
    peers : iterable of str
        Unique nonempty peer names. Initially no links exist.
    seed : int
        Private PRNG seed; construction does not modify global randomness.
    on_receive : callable, optional
        Callback for each first delivery, including the originating peer.
        Return False to reject that payload at that peer and stop forwarding.
        Returning None or True accepts it. Rejections remain seen.

    Notes
    -----
    Disconnecting a link drops its in-flight messages. Reconnecting does not
    automatically synchronize old data: call ``broadcast`` again. Latency is
    sampled at send time, inclusive of both endpoints, and is at least one tick.
    """

    def __init__(
        self,
        peers: Iterable[str],
        *,
        seed: int = 0,
        on_receive: Callable[[Delivery], bool | None] | None = None,
    ) -> None:
        check_seed(seed)
        names = tuple(peers)
        if not names or any(not isinstance(name, str) or not name for name in names):
            raise ValueError("provide nonempty peer names")
        if len(set(names)) != len(names):
            raise ValueError("peer names must be unique")
        self._links: dict[tuple[str, str], tuple[int, int, int]] = {}
        self._seen: dict[str, set[bytes]] = {name: set() for name in sorted(names)}
        self._accepted: dict[str, set[bytes]] = {name: set() for name in sorted(names)}
        self._queue: list[tuple[int, int, str, str, bytes, int]] = []
        self._deliveries: list[Delivery] = []
        self._random = Random(seed)
        self._callback = on_receive
        self._time = 0
        self._serial = 0
        self._generation = 0
        self._sent = 0

    @classmethod
    def from_graph(
        cls,
        graph: "Graph",
        *,
        latency: tuple[int, int] = (1, 1),
        seed: int = 0,
        on_receive: Callable[[Delivery], bool | None] | None = None,
    ) -> "SimulatedNetwork":
        """Build a network whose peers ``"0"``, ``"1"``, ... are linked like ``graph``.

        >>> from blockchainkit.network import SimulatedNetwork, ring_lattice
        >>> SimulatedNetwork.from_graph(ring_lattice(8, 2))
        SimulatedNetwork(peers=8, links=8, time=0, pending=0)
        """
        network = cls((str(node) for node in range(graph.n)), seed=seed, on_receive=on_receive)
        for left, right in graph.edges:
            network.connect(str(left), str(right), latency=latency)
        return network

    def __repr__(self) -> str:
        return (
            f"SimulatedNetwork(peers={len(self._seen)}, links={len(self._links)}, "
            f"time={self._time}, pending={len(self._queue)})"
        )

    @property
    def time(self) -> int:
        """Current simulated tick."""
        return self._time

    @property
    def deliveries(self) -> tuple[Delivery, ...]:
        """Immutable snapshot of accepted first deliveries."""
        return tuple(self._deliveries)

    @property
    def messages_sent(self) -> int:
        """Messages handed to links so far, including duplicates that receivers discard."""
        return self._sent

    @property
    def pending(self) -> int:
        """Number of queued events, including events invalidated by disconnection."""
        return len(self._queue)

    def _key(self, left: str, right: str) -> tuple[str, str]:
        if left not in self._seen or right not in self._seen or left == right:
            raise ValueError("link endpoints must be distinct known peers")
        return (left, right) if left < right else (right, left)

    def connect(self, left: str, right: str, *, latency: tuple[int, int] = (1, 1)) -> None:
        """Create or replace a link with inclusive integer latency bounds."""
        key = self._key(left, right)
        low, high = latency
        integer(low, "minimum latency", 1)
        integer(high, "maximum latency", low)
        self._generation += 1
        self._links[key] = (low, high, self._generation)

    def disconnect(self, left: str, right: str) -> None:
        """Remove a link, invalidating all in-flight events sent on that link."""
        self._links.pop(self._key(left, right), None)

    def _forward(self, sender: str, payload: bytes, *, exclude: str | None = None) -> None:
        for recipient in self._seen:
            if recipient in (sender, exclude):
                continue
            link = self._links.get(self._key(sender, recipient))
            if link is not None:
                low, high, generation = link
                self._serial += 1
                self._sent += 1
                heapq.heappush(
                    self._queue,
                    (
                        self.time + self._random.randint(low, high),
                        self._serial,
                        sender,
                        recipient,
                        payload,
                        generation,
                    ),
                )

    def _receive(self, sender: str, recipient: str, payload: bytes) -> bool:
        digest = sha256(payload)
        if digest in self._seen[recipient]:
            return False
        # Mark the payload seen before the callback runs, so a callback that
        # rebroadcasts it cannot recurse; undo the mark if the callback fails.
        self._seen[recipient].add(digest)
        delivery = Delivery(self.time, sender, recipient, payload)
        try:
            verdict = None if self._callback is None else self._callback(delivery)
        except BaseException:
            self._seen[recipient].discard(digest)
            raise
        if verdict is False:
            return False
        self._accepted[recipient].add(digest)
        self._deliveries.append(delivery)
        self._forward(recipient, payload, exclude=sender)
        return True

    def broadcast(self, sender: str, payload: bytes) -> None:
        """Originate or retransmit bytes to neighbors; receivers suppress duplicates."""
        if sender not in self._seen:
            raise ValueError("unknown sender")
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")
        if sha256(payload) in self._seen[sender]:
            if sha256(payload) in self._accepted[sender]:
                self._forward(sender, payload)
        else:
            self._receive(sender, sender, payload)

    def run(self, *, until: int | None = None, max_events: int = 100_000) -> int:
        """Process queued events up to a time/event bound; return events processed.

        With until set, the clock advances to that tick if the event budget
        was not exhausted. Events after until remain queued for a later run.
        """
        integer(max_events, "max_events", 1)
        if until is not None:
            integer(until, "until", self.time)
        processed = 0
        while self._queue and processed < max_events:
            if until is not None and self._queue[0][0] > until:
                break
            time, _, sender, recipient, payload, generation = heapq.heappop(self._queue)
            self._time = time
            processed += 1
            link = self._links.get(self._key(sender, recipient))
            if link is not None and link[2] == generation:
                self._receive(sender, recipient, payload)
        if until is not None and (not self._queue or self._queue[0][0] > until):
            self._time = until
        return processed
