"""
Bloom filters: membership with false positives (Bloom 1970)
===========================================================

Burton Bloom traded accuracy for space: set k bit positions per item in an
m-bit array, and report an item present if all its positions are set. Items
added are always found; others are occasionally found by mistake. Bitcoin
light wallets (BIP 37, 2012) sent full nodes a Bloom filter of their
addresses instead of the addresses themselves.

What to look for
----------------

No false negatives, and a false-positive rate that matches Bloom's formula
(1 - exp(-kn/m))**k. The false positives were meant to hide which
transactions a wallet cares about; analyses soon showed they leaked most of
that privacy, and BIP 37 was deprecated.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# A filter of one wallet's addresses
# ----------------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

wallet = [bk.crypto.sha256(f"my address {i}".encode()) for i in range(40)]
bloom = bk.structures.BloomFilter(512, bk.structures.BloomFilter.optimal_hash_count(512, 40))
for item in wallet:
    bloom.add(item)
assert all(item in bloom for item in wallet)  # Never a false negative.
others = [bk.crypto.sha256(f"someone else {i}".encode()) for i in range(10_000)]
rate = sum(item in bloom for item in others) / len(others)
print(f"k = {bk.structures.BloomFilter.optimal_hash_count(512, 40)}, false positives: {rate:.3%}")

# %%
# Measured rate against the formula
# ---------------------------------
sizes, measured, predicted = [], [], []
for n in range(10, 201, 10):
    filt = bk.structures.BloomFilter(1024, 4)
    for i in range(n):
        filt.add(f"in {i}".encode())
    sizes.append(n)
    measured.append(np.mean([f"out {i}".encode() in filt for i in range(3000)]))
    predicted.append(bk.structures.BloomFilter.false_positive_rate(1024, 4, n))
assert max(abs(a - b) for a, b in zip(measured, predicted, strict=True)) < 0.03
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(sizes, measured, "o", label="measured")
ax.plot(sizes, predicted, "-", color="black", label="(1 - exp(-kn/m))**k")
ax.set(
    xlabel="items added n (m = 1024 bits, k = 4)",
    ylabel="false-positive rate",
    title="Bloom's trade-off",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# A node sees a wallet's filter and every transaction it matches. If the
# filter matches 1% of unrelated transactions, and the wallet has 40
# addresses each used once a day among 300,000 daily transactions, what
# fraction of the matches really belong to the wallet?
