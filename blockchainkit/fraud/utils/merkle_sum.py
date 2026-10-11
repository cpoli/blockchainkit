"""Merkle sum trees: Merkle trees whose nodes also commit to the total below them.

Each leaf holds a customer's balance and each node the sum of its two
children, and every node's hash covers both children's sums as well as
their hashes. The root then commits to the exchange's total liabilities,
and a customer's inclusion proof shows that its balance is counted in that
total. A verifier rejects any sibling with a negative sum, which stops an
exchange from cancelling real balances with fake negative ones.

Odd nodes are promoted unchanged, as in
:class:`~blockchainkit.structures.systems.merkle.MerkleTree`.
"""

from collections.abc import Iterable

from blockchainkit._validation import integer
from blockchainkit.constants import SUM_LEAF_DOMAIN, SUM_NODE_DOMAIN, UINT64_LIMIT
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.fraud.core.base import SumProof, SumProofStep
from blockchainkit.structures.utils.encoding import canonical_json

Node = tuple[bytes, int]


def sum_leaf(label: str, balance: int, salt: bytes = b"") -> Node:
    """Hash a customer's ``label`` and ``balance`` into a leaf ``(digest, balance)``.

    The ``salt`` keeps a leaf from revealing which customer it belongs to.
    """
    if not isinstance(label, str):
        raise TypeError("label must be a string")
    integer(balance, "balance", -UINT64_LIMIT)
    if not isinstance(salt, bytes):
        raise TypeError("salt must be bytes")
    return sha256(SUM_LEAF_DOMAIN + canonical_json([salt.hex(), label, balance])), balance


def sum_node(left: Node, right: Node) -> Node:
    """Combine two children into ``(hash of both sums and both hashes, sum)``."""
    digest = sha256(SUM_NODE_DOMAIN + canonical_json([left[1], right[1]]) + left[0] + right[0])
    return digest, left[1] + right[1]


class MerkleSumTree:
    """A Merkle sum tree over customer balances (Maxwell, 2013).

    Parameters
    ----------
    balances : iterable of tuple
        ``(label, balance)`` pairs in leaf order. Negative balances are
        accepted so that the cheat they enable can be shown.
    salt : bytes
        Mixed into every leaf.

    Examples
    --------
    >>> from blockchainkit.fraud import MerkleSumTree, verify_sum_proof
    >>> tree = MerkleSumTree([("alice", 30), ("bob", 50), ("carol", 20)])
    >>> tree.total
    100
    >>> verify_sum_proof("bob", 50, tree.proof(1), tree.root, tree.total)
    True
    >>> verify_sum_proof("bob", 5, tree.proof(1), tree.root, tree.total)
    False
    """

    def __init__(self, balances: Iterable[tuple[str, int]], *, salt: bytes = b"") -> None:
        entries = tuple(balances)
        if not entries:
            raise ValueError("a sum tree needs at least one balance")
        self._labels = tuple(label for label, _ in entries)
        self._salt = salt
        level = tuple(sum_leaf(label, balance, salt) for label, balance in entries)
        levels = [level]
        while len(level) > 1:
            level = tuple(
                sum_node(level[i], level[i + 1]) if i + 1 < len(level) else level[i]
                for i in range(0, len(level), 2)
            )
            levels.append(level)
        self._levels = tuple(levels)

    def __repr__(self) -> str:
        return f"MerkleSumTree(leaves={len(self)}, total={self.total})"

    def __len__(self) -> int:
        return len(self._labels)

    @property
    def root(self) -> bytes:
        """The root hash, which commits to every balance and to the total."""
        return self._levels[-1][0][0]

    @property
    def total(self) -> int:
        """The sum of every balance, which is the liabilities the exchange declares."""
        return self._levels[-1][0][1]

    @property
    def salt(self) -> bytes:
        """The salt mixed into every leaf."""
        return self._salt

    @property
    def levels(self) -> tuple[tuple[Node, ...], ...]:
        """Every level from the leaves to the root, each node as ``(digest, sum)``."""
        return self._levels

    def index(self, label: str) -> int | None:
        """Position of ``label``'s leaf, or None if the tree leaves it out."""
        return self._labels.index(label) if label in self._labels else None

    def proof(self, index: int) -> SumProof:
        """The siblings on the path from leaf ``index`` to the root."""
        integer(index, "index")
        if index >= len(self):
            raise IndexError("leaf index out of range")
        steps = []
        position = index
        for level in self._levels[:-1]:
            sibling = position ^ 1
            if sibling < len(level):
                side = "left" if sibling < position else "right"
                steps.append(SumProofStep(side, *level[sibling]))
            position //= 2
        return SumProof(index, tuple(steps))


def verify_sum_proof(
    label: str, balance: int, proof: SumProof, root: bytes, total: int, *, salt: bytes = b""
) -> bool:
    """Check that ``label``'s ``balance`` is counted in a tree with ``root`` and ``total``.

    Rejects a negative balance and any sibling whose sum is negative.
    """
    node = sum_leaf(label, balance, salt)
    if balance < 0:
        return False
    for step in proof.steps:
        if step.amount < 0:
            return False
        sibling = (step.digest, step.amount)
        node = sum_node(sibling, node) if step.side == "left" else sum_node(node, sibling)
    return node == (root, total)
