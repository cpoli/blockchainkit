"""
Merkle trees: authenticate one item with a short proof
======================================================

A root commits to an ordered collection. An inclusion proof reveals the
sibling digests needed to recompute that root, rather than the full dataset.
The verifier must already trust the root by some independent mechanism.

What to look for
----------------

Watch a genuine membership proof pass and an altered payment fail. In the size plot,
proof length grows much more slowly than the number of records.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

See :doc:`/course` for prerequisites and :doc:`/solutions` for worked answers.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.structures.visualizers import plot_merkle_tree, plot_proof_trace

leaves = [b"Alice pays Bob", b"Bob pays Carol", b"Carol pays Dave"]
tree = bk.structures.MerkleTree(leaves)
proof = tree.proof(1)
assert bk.structures.verify_proof(leaves[1], proof, tree.root)
assert not bk.structures.verify_proof(b"Bob pays Mallory", proof, tree.root)
print("Root:", tree.root.hex())
print("Proof:", proof)

# %%
# Shape is part of the commitment
# -------------------------------
# Our convention promotes odd nodes and commits the count into the root.
# It does not duplicate odd leaves, and is intentionally not Bitcoin's format.
assert tree.root != bk.structures.MerkleTree(leaves + [leaves[-1]]).root
print("Last leaf's missing sibling is represented explicitly:", tree.proof(2).siblings[0])

# %%
sizes = [2**power for power in range(1, 11)]
proof_bytes = []
for size in sizes:
    sample = bk.structures.MerkleTree(str(i).encode() for i in range(size))
    proof_bytes.append(sum(32 for sibling in sample.proof(0).siblings if sibling is not None))
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(sizes, proof_bytes, "o-", label="Sibling hashes only")
ax.set(
    xscale="log",
    xlabel="Number of leaves",
    ylabel="Proof digest bytes",
    title="Logarithmic inclusion proofs",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Change the leaf index or leaf count in the proof and check verification.
# Explain why inclusion in a committed list does not establish that a payment
# was authorized, funded, or finalized by a consensus protocol.

# %%
# Trace one proof from its leaf to the trusted root
# -------------------------------------------------
# Index 1 is a right child: its sibling goes on the left before hashing.
# At the next level our node is on the left, so the order reverses. The final
# step binds the leaf count before comparing with the trusted root.
trace = bk.structures.trace_proof(leaves[1], proof, tree.root)
assert trace.valid and [step.side for step in trace.steps] == ["left", "right"]
fig, (tree_ax, table_ax) = plt.subplots(2, 1, figsize=(9, 6), height_ratios=[1.2, 1])
plot_merkle_tree(tree, highlight=1, ax=tree_ax)
plot_proof_trace(trace, ax=table_ax)
fig.tight_layout()
