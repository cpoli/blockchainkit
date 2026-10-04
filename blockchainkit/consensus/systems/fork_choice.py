"""GHOST fork choice (Sompolinsky and Zohar 2013): follow the heaviest subtree.

When blocks are frequent, many honest blocks end up off the longest chain,
and that wasted work no longer protects it. GHOST (Greedy Heaviest Observed
SubTree) walks from genesis and at each fork picks the child whose whole
subtree carries the most work, counting the honest side branches too.
Ethereum's proof-of-work chain used a variant through uncle rewards.
"""

from blockchainkit.consensus.systems.pow import expected_trials
from blockchainkit.structures.systems.block import Block
from blockchainkit.structures.systems.chain import Blockchain


def _children(chain: Blockchain) -> dict[bytes, list[Block]]:
    children: dict[bytes, list[Block]] = {}
    for block in chain.blocks.values():
        if block.height:
            children.setdefault(block.previous_hash, []).append(block)
    return children


def subtree_work(chain: Blockchain, block_hash: bytes) -> int:
    """Return the expected work of a block and all its descendants."""
    children = _children(chain)
    stack, total = [chain.blocks[block_hash]], 0
    while stack:
        block = stack.pop()
        total += expected_trials(block.difficulty)
        stack.extend(children.get(block.hash, []))
    return total


def ghost_tip(chain: Blockchain) -> Block:
    """Return the tip chosen by GHOST: descend into the heaviest subtree at every fork.

    Ties go to the smaller hash, matching
    :class:`~blockchainkit.structures.systems.chain.Blockchain`.
    """
    children = _children(chain)
    block = chain.canonical_blocks()[0]
    while children.get(block.hash):
        block = min(children[block.hash], key=lambda c: (-subtree_work(chain, c.hash), c.hash))
    return block
