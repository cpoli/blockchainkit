"""Domain-separated Merkle trees with explicit leaf-count commitments.

Odd nodes are promoted unchanged. Roots bind the leaf count to avoid
ambiguity between differently shaped trees. This is not Bitcoin's format.
"""

from collections.abc import Iterable

from blockchainkit._validation import integer
from blockchainkit.constants import (
    MERKLE_LEAF_PREFIX,
    MERKLE_NODE_PREFIX,
    MERKLE_ROOT_PREFIX,
    UINT64_LIMIT,
)
from blockchainkit.crypto.systems.hashing import hash256, sha256
from blockchainkit.structures.core.base import MerkleProof, MerkleTrace, ProofStep


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

    @property
    def leaf_count(self) -> int:
        """Return the number of leaves the root commits to."""
        return self._count

    def consistency_proof(self, old_size: int) -> tuple[bytes, ...]:
        """Prove that this tree extends its first ``old_size`` leaves (RFC 6962)."""
        return consistency_proof(self, old_size)

    @property
    def levels(self) -> tuple[tuple[bytes, ...], ...]:
        """Return every level's digests, from leaf hashes up to the top digest.

        The top digest is not yet the root: the root also binds the leaf count.
        An empty tree has a single empty level.
        """
        return self._levels

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


def _walk(leaf: bytes, proof: MerkleProof) -> tuple[bytes, list[ProofStep]] | None:
    """Recompute the top digest bottom-up; return None for a malformed proof."""
    if not isinstance(leaf, bytes) or not isinstance(proof, MerkleProof):
        return None
    if type(proof.leaf_count) is not int or not 0 < proof.leaf_count < UINT64_LIMIT:
        return None
    if type(proof.index) is not int or not 0 <= proof.index < proof.leaf_count:
        return None
    if not isinstance(proof.siblings, tuple):
        return None
    if len(proof.siblings) != (proof.leaf_count - 1).bit_length():
        return None
    leaf_digest = sha256(MERKLE_LEAF_PREFIX + leaf)
    current, index, count = leaf_digest, proof.index, proof.leaf_count
    steps = []
    # The checked path length ensures count > 1 at every iteration, and
    # repeated ceiling-halving reaches exactly 1 after the final sibling.
    for sibling in proof.siblings:
        if (index ^ 1) >= count:
            if sibling is not None:
                return None
            side = "promoted"
        else:
            if not isinstance(sibling, bytes) or len(sibling) != 32:
                return None
            side = "left" if index % 2 else "right"
            left, right = (sibling, current) if side == "left" else (current, sibling)
            current = sha256(MERKLE_NODE_PREFIX + left + right)
        steps.append(ProofStep(side, sibling, current))
        index //= 2
        count = (count + 1) // 2
    return leaf_digest, steps


def verify_proof(leaf: bytes, proof: MerkleProof, root: bytes) -> bool:
    """Verify payload, position, shape, count, and root; reject malformed proofs."""
    if not isinstance(root, bytes) or len(root) != 32:
        return False
    walked = _walk(leaf, proof)
    if walked is None:
        return False
    leaf_digest, steps = walked
    top = steps[-1].digest if steps else leaf_digest
    return _root(proof.leaf_count, top) == root


def trace_proof(leaf: bytes, proof: MerkleProof, root: bytes) -> MerkleTrace:
    """Reconstruct the root step by step, recording each level.

    Unlike :func:`verify_proof`, a well-formed proof that reconstructs the
    wrong root still returns its full trace (with ``valid=False``), so an
    experiment can show where a tampered leaf diverges.

    Raises
    ------
    ValueError
        The proof is malformed: wrong shape, count, index, or sibling type.

    Examples
    --------
    >>> from blockchainkit.structures import MerkleTree, trace_proof
    >>> tree = MerkleTree([b"a", b"b", b"c"])
    >>> [step.side for step in trace_proof(b"c", tree.proof(2), tree.root).steps]
    ['promoted', 'left']
    """
    walked = _walk(leaf, proof)
    if walked is None:
        raise ValueError("malformed Merkle proof")
    leaf_digest, steps = walked
    top = steps[-1].digest if steps else leaf_digest
    computed = _root(proof.leaf_count, top)
    return MerkleTrace(leaf_digest, tuple(steps), computed, computed == root)


def _subtree(digests: list[bytes]) -> bytes:
    """Top digest of consecutive leaf digests (the RFC 6962 tree shape)."""
    if len(digests) == 1:
        return digests[0]
    split = 1 << ((len(digests) - 1).bit_length() - 1)  # Largest power of two below n.
    return sha256(MERKLE_NODE_PREFIX + _subtree(digests[:split]) + _subtree(digests[split:]))


def _subproof(m: int, digests: list[bytes], complete: bool) -> list[bytes]:
    n = len(digests)
    if m == n:
        return [] if complete else [_subtree(digests)]
    split = 1 << ((n - 1).bit_length() - 1)
    if m <= split:
        return _subproof(m, digests[:split], complete) + [_subtree(digests[split:])]
    return _subproof(m - split, digests[split:], False) + [_subtree(digests[:split])]


def consistency_proof(tree: MerkleTree, old_size: int) -> tuple[bytes, ...]:
    """Prove that the first ``old_size`` leaves of ``tree`` form an earlier tree.

    The proof (RFC 6962, section 2.1.2) lists the subtree digests needed to
    rebuild both the old and the new top digest from shared parts, so a
    verifier can check that the log only appended. Because blockchainkit's
    roots also bind the leaf count, the verifier cannot read the old top
    digest off the old root; when ``old_size`` is a power of two (the case
    where RFC 6962 omits it) the proof starts with it. Also available as
    :meth:`MerkleTree.consistency_proof`.
    """
    integer(old_size, "old_size", 1)
    if old_size > tree.leaf_count:
        raise ValueError("old_size cannot exceed the tree's leaf count")
    digests = list(tree.levels[0])
    if old_size == tree.leaf_count:
        return ()
    proof = _subproof(old_size, digests, True)
    if old_size & (old_size - 1) == 0:
        proof.insert(0, _subtree(digests[:old_size]))
    return tuple(proof)


def verify_consistency(
    old_size: int, old_root: bytes, new_size: int, new_root: bytes, proof: tuple[bytes, ...]
) -> bool:
    """Check that the tree with ``old_root`` is a prefix of the tree with ``new_root``.

    Follows RFC 9162, section 2.1.4.2, on top digests, then checks both
    count-bound roots. Malformed or mismatched proofs return False.

    Examples
    --------
    >>> from blockchainkit.structures import MerkleTree, verify_consistency
    >>> leaves = [bytes([i]) for i in range(7)]
    >>> old, new = MerkleTree(leaves[:3]), MerkleTree(leaves)
    >>> verify_consistency(3, old.root, 7, new.root, new.consistency_proof(3))
    True
    """
    if type(old_size) is not int or type(new_size) is not int or not 0 < old_size <= new_size:
        return False
    if any(not isinstance(digest, bytes) or len(digest) != 32 for digest in proof):
        return False
    if old_size == new_size:
        return not proof and old_root == new_root
    if not proof:
        return False
    fn, sn = old_size - 1, new_size - 1
    while fn & 1:
        fn, sn = fn >> 1, sn >> 1
    old_top = new_top = proof[0]
    for digest in proof[1:]:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            old_top = sha256(MERKLE_NODE_PREFIX + digest + old_top)
            new_top = sha256(MERKLE_NODE_PREFIX + digest + new_top)
            while not fn & 1 and fn:
                fn, sn = fn >> 1, sn >> 1
        else:
            new_top = sha256(MERKLE_NODE_PREFIX + new_top + digest)
        fn, sn = fn >> 1, sn >> 1
    return sn == 0 and _root(old_size, old_top) == old_root and _root(new_size, new_top) == new_root


def bitcoin_merkle_root(leaves: Iterable[bytes]) -> bytes:
    """Return a root in Bitcoin's convention: double SHA-256, odd nodes duplicated.

    Shown for contrast with :class:`MerkleTree`. With no domain separation
    and no leaf count, the lists ``[a, b, c]`` and ``[a, b, c, c]`` share a
    root (CVE-2012-2459), which let an attacker make nodes reject a valid
    block. :class:`MerkleTree` promotes odd nodes and binds the count instead.

    >>> from blockchainkit.structures import bitcoin_merkle_root
    >>> bitcoin_merkle_root([b"a", b"b", b"c"]) == bitcoin_merkle_root([b"a", b"b", b"c", b"c"])
    True
    """
    level = [hash256(leaf) for leaf in leaves]
    if not level:
        raise ValueError("Bitcoin's convention has no root for an empty list")
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hash256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]
