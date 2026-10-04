"""
Sparse Merkle trees: proofs of absence (Dahlberg, Pulls and Peeters 2016)
=========================================================================

A blockchain's state is a map from accounts to balances. A sparse Merkle
tree commits to such a map: it is a tree with a leaf for every possible
key, almost all empty, so each key has a fixed position. Empty subtrees
have precomputed digests, so only paths to stored keys cost anything.
Dahlberg, Pulls and Peeters made them efficient and gave non-membership
proofs.

What to look for
----------------

The root does not depend on insertion order. A key that is absent has a
proof too: the leaf at its position is empty. Ethereum's state root plays
this role with a related structure, the Merkle Patricia trie.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Commit to balances
# ------------------
from dataclasses import replace

import matplotlib.pyplot as plt

import blockchainkit as bk

balances = {b"alice": b"100", b"bob": b"5", b"carol": b"42"}
tree = bk.structures.SparseMerkleTree()
for key, value in balances.items():
    tree = tree.set(key, value)
reordered = bk.structures.SparseMerkleTree()
for key in reversed(list(balances)):
    reordered = reordered.set(key, balances[key])
assert tree.root == reordered.root
print(tree)

# %%
# Prove a balance, and prove an absence
# -------------------------------------
member = tree.prove(b"bob")
absent = tree.prove(b"mallory")
assert bk.structures.verify_sparse_proof(member, tree.root) and member.value == b"5"
assert bk.structures.verify_sparse_proof(absent, tree.root) and absent.value is None
assert not bk.structures.verify_sparse_proof(replace(member, value=b"5000"), tree.root)

# %%
# Most siblings are default digests of empty subtrees
# ---------------------------------------------------
counts = []
for size in (1, 4, 16, 64, 256):
    grown = bk.structures.SparseMerkleTree()
    for i in range(size):
        grown = grown.set(f"account {i}".encode(), b"1")
    empty = bk.structures.SparseMerkleTree()
    defaults = set(empty.prove(b"x").siblings)
    proof = grown.prove(b"account 0")
    counts.append(sum(s not in defaults for s in proof.siblings))
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.semilogx([1, 4, 16, 64, 256], counts, "o-", base=2)
ax.set(
    xlabel="keys stored",
    ylabel="non-default siblings (of 256)",
    title="Proofs compress to about log2(keys) hashes",
)
fig.tight_layout()

# %%
# Exercise
# --------
# Why does a fixed position per key make proofs of absence possible, while
# an ordinary Merkle tree over a sorted list needs two neighbouring leaves?
