"""
Rumor spreading in log2 n + ln n rounds (Frieze and Grimmett 1985, Pittel 1987)
===============================================================================

How long does push gossip take to reach everyone? On the complete graph,
Frieze and Grimmett, and then Pittel more precisely, showed it takes
``log2 n + ln n + O(1)`` rounds. The first term is the doubling phase, while
almost every call reaches someone new; the second is a coupon-collector
phase, while the last few peers wait to be called.

What to look for
----------------

The measured rounds track ``log2 n + ln n`` with a gap that stays roughly
constant as n grows a thousandfold. A network of a million peers needs only
about 34 rounds: this is why gossip scales.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# Measure rounds for n from 16 to 16384
# -------------------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

sizes = [2**k for k in range(4, 15, 2)]
measured = [np.mean([bk.network.spread_rumor(n, seed=s).rounds for s in range(8)]) for n in sizes]
predicted = [bk.network.pittel_rounds(n) for n in sizes]
gaps = [m - p for m, p in zip(measured, predicted, strict=True)]
print([round(float(g), 2) for g in gaps])
assert max(gaps) - min(gaps) < 2.5  # The O(1) term does not grow with n.
print(round(bk.network.pittel_rounds(10**6), 1), "rounds for a million peers")

# %%
# The two phases
# --------------
run = bk.network.spread_rumor(16384, seed=1)
doubling = next(r for r, count in enumerate(run.informed) if count > 16384 / 2)
print(f"half informed after {doubling} rounds; done after {run.rounds}")
assert abs(doubling - np.log2(16384)) < 2

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 3.8))
left.semilogx(sizes, measured, "o", label="simulated push")
left.semilogx(sizes, predicted, "-", color="black", label="log2 n + ln n")
left.set(xlabel="peers n", ylabel="rounds", title="Rounds to inform everyone")
left.legend()
right.plot(run.informed, marker="o", markersize=3)
right.axvline(doubling, color="black", linestyle="--", label="half informed")
right.set(xlabel="round", ylabel="informed peers", title="Doubling, then the tail")
right.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Run push on a ring (``bk.network.ring_lattice(n, 2)``) instead of the
# complete graph. How do the rounds grow with n now, and why?
