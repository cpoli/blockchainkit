"""
Batching timestamps with a Merkle tree (Bayer, Haber and Stornetta 1993)
========================================================================

Linking every document into a chain costs one record per document. Bayer,
Haber and Stornetta batched them: put a round's documents in a Merkle tree
and timestamp only the root. Each document keeps a short proof linking it
to that root. This is exactly how a block commits to its transactions.

What to look for
----------------

One 32-byte root timestamps a thousand documents, and each proof grows only
logarithmically. A block's header commits to its transactions the same way.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
See :doc:`/exercises/structures` for a worked solution to the exercise.
"""

# %%
# Timestamp a round of documents with one root
# --------------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

documents = [f"contract {i}".encode() for i in range(1000)]
tree = bk.structures.MerkleTree(documents)
stamp = bk.structures.BlockHeader(merkle_root=tree.root, height=0, timestamp=1993, difficulty=0)
proof = tree.proof(617)
assert bk.structures.verify_proof(documents[617], proof, stamp.merkle_root)
size = sum(32 for sibling in proof.siblings if sibling is not None)
print(f"1000 documents, one root; proof for contract 617: {size} bytes")

# %%
# A block does the same for its transactions
# ------------------------------------------
alice = bk.crypto.public_key(7)
bob = bk.structures.address(bk.crypto.public_key(11))
payments = tuple(
    bk.structures.Transaction(alice, bob, 1, n).signed(7, signing_nonce=100 + n) for n in range(5)
)
block = bk.structures.Block(transactions=payments, difficulty=0)
assert block.merkle_root == bk.structures.MerkleTree(tx.to_bytes() for tx in payments).root

# %%
# Records needed: one per document, or one per round
# --------------------------------------------------
counts = [2**k for k in range(1, 15)]
proof_bytes = [32 * (n - 1).bit_length() for n in counts]
fig, ax = plt.subplots(figsize=(7, 4))
ax.loglog(counts, counts, "--", label="linked records (one per document)")
ax.loglog(counts, [1] * len(counts), "-", label="batched records (one per round)")
ax.loglog(counts, proof_bytes, "o-", label="proof bytes per document")
ax.set(xlabel="documents per round", title="Batching: one timestamp, logarithmic proofs")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# OpenTimestamps batches documents worldwide into one Bitcoin transaction per
# round. Estimate the proof length for a round of a million documents.
