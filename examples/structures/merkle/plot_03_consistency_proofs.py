"""
Append-only logs: consistency proofs (Certificate Transparency 2013)
====================================================================

After certificate authorities were compromised in 2011, Google proposed
Certificate Transparency: every certificate goes into a public Merkle-tree
log. Auditors need to know the log only ever *appends*: that today's tree
contains yesterday's as a prefix. A consistency proof shows it with a
logarithmic number of hashes.

What to look for
----------------

Every older version of the log is proven to be a prefix of the newer one.
A log that rewrote an old entry cannot produce a passing proof. Proof size
grows with log2 of the log, not with its length.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Prove that the log only appended
# --------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

certificates = [f"certificate for site-{i}.example".encode() for i in range(1000)]
yesterday = bk.structures.MerkleTree(certificates[:600])
today = bk.structures.MerkleTree(certificates)
proof = today.consistency_proof(600)
assert bk.structures.verify_consistency(600, yesterday.root, 1000, today.root, proof)
print(f"consistency proof from 600 to 1000 entries: {len(proof)} hashes")

# %%
# A rewritten history fails
# -------------------------
forged = list(certificates)
forged[42] = b"certificate for bank.example, issued to an attacker"
forged_today = bk.structures.MerkleTree(forged)
forged_proof = forged_today.consistency_proof(600)
assert not bk.structures.verify_consistency(
    600, yesterday.root, 1000, forged_today.root, forged_proof
)

# %%
# Proof size against log size
# ---------------------------
sizes = [2**k for k in range(2, 12)]
lengths = []
for n in sizes:
    log = bk.structures.MerkleTree(f"entry {i}".encode() for i in range(n))
    lengths.append(len(log.consistency_proof(n // 2 + 1)))
fig, ax = plt.subplots(figsize=(7, 4))
ax.semilogx(sizes, lengths, "o-", base=2)
ax.set(xlabel="log size", ylabel="hashes in proof", title="Consistency proofs are logarithmic")
fig.tight_layout()

# %%
# Exercise
# --------
# A log could show one tree to you and another to everyone else ("split
# view"). Why do consistency proofs alone not prevent that, and how do
# gossiped signed tree heads help?
