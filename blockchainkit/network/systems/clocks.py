"""Logical clocks: Lamport timestamps (1978) and vector clocks (Fidge, Mattern 1988).

Peers have no shared clock, so "which happened first?" has no physical
answer. Lamport defined *happened before* from the messages themselves: an
event precedes later events at the same process, a send precedes its
receive, and the relation is transitive. Two events related neither way are
*concurrent*.

A history is a sequence of processes, each a sequence of events. An event is
a pair ``(kind, label)``: ``("local", name)``, ``("send", message)`` or
``("receive", message)``. Each message label is sent once and received at
most once.
"""

from collections.abc import Sequence

Event = tuple[str, str]
"""``(kind, label)`` with kind ``"local"``, ``"send"`` or ``"receive"``."""

_KINDS = ("local", "send", "receive")


def _schedule(processes: Sequence[Sequence[Event]]) -> list[tuple[int, int]]:
    """Positions ``(process, index)`` in an order where every send precedes its receive."""
    senders: dict[str, tuple[int, int]] = {}
    received: set[str] = set()
    for p, events in enumerate(processes):
        for i, event in enumerate(events):
            if not isinstance(event, tuple) or len(event) != 2 or event[0] not in _KINDS:
                raise ValueError(f"event {event!r} is not (kind, label) with a known kind")
            kind, label = event
            if kind == "send":
                if label in senders:
                    raise ValueError(f"message {label!r} is sent twice")
                senders[label] = (p, i)
            elif kind == "receive":
                if label in received:
                    raise ValueError(f"message {label!r} is received twice")
                received.add(label)
    if missing := received - senders.keys():
        raise ValueError(f"messages received but never sent: {sorted(missing)}")
    done: set[tuple[int, int]] = set()
    order: list[tuple[int, int]] = []
    cursor = [0] * len(processes)
    progress = True
    while progress:
        progress = False
        for p, events in enumerate(processes):
            while cursor[p] < len(events):
                kind, label = events[cursor[p]]
                if kind == "receive" and senders[label] not in done:
                    break  # Wait until the matching send has a timestamp.
                done.add((p, cursor[p]))
                order.append((p, cursor[p]))
                cursor[p] += 1
                progress = True
    if len(order) != sum(len(events) for events in processes):
        raise ValueError("the history has a causal cycle: a receive waits on its own future")
    return order


def lamport_timestamps(processes: Sequence[Sequence[Event]]) -> tuple[tuple[int, ...], ...]:
    """Assign Lamport clock values to every event.

    Each process keeps a counter. It increments the counter before each
    event, attaches it to every message it sends, and on receipt jumps to
    ``max(own, received) + 1``. The result satisfies the *clock condition*:
    if a happened before b, then ``C(a) < C(b)``. The converse does not hold.

    Returns
    -------
    tuple of tuple of int
        ``result[p][i]`` is the timestamp of event ``i`` at process ``p``.

    Examples
    --------
    >>> from blockchainkit.network import lamport_timestamps
    >>> lamport_timestamps([[("send", "m")], [("local", "x"), ("local", "y"), ("receive", "m")]])
    ((1,), (1, 2, 3))
    """
    stamps = [[0] * len(events) for events in processes]
    clock = [0] * len(processes)
    sent: dict[str, int] = {}
    for p, i in _schedule(processes):
        kind, label = processes[p][i]
        if kind == "receive":
            clock[p] = max(clock[p], sent[label])
        clock[p] += 1
        stamps[p][i] = clock[p]
        if kind == "send":
            sent[label] = clock[p]
    return tuple(tuple(row) for row in stamps)


def vector_timestamps(
    processes: Sequence[Sequence[Event]],
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    """Assign vector clock values to every event.

    Each process ``p`` keeps one counter per process. It increments entry
    ``p`` before each event and, on receipt, first takes the entrywise maximum
    with the vector carried by the message. Entry ``q`` of an event's vector
    counts the events at ``q`` that happened before or at it, so vectors
    characterize causality exactly: see :func:`happened_before`.

    Examples
    --------
    >>> from blockchainkit.network import vector_timestamps
    >>> vector_timestamps([[("send", "m")], [("local", "x"), ("receive", "m")]])
    (((1, 0),), ((0, 1), (1, 2)))
    """
    n = len(processes)
    stamps: list[list[tuple[int, ...]]] = [[()] * len(events) for events in processes]
    clock = [[0] * n for _ in range(n)]
    sent: dict[str, tuple[int, ...]] = {}
    for p, i in _schedule(processes):
        kind, label = processes[p][i]
        if kind == "receive":
            clock[p] = [max(a, b) for a, b in zip(clock[p], sent[label], strict=True)]
        clock[p][p] += 1
        stamps[p][i] = tuple(clock[p])
        if kind == "send":
            sent[label] = stamps[p][i]
    return tuple(tuple(row) for row in stamps)


def happened_before(a: Sequence[int], b: Sequence[int]) -> bool:
    """True if the event stamped ``a`` happened before the event stamped ``b``.

    For vector timestamps, ``a -> b`` exactly when ``a <= b`` entrywise and
    ``a != b``.

    >>> from blockchainkit.network import happened_before
    >>> happened_before((1, 0), (1, 2)), happened_before((1, 0), (0, 1))
    (True, False)
    """
    if len(a) != len(b):
        raise ValueError("vector timestamps must have the same length")
    return all(x <= y for x, y in zip(a, b, strict=True)) and tuple(a) != tuple(b)


def concurrent(a: Sequence[int], b: Sequence[int]) -> bool:
    """True if neither vector-stamped event happened before the other (and they differ).

    >>> from blockchainkit.network import concurrent
    >>> concurrent((1, 0), (0, 1))
    True
    """
    return tuple(a) != tuple(b) and not happened_before(a, b) and not happened_before(b, a)
