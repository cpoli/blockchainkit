"""Sparse Merkle trees (2016): a key-value map with membership and non-membership proofs.

Picture a Merkle tree with one leaf for every possible 256-bit key, almost
all empty. Each key's position is fixed by its hash, so the root is
independent of insertion order, and absence is provable: show that the leaf
at the key's position is empty. Empty subtrees have precomputed default
digests, so only paths to non-empty leaves are ever hashed.
"""

from functools import cache, cached_property

from blockchainkit._validation import integer
from blockchainkit.constants import MERKLE_LEAF_PREFIX, MERKLE_NODE_PREFIX
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.core.base import SparseMerkleProof

_EMPTY_LEAF = bytes(32)


@cache
def _default(height: int) -> bytes:
    """Digest of an empty subtree of the given height."""
    if height == 0:
        return _EMPTY_LEAF
    below = _default(height - 1)
    return sha256(MERKLE_NODE_PREFIX + below + below)


def _path(key: bytes, depth: int) -> int:
    return int.from_bytes(sha256(key), "big") >> (256 - depth)


def _leaf(key: bytes, value: bytes) -> bytes:
    return sha256(MERKLE_LEAF_PREFIX + len(key).to_bytes(8, "big") + key + value)


class SparseMerkleTree:
    """An immutable map from byte keys to byte values with a Merkle root.

    Parameters
    ----------
    depth : int
        Number of key-hash bits used for the position, 1 to 256. A small
        depth makes collisions between keys possible; it exists only to make
        small experiments easy to draw.

    Examples
    --------
    >>> from blockchainkit.structures import SparseMerkleTree, verify_sparse_proof
    >>> tree = SparseMerkleTree().set(b"alice", b"100")
    >>> verify_sparse_proof(tree.prove(b"bob"), tree.root)  # Proof that bob is absent.
    True
    """

    def __init__(self, depth: int = 256, items: dict[bytes, bytes] | None = None) -> None:
        integer(depth, "depth", 1)
        if depth > 256:
            raise ValueError("depth cannot exceed 256")
        self._depth = depth
        self._items = dict(items or {})
        self._leaves = {_path(k, depth): _leaf(k, v) for k, v in self._items.items()}

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        root = self.root.hex()[:16]
        return f"SparseMerkleTree(depth={self._depth}, keys={len(self)}, root={root}...)"

    @staticmethod
    def _check(key: bytes, value: bytes = b"") -> None:
        if not isinstance(key, bytes) or not isinstance(value, bytes):
            raise TypeError("keys and values must be bytes")

    def get(self, key: bytes) -> bytes | None:
        """Return the value stored at a key, or None."""
        self._check(key)
        return self._items.get(key)

    def set(self, key: bytes, value: bytes) -> "SparseMerkleTree":
        """Return a new tree with ``key`` mapped to ``value``."""
        self._check(key, value)
        return SparseMerkleTree(self._depth, {**self._items, key: value})

    def delete(self, key: bytes) -> "SparseMerkleTree":
        """Return a new tree without ``key``."""
        self._check(key)
        return SparseMerkleTree(self._depth, {k: v for k, v in self._items.items() if k != key})

    def _digest(self, height: int, prefix: int, leaves: dict[int, bytes]) -> bytes:
        """Digest of the subtree of ``height`` whose positions start with ``prefix``."""
        if not leaves:
            return _default(height)
        if height == 0:
            return leaves[prefix]
        left_prefix, right_prefix = prefix << 1, (prefix << 1) | 1
        shift = height - 1
        left = {p: d for p, d in leaves.items() if p >> shift == left_prefix}
        right = {p: d for p, d in leaves.items() if p >> shift == right_prefix}
        return sha256(
            MERKLE_NODE_PREFIX
            + self._digest(shift, left_prefix, left)
            + self._digest(shift, right_prefix, right)
        )

    @cached_property
    def root(self) -> bytes:
        """Return the root digest; equal maps give equal roots, in any order."""
        return self._digest(self._depth, 0, self._leaves)

    def prove(self, key: bytes) -> SparseMerkleProof:
        """Return a proof of the key's value, or of its absence."""
        self._check(key)
        position = _path(key, self._depth)
        siblings = []
        for height in range(self._depth):
            sibling_prefix = (position >> height) ^ 1
            subtree = {p: d for p, d in self._leaves.items() if p >> height == sibling_prefix}
            siblings.append(self._digest(height, sibling_prefix, subtree))
        return SparseMerkleProof(key, self._items.get(key), tuple(siblings))


def verify_sparse_proof(proof: SparseMerkleProof, root: bytes) -> bool:
    """Recompute the root from a key, its claimed value (or absence), and siblings.

    The number of siblings is the tree depth. Leaf and node digests carry
    different prefixes, so a shorter proof cannot pass for a longer one.
    """
    depth = len(proof.siblings)
    if not 1 <= depth <= 256 or any(not isinstance(d, bytes) for d in proof.siblings):
        return False
    position = _path(proof.key, depth)
    current = _EMPTY_LEAF if proof.value is None else _leaf(proof.key, proof.value)
    for height, sibling in enumerate(proof.siblings):
        if (position >> height) & 1:
            current = sha256(MERKLE_NODE_PREFIX + sibling + current)
        else:
            current = sha256(MERKLE_NODE_PREFIX + current + sibling)
    return current == root
