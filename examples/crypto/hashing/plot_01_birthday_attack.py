"""
The birthday attack on hash functions (Yuval 1979)
==================================================

In a room of 23 people, two probably share a birthday. Yuval turned this
into an attack: to find *any* two messages with the same n-bit hash takes
about 2**(n/2) trials, not the 2**n needed to match one given hash. A
signer tricked into signing one of a colliding pair has signed both.

What to look for
----------------

Collision searches on truncated SHA-256 succeed after about sqrt(2**n)
trials. This square root is why hashes have 256-bit outputs: to give
128-bit collision resistance.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Find a collision on 24 bits
# ---------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

result = bk.crypto.find_collision(24, prefix=b"contract v")
assert bk.crypto.truncated_hash(result.first, 24) == bk.crypto.truncated_hash(result.second, 24)
print(result.first, result.second, "collide after", result.trials, "trials")
print("Matching one given 24-bit hash would take about", 2**24, "trials")

# %%
# Collision cost follows the square root
# --------------------------------------
sizes = list(range(8, 33, 2))
mean_trials = []
for bits in sizes:
    trials = [bk.crypto.find_collision(bits, prefix=bytes([seed])).trials for seed in range(12)]
    mean_trials.append(np.mean(trials))
sizes_arr = np.array(sizes)
fig, ax = plt.subplots(figsize=(7, 4))
ax.semilogy(sizes, mean_trials, "o", label="measured (mean of 12)")
ax.semilogy(
    sizes_arr, np.sqrt(np.pi / 2 * 2.0**sizes_arr), "-", color="black", label="sqrt(pi/2 * 2**n)"
)
ax.semilogy(sizes_arr, 2.0**sizes_arr, ":", color="#b45309", label="second preimage: 2**n")
ax.set(xlabel="hash bits n", ylabel="trials", title="Collisions cost the square root")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# The expected number of trials is about sqrt(pi/2 * 2**n). At a billion
# hashes per second, how long does a collision on a 64-bit hash take? On a
# 128-bit hash? Why did MD5 (128 bits) fall, but not only because of this?
