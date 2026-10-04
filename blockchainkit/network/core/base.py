"""Event records and result containers for blockchainkit.network."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Delivery:
    """First receipt of a byte payload at a peer at integer simulation time."""

    time: int
    sender: str
    recipient: str
    payload: bytes


@dataclass(frozen=True)
class RumorRun:
    """How a rumor spread, round by synchronous round.

    Attributes
    ----------
    informed : tuple of int
        ``informed[r]`` peers knew the rumor after round ``r``;
        ``informed[0]`` is 1, the source.
    n : int
        Number of peers.
    """

    informed: tuple[int, ...]
    n: int

    @property
    def rounds(self) -> int:
        """Rounds played until the run stopped."""
        return len(self.informed) - 1

    @property
    def complete(self) -> bool:
        """True if every peer heard the rumor."""
        return self.informed[-1] == self.n


@dataclass(frozen=True)
class BroadcastResult:
    """Outcome of a Byzantine reliable-broadcast run.

    Attributes
    ----------
    delivered : dict
        Each correct process's delivered value, or None if it delivered nothing.
    agreement : bool
        No two correct processes delivered different values.
    totality : bool
        Either every correct process delivered or none did.
    messages : int
        Messages sent by correct processes.
    """

    delivered: dict[int, str | None]
    agreement: bool
    totality: bool
    messages: int


@dataclass(frozen=True)
class Operation:
    """One client request to a replicated register and its outcome.

    Attributes
    ----------
    kind : str
        ``"read"`` or ``"write"``.
    replica : int
        The replica the client contacted.
    value : str or None
        The value written, or the value read; None if the request failed.
    ok : bool
        False if the replica refused the request to stay consistent.
    """

    kind: str
    replica: int
    value: str | None
    ok: bool


@dataclass(frozen=True)
class LookupResult:
    """Route of a Kademlia lookup.

    Attributes
    ----------
    path : tuple of int
        Node identifiers visited, from the source to the node that answered.
    """

    path: tuple[int, ...]

    @property
    def hops(self) -> int:
        """Number of messages forwarded, one fewer than the nodes on the path."""
        return len(self.path) - 1

    @property
    def found(self) -> int:
        """The node that answered, the closest to the target that the route reached."""
        return self.path[-1]


@dataclass(frozen=True)
class RelayCost:
    """Traffic and time to relay one block from one source to every reachable peer.

    Attributes
    ----------
    messages : int
        Messages of any kind sent.
    bytes : int
        Total bytes sent.
    completion : int
        Time until the last peer has the block, in one-way link latencies.
    """

    messages: int
    bytes: int
    completion: int


@dataclass(frozen=True)
class CompactBlockResult:
    """Bytes needed to relay one block in full and as a compact block (BIP 152).

    Attributes
    ----------
    full_bytes : int
        Header plus every transaction.
    compact_bytes : int
        Header, nonce, short IDs, and the transactions the receiver lacked.
    missing : int
        Transactions the receiver had to request: absent from its mempool, or
        ambiguous because their short ID collided.
    round_trips : int
        1 if the mempool covered the block, 2 if a request was needed.
    """

    full_bytes: int
    compact_bytes: int
    missing: int
    round_trips: int
