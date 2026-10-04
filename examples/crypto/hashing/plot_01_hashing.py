"""
Hashing: fingerprints, commitments, and the avalanche effect
============================================================

A cryptographic hash maps arbitrary bytes to a fixed-size digest. Changing
one input bit usually changes about half the output bits. This observation
is useful intuition, not a proof of collision or preimage resistance.

What to look for
----------------

Compare the fingerprints before and after changing input bits. Many output bits change.
Then compare a guessable unsalted message with a commitment that uses a secret salt.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

See :doc:`/tutorials/course` for prerequisites and :doc:`/tutorials/solutions` for worked answers.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

message = b"blockchainkit: a reproducible experiment"
digest = bk.crypto.sha256(message)
distances = []
for bit in range(len(message) * 8):
    modified = bytearray(message)
    modified[bit // 8] ^= 1 << (bit % 8)
    distances.append(bk.crypto.hamming_distance(digest, bk.crypto.sha256(bytes(modified))))
print("Mean changed digest bits:", sum(distances) / len(distances), "out of 256")

# %%
# Commit now, reveal later
# ------------------------
# A real salt should come from secrets.token_bytes(32). This fixed salt makes
# the lesson reproducible, but is public and does not hide the message.
salt = bytes(range(32))
commitment = bk.crypto.commit(b"bid=42", salt)
assert bk.crypto.verify_commitment(commitment, b"bid=42", salt)
assert not bk.crypto.verify_commitment(commitment, b"bid=43", salt)
print("Commitment:", commitment.hex())

# %%
fig, ax = plt.subplots(figsize=(7, 4))
ax.hist(distances, bins=18, color="#0d9488", edgecolor="white")
ax.axvline(128, color="#b45309", linestyle="--", label="Half of 256 bits")
ax.set(
    xlabel="Changed output bits after one input-bit flip",
    ylabel="Count",
    title="SHA-256 avalanche experiment",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Hash only the first byte of each digest and find collisions. Compare the
# number of trials to the birthday estimate. Why is this not an attack on
# the full SHA-256 output? Why does hashing a small unsalted bid fail to hide it?
