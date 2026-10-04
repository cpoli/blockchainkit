"""Kademlia routing by XOR distance (Maymounkov and Mazières 2002).

Every node has a ``bits``-bit identifier, and the distance between two
identifiers is their bitwise XOR read as an integer. A node sorts the nodes
it knows into *k-buckets*: bucket ``i`` holds up to ``k`` nodes whose
distance lies in ``[2**i, 2**(i+1))``, the nodes whose identifier first
differs from its own at bit ``i``. Knowing a few nodes at every scale lets a
lookup halve the remaining distance at each hop, so it takes about
``log2 n`` hops among ``n`` nodes.
"""

from collections.abc import Iterable
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.network.core.base import LookupResult


def xor_distance(a: int, b: int) -> int:
    """Kademlia's distance: ``a XOR b``. It is symmetric and zero only for ``a == b``.

    >>> from blockchainkit.network import xor_distance
    >>> xor_distance(0b1010, 0b0110)
    12
    """
    integer(a, "a")
    integer(b, "b")
    return a ^ b


def node_id(key: bytes, bits: int) -> int:
    """Derive a ``bits``-bit identifier from a public key: the top bits of its SHA-256.

    Assigning identifiers by hash means a node cannot simply pick a position
    in the identifier space; it has to search for keys. See the Sybil
    experiment.

    >>> from blockchainkit.network import node_id
    >>> node_id(b"alice", 8) < 2**8
    True
    """
    if not isinstance(key, bytes):
        raise TypeError("key must be bytes")
    integer(bits, "bits", 1)
    if bits > 256:
        raise ValueError("SHA-256 provides at most 256 bits")
    return int.from_bytes(sha256(key), "big") >> (256 - bits)


class KademliaNetwork:
    """Nodes with idealized k-bucket routing tables.

    Parameters
    ----------
    ids : iterable of int
        Distinct node identifiers in ``[0, 2**bits)``.
    bits : int
        Identifier length.
    k : int
        Bucket capacity. Each bucket is filled with up to ``k`` nodes drawn
        uniformly from all nodes at that distance scale.
    seed : int
        Seed for filling the buckets.

    Notes
    -----
    Real Kademlia nodes fill their buckets gradually from the traffic they
    see and prefer long-lived contacts. Here every table is filled at once
    from global knowledge, which isolates the routing geometry.

    Examples
    --------
    >>> from blockchainkit.network import KademliaNetwork
    >>> net = KademliaNetwork([0b000, 0b011, 0b100, 0b110], bits=3, k=1)
    >>> net.lookup(0b000, 0b111).path
    (0, 6)
    """

    def __init__(self, ids: Iterable[int], *, bits: int, k: int = 8, seed: int = 0) -> None:
        integer(bits, "bits", 1)
        integer(k, "k", 1)
        check_seed(seed)
        nodes = tuple(sorted(ids))
        if not nodes:
            raise ValueError("provide at least one node")
        for node in nodes:
            integer(node, "node id")
            if node >= 2**bits:
                raise ValueError(f"node ids must be below 2**{bits}")
        if len(set(nodes)) != len(nodes):
            raise ValueError("node ids must be distinct")
        self._bits, self._k, self._ids = bits, k, nodes
        random = Random(seed)
        self._tables: dict[int, tuple[tuple[int, ...], ...]] = {}
        for node in nodes:
            scales: list[list[int]] = [[] for _ in range(bits)]
            for other in nodes:
                if other != node:
                    scales[(node ^ other).bit_length() - 1].append(other)
            self._tables[node] = tuple(
                tuple(sorted(random.sample(scale, min(k, len(scale))))) for scale in scales
            )

    def __repr__(self) -> str:
        return f"KademliaNetwork(nodes={len(self._ids)}, bits={self._bits}, k={self._k})"

    @property
    def ids(self) -> tuple[int, ...]:
        """Node identifiers in increasing order."""
        return self._ids

    def buckets(self, node: int) -> tuple[tuple[int, ...], ...]:
        """The k-buckets of ``node``; bucket ``i`` holds contacts at distance [2**i, 2**(i+1))."""
        if node not in self._tables:
            raise ValueError("unknown node")
        return self._tables[node]

    def closest(self, target: int, count: int) -> tuple[int, ...]:
        """The ``count`` nodes closest to ``target`` by XOR distance (global truth).

        In Kademlia these nodes store the value with key ``target``.
        """
        integer(target, "target")
        integer(count, "count", 1)
        return tuple(sorted(self._ids, key=lambda node: node ^ target)[:count])

    def lookup(self, source: int, target: int) -> LookupResult:
        """Route greedily from ``source`` toward ``target``.

        At each hop the current node forwards to the contact in its buckets
        closest to ``target``, while that is closer than itself. If the
        current node differs at bit ``i`` from the true closest node, its
        bucket ``i`` is nonempty and every contact there is closer to the
        target, so the route always ends at the closest node.
        """
        integer(target, "target")
        current = source
        path = [current]
        while True:
            contacts = [c for bucket in self.buckets(current) for c in bucket]
            best = min(contacts, key=lambda c: c ^ target, default=current)
            if best ^ target >= current ^ target:
                return LookupResult(tuple(path))
            current = best
            path.append(current)
