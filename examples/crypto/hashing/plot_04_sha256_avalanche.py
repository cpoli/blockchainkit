"""
SHA-256 and the avalanche effect (FIPS 180-2, 2002)
===================================================

SHA-256 became the standardized hash behind Bitcoin's block hashes,
addresses, and Merkle trees. A good hash behaves like a random function:
flipping one input bit flips each output bit with probability one half.

What to look for
----------------

Flip every bit of a message in turn. The number of changed output bits
clusters around 128 of 256, following a Binomial(256, 1/2) distribution.
This is useful intuition, not a proof of collision or preimage resistance.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
See :doc:`/tutorials/solutions` for a worked answer to the exercise.
"""

# %%
import blockchainkit as bk
from blockchainkit.crypto.visualizers import plot_hamming_distances

message = b"blockchainkit: a reproducible experiment"
digest = bk.crypto.sha256(message)
assert digest.hex() == bk.crypto.merkle_damgard_sha256(message).hex()
distances = []
for bit in range(len(message) * 8):
    flipped = bytearray(message)
    flipped[bit // 8] ^= 1 << (bit % 8)
    distances.append(bk.crypto.hamming_distance(digest, bk.crypto.sha256(bytes(flipped))))
mean = sum(distances) / len(distances)
assert 120 < mean < 136
print("Mean changed digest bits:", mean, "out of 256")

# %%
ax = plot_hamming_distances(distances)
ax.figure.tight_layout()

# %%
# Exercise
# --------
# Hash only the first byte of each digest and find collisions. Compare the
# number of trials to the birthday estimate. Why is this not an attack on
# the full SHA-256 output?
