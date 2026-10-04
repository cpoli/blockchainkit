"""Domain-separated Merkle trees with explicit leaf-count commitments.

Odd nodes are promoted unchanged. Roots bind the leaf count to avoid
ambiguity between differently shaped trees. This is not Bitcoin's format.
"""

from collections.abc import Iterable

from blockchainkit.constants import (
    MERKLE_LEAF_PREFIX,
    MERKLE_NODE_PREFIX,
    MERKLE_ROOT_PREFIX,
    UINT64_LIMIT,
)
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.core.base import MerkleProof


def _root(count: int, digest: bytes) -> bytes:
    return sha256(MERKLE_ROOT_PREFIX + count.to_bytes(8, "big") + digest)


class MerkleTree:
    """Build a tree from an iterable of byte strings.

    Parameters
    ----------
    leaves : iterable of bytes
        Ordered payloads, hashed as SHA256(0x00 || payload).

    Examples
    --------
    >>> from blockchainkit.structures import MerkleTree, verify_proof
    >>> tree = MerkleTree([b"alice", b"bob", b"carol"])
    >>> verify_proof(b"bob", tree.proof(1), tree.root)
    True
    """

    def __init__(self, leaves: Iterable[bytes]) -> None:
        payloads = tuple(leaves)
        if any(not isinstance(leaf, bytes) for leaf in payloads):
            raise TypeError("leaves must be bytes")
        self._count = len(payloads)
        level = tuple(sha256(MERKLE_LEAF_PREFIX + leaf) for leaf in payloads)
        levels = [level]
        while len(level) > 1:
            level = tuple(
                sha256(MERKLE_NODE_PREFIX + level[i] + level[i + 1])
                if i + 1 < len(level)
                else level[i]
                for i in range(0, len(level), 2)
            )
            levels.append(level)
        self._levels = tuple(levels)
        self._root = _root(self._count, level[0] if level else b"")

    def __repr__(self) -> str:
        return f"MerkleTree(leaves={self._count}, root={self._root.hex()[:16]}...)"

    @property
    def root(self) -> bytes:
        """Return the immutable 32-byte, leaf-count-bound root."""
        return self._root

    def proof(self, index: int) -> MerkleProof:
        """Return a logarithmic-size inclusion proof at a zero-based position."""
        if type(index) is not int or not 0 <= index < self._count:
            raise IndexError("leaf index out of range")
        siblings = []
        position = index
        for level in self._levels[:-1]:
            sibling = position ^ 1
            siblings.append(level[sibling] if sibling < len(level) else None)
            position //= 2
        return MerkleProof(index, self._count, tuple(siblings))


def verify_proof(leaf: bytes, proof: MerkleProof, root: bytes) -> bool:
    """Verify payload, position, shape, count, and root; reject malformed proofs."""
    if not isinstance(leaf, bytes) or not isinstance(root, bytes) or len(root) != 32:
        return False
    if not isinstance(proof, MerkleProof):
        return False
    if type(proof.leaf_count) is not int or not 0 < proof.leaf_count < UINT64_LIMIT:
        return False
    if type(proof.index) is not int or not 0 <= proof.index < proof.leaf_count:
        return False
    if not isinstance(proof.siblings, tuple):
        return False
    if len(proof.siblings) != (proof.leaf_count - 1).bit_length():
        return False
    current, index, count = sha256(MERKLE_LEAF_PREFIX + leaf), proof.index, proof.leaf_count
    # The checked path length ensures count > 1 at every iteration, and
    # repeated ceiling-halving reaches exactly 1 after the final sibling.
    for sibling in proof.siblings:
        if (index ^ 1) >= count:
            if sibling is not None:
                return False
        else:
            if not isinstance(sibling, bytes) or len(sibling) != 32:
                return False
            left, right = (sibling, current) if index % 2 else (current, sibling)
            current = sha256(MERKLE_NODE_PREFIX + left + right)
        index //= 2
        count = (count + 1) // 2
    return count == 1 and _root(proof.leaf_count, current) == root
