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
# Index 1 is a right child: put its sibling on the left before hashing.
# The next level has our node on the left, so the ordering reverses.
current = bk.crypto.sha256(b"\x00" + leaves[1])
trace = [("Hash leaf with prefix 0", current.hex()[:16])]
position = proof.index
for sibling in proof.siblings:
    assert sibling is not None  # This chosen path has no promoted nodes.
    left, right = (sibling, current) if position % 2 else (current, sibling)
    current = bk.crypto.sha256(b"\x01" + left + right)
    trace.append(
        ("Combine sibling on " + ("left" if position % 2 else "right"), current.hex()[:16])
    )
    position //= 2
current = bk.crypto.sha256(b"\x02" + proof.leaf_count.to_bytes(8, "big") + current)
assert current == tree.root
trace.append(("Bind leaf count = 3; compare root", current.hex()[:16]))
fig, ax = plt.subplots(figsize=(9, 3))
ax.axis("off")
table = ax.table(
    cellText=trace, colLabels=["Verification step", "Digest prefix (display only)"], loc="center"
)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2)
ax.set_title("A Merkle proof is a recipe for reconstructing a root")
fig.tight_layout()
