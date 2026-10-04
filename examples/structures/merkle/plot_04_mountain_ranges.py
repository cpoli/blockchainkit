"""
Merkle mountain ranges: an append-only accumulator (Todd 2016)
==============================================================

Peter Todd described a structure for logs that only grow, designed for
OpenTimestamps: a list of perfect Merkle trees ("peaks") of decreasing
size. Appending adds a one-leaf peak and merges equal-sized neighbours,
like carrying in binary addition. Old peaks are never rewritten, so an
append costs about two hashes, however long the range is.

What to look for
----------------

The number of peaks equals the number of 1-bits in the size. Every leaf
has a short proof to its peak. Grin and other chains use mountain ranges to
commit to their entire history of outputs or headers.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Grow a range and watch the peaks
# --------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

mmr = bk.structures.MerkleMountainRange()
peak_counts, merges = [], []
for i in range(64):
    before = len(mmr.peaks)
    mmr = mmr.append(f"header {i}".encode())
    peak_counts.append(len(mmr.peaks))
    merges.append(before + 1 - len(mmr.peaks))
assert all(count == bin(n + 1).count("1") for n, count in enumerate(peak_counts))
print(f"64 appends needed {sum(merges)} merges in total ({sum(merges) / 64:.2f} per append)")

# %%
# Prove one old leaf
# ------------------
proof = mmr.proof(37)
assert bk.structures.verify_mmr_proof(b"header 37", proof, mmr.root)
assert not bk.structures.verify_mmr_proof(b"header 99", proof, mmr.root)

# %%
fig, (top, bottom) = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
top.step(range(1, 65), peak_counts, where="post")
top.set(ylabel="peaks", title="Peaks = 1-bits of the size; merges = carries")
bottom.bar(range(1, 65), merges, color="#2563eb")
bottom.set(xlabel="leaves", ylabel="merges at this append")
fig.tight_layout()

# %%
# Exercise
# --------
# When does a single append cause the most merges? Relate the answer to
# carries when adding 1 in binary, and compute the average over 2**k appends.
