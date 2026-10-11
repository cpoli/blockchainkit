"""GHOST fork choice (Sompolinsky and Zohar 2013): follow the heaviest subtree.

When blocks are frequent, many honest blocks end up off the longest chain,
and that wasted work no longer protects it. GHOST (Greedy Heaviest Observed
SubTree) walks from genesis and at each fork picks the child whose whole
subtree carries the most work, counting the honest side branches too.
Ethereum's proof-of-work chain adopted its uncle rewards but kept heaviest-chain
selection; LMD-GHOST became Ethereum's fork choice with proof of stake.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from blockchainkit.consensus.systems.pow import expected_trials

if TYPE_CHECKING:  # structures.systems.chain imports consensus: avoid the cycle.
    from blockchainkit.structures.systems.block import Block
    from blockchainkit.structures.systems.chain import Blockchain


def _children(chain: Blockchain) -> dict[bytes, list[Block]]:
    children: dict[bytes, list[Block]] = {}
    for block in chain.blocks.values():
        if block.height:
            children.setdefault(block.previous_hash, []).append(block)
    return children


def _subtree_weights(chain: Blockchain) -> dict[bytes, int]:
    """Expected work of every stored block's subtree, children before parents."""
    weights: dict[bytes, int] = {}
    for block in sorted(chain.blocks.values(), key=lambda b: -b.height):
        weights[block.hash] = weights.get(block.hash, 0) + expected_trials(block.difficulty)
        if block.height:
            weights[block.previous_hash] = weights.get(block.previous_hash, 0) + weights[block.hash]
    return weights


def subtree_work(chain: Blockchain, block_hash: bytes) -> int:
    """Return the expected work of a block and all its descendants.

    Raises KeyError for an unknown hash.
    """
    return _subtree_weights(chain)[block_hash]


def ghost_tip(chain: Blockchain) -> Block:
    """Return the tip chosen by GHOST: descend into the heaviest subtree at every fork.

    Ties go to the smaller hash, matching
    :class:`~blockchainkit.structures.systems.chain.Blockchain`.
    """
    children = _children(chain)
    weights = _subtree_weights(chain)
    block = chain.canonical_blocks()[0]
    while children.get(block.hash):
        block = min(children[block.hash], key=lambda c: (-weights[c.hash], c.hash))
    return block
