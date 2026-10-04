"""Merkle mountain ranges (2016): an append-only log with cheap updates.

A Merkle tree over n leaves is rebuilt along a whole path when a leaf is
added. A mountain range keeps a list of perfect binary trees ("peaks") of
decreasing size, one per 1-bit of n. Appending a leaf adds a peak of size
one and merges equal-sized neighbours, like binary addition: on average a
constant number of merges. Old peaks are never rewritten, so proofs about
old leaves need only the peaks to be refreshed. The root "bags" the peaks.
"""

from blockchainkit.constants import MERKLE_LEAF_PREFIX, MERKLE_NODE_PREFIX, MMR_ROOT_PREFIX
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.core.base import MMRProof


def _node(left: bytes, right: bytes) -> bytes:
    return sha256(MERKLE_NODE_PREFIX + left + right)


def _bag(size: int, peaks: tuple[bytes, ...]) -> bytes:
    return sha256(MMR_ROOT_PREFIX + size.to_bytes(8, "big") + b"".join(peaks))


def _peak_ranges(size: int) -> list[tuple[int, int]]:
    """(start, leaf count) of each peak, largest first: the 1-bits of ``size``."""
    ranges, start = [], 0
    for bit in reversed(range(size.bit_length())):
        if size >> bit & 1:
            ranges.append((start, 1 << bit))
            start += 1 << bit
    return ranges


class MerkleMountainRange:
    """An immutable append-only accumulator of byte strings.

    Examples
    --------
    >>> from blockchainkit.structures import MerkleMountainRange, verify_mmr_proof
    >>> mmr = MerkleMountainRange()
    >>> for leaf in (b"a", b"b", b"c"):
    ...     mmr = mmr.append(leaf)
    >>> len(mmr.peaks), verify_mmr_proof(b"c", mmr.proof(2), mmr.root)
    (2, True)
    """

    def __init__(self) -> None:
        self._leaves: tuple[bytes, ...] = ()
        self._peaks: tuple[tuple[int, bytes], ...] = ()  # (leaf count, digest)

    def __len__(self) -> int:
        return len(self._leaves)

    def __repr__(self) -> str:
        return f"MerkleMountainRange(leaves={len(self)}, peaks={len(self._peaks)})"

    def append(self, leaf: bytes) -> "MerkleMountainRange":
        """Return a range with one more leaf, merging equal-sized peaks.

        Only the new leaf's hash and the merged nodes are computed: about
        two hashes per append on average, however long the range.
        """
        if not isinstance(leaf, bytes):
            raise TypeError("leaves must be bytes")
        peaks = [*self._peaks, (1, sha256(MERKLE_LEAF_PREFIX + leaf))]
        while len(peaks) > 1 and peaks[-1][0] == peaks[-2][0]:
            (count, left), (_, right) = peaks[-2], peaks[-1]
            peaks[-2:] = [(2 * count, _node(left, right))]
        grown = MerkleMountainRange()
        grown._leaves, grown._peaks = (*self._leaves, leaf), tuple(peaks)
        return grown

    @property
    def peaks(self) -> tuple[bytes, ...]:
        """Peak digests, largest tree first; there is one per 1-bit of the size."""
        return tuple(digest for _, digest in self._peaks)

    @property
    def root(self) -> bytes:
        """Bag the peaks, with the size, into one commitment."""
        return _bag(len(self), self.peaks)

    def proof(self, index: int) -> MMRProof:
        """Return an inclusion proof for the leaf at ``index``."""
        if type(index) is not int or not 0 <= index < len(self):
            raise IndexError("leaf index out of range")
        start, count = next((s, n) for s, n in _peak_ranges(len(self)) if s <= index < s + n)
        level = [sha256(MERKLE_LEAF_PREFIX + leaf) for leaf in self._leaves[start : start + count]]
        position, siblings = index - start, []
        while len(level) > 1:
            siblings.append(level[position ^ 1])
            level = [_node(level[i], level[i + 1]) for i in range(0, len(level), 2)]
            position //= 2
        return MMRProof(index, len(self), tuple(siblings), self.peaks)


def verify_mmr_proof(leaf: bytes, proof: MMRProof, root: bytes) -> bool:
    """Rebuild the leaf's peak, find it among the peaks, and check the bagged root."""
    ranges = _peak_ranges(proof.size)
    if len(proof.peaks) != len(ranges) or _bag(proof.size, proof.peaks) != root:
        return False
    found = [(i, s, n) for i, (s, n) in enumerate(ranges) if s <= proof.index < s + n]
    if not found or not isinstance(leaf, bytes):
        return False
    peak_index, start, count = found[0]
    if len(proof.siblings) != count.bit_length() - 1:
        return False
    current, position = sha256(MERKLE_LEAF_PREFIX + leaf), proof.index - start
    for sibling in proof.siblings:
        current = _node(sibling, current) if position & 1 else _node(current, sibling)
        position //= 2
    return current == proof.peaks[peak_index]
