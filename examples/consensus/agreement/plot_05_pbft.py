"""
Practical Byzantine Fault Tolerance (Castro and Liskov 1999)
============================================================

Castro and Liskov made Byzantine agreement fast enough for real services.
With n = 3f + 1 replicas, every quorum of 2f + 1 overlaps every other in at
least f + 1 replicas, so in at least one honest replica. A replica prepares
a value after 2f matching prepares and commits after 2f + 1 matching
commits; no two honest replicas can commit different values in one view.

What to look for
----------------

With one faulty replica among four, even an equivocating leader cannot make
honest replicas commit different values. With two faulty replicas the
quorums no longer intersect in an honest replica, and safety breaks.
Tendermint, HotStuff and many proof-of-stake chains descend from PBFT.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# An equivocating leader, one fault: still safe
# ---------------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

safe = bk.consensus.pbft_round(4, faulty={0}, value="A", equivocate=True)
print("one faulty leader:", safe.commits)
assert len({v for v in safe.commits.values() if v}) <= 1

# %%
# Two faults among four: safety breaks
# ------------------------------------
broken = bk.consensus.pbft_round(4, faulty={0, 1}, value="A", equivocate=True)
print("two faulty replicas:", broken.commits)
assert {v for v in broken.commits.values() if v} == {"A", "B"}

# %%
# Quorum intersection
# -------------------
sizes = range(4, 32, 3)
overlap = [2 * bk.consensus.quorum_size(n) - n for n in sizes]
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.plot(sizes, overlap, "o-", label="minimum quorum overlap 2(2f+1) - n")
ax.plot(sizes, [(n - 1) // 3 + 1 for n in sizes], "--", color="black", label="f + 1")
ax.set(
    xlabel="replicas n = 3f + 1",
    ylabel="replicas",
    title="Two quorums always share an honest replica",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Why does a replica wait for 2f + 1 commits and not 2f? Find the run where
# 2f would let two honest replicas commit different values.
