"""Block relay: flooding, inv/getdata announcements (Bitcoin 2009), compact blocks (BIP 152, 2016).

Flooding sends the full block over every link. Bitcoin's original protocol
instead *announces* the block's hash with an ``inv`` message and sends the
block only to peers that ask with ``getdata``, so each peer downloads it
once, at the price of a round trip per hop. Compact blocks go further: most
transactions are already in the receiver's mempool, so the sender lists
short transaction IDs and the receiver rebuilds the block locally.
"""

from collections.abc import Iterable, Sequence

from blockchainkit._validation import integer
from blockchainkit.constants import COMPACT_BLOCK_DOMAIN
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.network.core.base import CompactBlockResult, RelayCost
from blockchainkit.network.systems.topology import Graph

HEADER_SIZE = 80
"""int: Bytes in a block header."""

ANNOUNCE_SIZE = 61
"""int: Bytes in an ``inv`` or ``getdata`` for one item: a 24-byte message
header, a one-byte count, and a 36-byte inventory vector."""

MODES = ("flood", "announce")
"""tuple of str: The relay strategies compared by :func:`relay_cost`."""


def relay_cost(graph: Graph, *, size: int, mode: str = "flood", source: int = 0) -> RelayCost:
    """Count the traffic to relay a ``size``-byte block from ``source`` to its component.

    Every peer, on first receiving the block, passes it on to each neighbor
    except the one it came from, so ``2E - (n - 1)`` messages cross the
    links of a connected graph with E edges and n peers.

    * ``"flood"``: each such message carries the whole block, and the block
      reaches a peer at distance d after d link latencies.
    * ``"announce"``: each such message is an ``inv``; a peer that lacks the
      block answers its first ``inv`` with a ``getdata`` and receives the
      block. Every peer downloads the block once, but each hop costs three
      latencies.

    Examples
    --------
    >>> from blockchainkit.network import complete_graph, relay_cost
    >>> relay_cost(complete_graph(10), size=1_000_000).bytes
    81000000
    """
    integer(size, "size", 1)
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    distances = graph.distances(source)
    reached = [node for node, d in enumerate(distances) if d is not None]
    forwards = sum(graph.degrees()[node] for node in reached) - (len(reached) - 1)
    depth = max(d for d in distances if d is not None)
    if mode == "flood":
        return RelayCost(forwards, forwards * size, depth)
    downloads = len(reached) - 1
    return RelayCost(
        forwards + 2 * downloads,
        forwards * ANNOUNCE_SIZE + downloads * (ANNOUNCE_SIZE + size),
        3 * depth,
    )


def short_id(transaction: bytes, nonce: int, size: int = 6) -> bytes:
    """A ``size``-byte transaction ID salted by the block's ``nonce``.

    Salting with a per-block nonce stops an attacker from crafting
    transactions whose short IDs collide in every block. BIP 152 uses
    SipHash keyed by the header and nonce; this teaching version uses
    SHA-256.

    >>> from blockchainkit.network import short_id
    >>> len(short_id(b"tx", nonce=7))
    6
    """
    if not isinstance(transaction, bytes):
        raise TypeError("transaction must be bytes")
    integer(nonce, "nonce")
    integer(size, "size", 1)
    return sha256(COMPACT_BLOCK_DOMAIN + nonce.to_bytes(8, "big") + sha256(transaction))[:size]


def compact_block_relay(
    block: Sequence[bytes],
    mempool: Iterable[bytes],
    *,
    nonce: int = 0,
    short_id_size: int = 6,
) -> CompactBlockResult:
    """Compare sending ``block`` in full with sending it as a compact block.

    The compact form costs the header, an 8-byte nonce, and one short ID
    per transaction. The receiver matches short IDs against its mempool.
    A transaction with no match, or with an ambiguous or wrong match, must
    be requested in a second round trip: a request of ``ANNOUNCE_SIZE``
    bytes plus 2 bytes per index, then the transactions themselves.

    Examples
    --------
    >>> from blockchainkit.network import compact_block_relay
    >>> block = [bytes([i]) * 250 for i in range(100)]
    >>> result = compact_block_relay(block, block[:90])
    >>> result.missing, result.round_trips, result.full_bytes
    (10, 2, 25080)
    """
    integer(short_id_size, "short_id_size", 1)
    pool: dict[bytes, list[bytes]] = {}
    for transaction in set(mempool):
        pool.setdefault(short_id(transaction, nonce, short_id_size), []).append(transaction)
    missing = [
        transaction
        for transaction in block
        if pool.get(short_id(transaction, nonce, short_id_size)) != [transaction]
    ]
    compact = HEADER_SIZE + 8 + short_id_size * len(block)
    if missing:
        compact += ANNOUNCE_SIZE + 2 * len(missing) + sum(len(tx) for tx in missing)
    return CompactBlockResult(
        HEADER_SIZE + sum(len(tx) for tx in block), compact, len(missing), 2 if missing else 1
    )
