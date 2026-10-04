"""The CAP trade-off (Brewer 2000; Gilbert and Lynch 2002) on a replicated register.

A register is copied on several replicas. When the network partitions them,
a replica that cannot reach the others must choose: answer from what it
knows (stay *available*, risking stale reads and lost writes) or refuse
(stay *consistent*). Gilbert and Lynch proved no system can guarantee both
during a partition. A blockchain makes the same choice: Bitcoin keeps
producing blocks on both sides of a split and reconciles later.
"""

from collections.abc import Iterable

from blockchainkit._validation import integer
from blockchainkit.network.core.base import Operation

MODES = ("consistent", "available")
"""tuple of str: The two policies a replica can follow during a partition."""


class ReplicatedRegister:
    """A string register replicated on ``replicas`` nodes that can be partitioned.

    Parameters
    ----------
    replicas : int
        Number of replicas, at least 1; they are numbered from 0.
    mode : {"consistent", "available"}
        ``"consistent"``: a request succeeds only if the contacted replica
        reaches a strict majority, and it then writes to or reads from every
        reachable replica. Any two majorities overlap, so a read sees the
        latest successful write. ``"available"``: every request succeeds
        using the replicas the contacted one can reach.
    initial : str
        The value every replica starts with.

    Notes
    -----
    Every value carries a version ``(counter, replica)``; a write's counter
    is one more than the highest it can see. :meth:`heal` reconnects all
    replicas and keeps the highest version (last writer wins), so in
    available mode a write made on the losing side of a partition is lost.

    Examples
    --------
    >>> from blockchainkit.network import ReplicatedRegister
    >>> register = ReplicatedRegister(3, mode="consistent")
    >>> register.partition([0], [1, 2])
    >>> register.write(0, "x").ok, register.write(1, "y").ok
    (False, True)
    """

    def __init__(self, replicas: int, *, mode: str = "consistent", initial: str = "") -> None:
        integer(replicas, "replicas", 1)
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self._mode = mode
        self._store: list[tuple[tuple[int, int], str]] = [((0, 0), initial)] * replicas
        self._group = [frozenset(range(replicas))] * replicas
        self._history: list[Operation] = []

    def __repr__(self) -> str:
        return f"ReplicatedRegister(replicas={len(self._store)}, mode={self._mode!r})"

    @property
    def history(self) -> tuple[Operation, ...]:
        """Every request so far, in order."""
        return tuple(self._history)

    def values(self) -> tuple[str, ...]:
        """The value each replica currently holds, indexed by replica."""
        return tuple(value for _, value in self._store)

    def partition(self, *groups: Iterable[int]) -> None:
        """Split the replicas into groups that can talk only within themselves.

        The groups must cover every replica exactly once.
        """
        sets = [frozenset(group) for group in groups]
        if sorted(r for group in sets for r in group) != list(range(len(self._store))):
            raise ValueError("groups must cover every replica exactly once")
        for group in sets:
            for replica in group:
                self._group[replica] = group

    def heal(self) -> None:
        """Reconnect every replica and converge on the highest version."""
        self._group = [frozenset(range(len(self._store)))] * len(self._store)
        self._store = [max(self._store)] * len(self._store)

    def _reachable(self, replica: int) -> frozenset[int] | None:
        integer(replica, "replica")
        if replica >= len(self._store):
            raise ValueError("unknown replica")
        group = self._group[replica]
        if self._mode == "consistent" and 2 * len(group) <= len(self._store):
            return None  # No majority: refuse rather than risk inconsistency.
        return group

    def write(self, replica: int, value: str) -> Operation:
        """Ask ``replica`` to store ``value``; return the recorded operation."""
        if not isinstance(value, str):
            raise TypeError("value must be a str")
        group = self._reachable(replica)
        if group is None:
            operation = Operation("write", replica, None, False)
        else:
            counter = max(self._store[r][0][0] for r in group) + 1
            for r in group:
                self._store[r] = ((counter, replica), value)
            operation = Operation("write", replica, value, True)
        self._history.append(operation)
        return operation

    def read(self, replica: int) -> Operation:
        """Ask ``replica`` for the value; return the recorded operation."""
        group = self._reachable(replica)
        if group is None:
            operation = Operation("read", replica, None, False)
        else:
            operation = Operation("read", replica, max(self._store[r] for r in group)[1], True)
        self._history.append(operation)
        return operation
