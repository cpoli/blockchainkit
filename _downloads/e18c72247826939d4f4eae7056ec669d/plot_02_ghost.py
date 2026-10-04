"""
GHOST: follow the heaviest subtree (Sompolinsky and Zohar 2013)
===============================================================

When blocks are fast relative to network delay, honest miners often extend
the same parent at once, and the longest chain discards their side blocks.
That wasted work no longer protects the chain. GHOST (Greedy Heaviest
Observed SubTree) counts it: at each fork, follow the child whose whole
subtree carries the most work.

What to look for
----------------

A single long branch wins the longest-chain rule, while a shorter but
bushier branch, with more honest work behind it, wins under GHOST.
Ethereum's proof-of-work chain used a GHOST variant, with uncle rewards.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Build a fork
# ------------

import blockchainkit as bk
from blockchainkit.structures.visualizers import plot_block_tree

genesis = bk.consensus.mine(bk.structures.Block(difficulty=3)).block
chain = bk.structures.Blockchain(genesis)


def extend(parent, timestamp):
    block = bk.structures.Block(
        parent.hash, height=parent.height + 1, timestamp=timestamp, difficulty=3
    )
    block = bk.consensus.mine(block).block
    chain.add(block)
    return block


a = extend(genesis, 1)
a = extend(a, 2)
a = extend(a, 3)  # Branch A: three blocks in a row.
b = extend(genesis, 4)
b_children = [extend(b, 10 + i) for i in range(3)]  # Branch B: one block, three children.

# %%
# Two fork-choice rules, two answers
# ----------------------------------
ghost = bk.consensus.ghost_tip(chain)
assert chain.tip == a and ghost in b_children
print("longest chain picks height", chain.tip.height, "; GHOST picks height", ghost.height)
work_a = bk.consensus.subtree_work(
    chain, chain.blocks[chain.blocks[a.previous_hash].previous_hash].hash
)
work_b = bk.consensus.subtree_work(chain, b.hash)
print(f"subtree work: branch A {work_a}, branch B {work_b}")

ax = plot_block_tree(chain)
ax.set_title("Longest chain (blue) versus GHOST's heaviest subtree (branch B)")
ax.figure.tight_layout()

# %%
# Exercise
# --------
# With a 12-second block time, a large share of Ethereum's blocks were
# uncles. Why would the longest-chain rule have let an attacker with less
# than half the hashrate win more often?
