"""
Two lists, one root: the duplicated-leaf ambiguity (CVE-2012-2459)
==================================================================

Bitcoin's Merkle tree pairs an odd node with a copy of itself. So the lists
[a, b, c] and [a, b, c, c] have the same root. In 2012 this let an attacker
send a block with a duplicated transaction: nodes rejected it as invalid and
remembered its hash as bad, so they later refused the valid block with the
same hash. The bug was fixed by checking for the duplication.

What to look for
----------------

Bitcoin's convention gives one root to two different lists. blockchainkit's
tree promotes odd nodes instead and binds the leaf count into the root, so
every list has its own root.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
See :doc:`/exercises/structures` for a worked solution to the exercise.
"""

# %%
# One root, two lists
# -------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

honest = [b"coinbase", b"pay Bob", b"pay Carol"]
mutated = honest + [b"pay Carol"]
assert bk.structures.bitcoin_merkle_root(honest) == bk.structures.bitcoin_merkle_root(mutated)
assert bk.structures.MerkleTree(honest).root != bk.structures.MerkleTree(mutated).root
print("Bitcoin convention:", bk.structures.bitcoin_merkle_root(honest).hex()[:16], "for both lists")

# %%
# How many sizes are affected?
# ----------------------------
ambiguous = []
for n in range(1, 40):
    leaves = [bytes([i]) for i in range(n)]
    ambiguous.append(
        bk.structures.bitcoin_merkle_root(leaves)
        == bk.structures.bitcoin_merkle_root(leaves + leaves[-1:])
    )
assert ambiguous == [n % 2 == 1 and n > 1 for n in range(1, 40)]
fig, ax = plt.subplots(figsize=(8, 2.8))
ax.bar(range(1, 40), ambiguous, color="#dc2626")
ax.set(
    xlabel="number of leaves n",
    yticks=[0, 1],
    yticklabels=["distinct", "same root"],
    title="Is [..., x] confusable with [..., x, x]?",
)
fig.tight_layout()

# %%
# Exercise
# --------
# The plot shows the ambiguity for every odd n above 1 (a single leaf is
# never paired). Find a length-6 list whose
# Bitcoin-style root equals that of a length-8 list. (Hint: duplicate a
# whole pair.) Why does binding the count rule out all such cases?
