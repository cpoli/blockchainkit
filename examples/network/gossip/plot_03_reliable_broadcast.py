"""
Byzantine reliable broadcast: echo, then ready (Bracha 1987)
============================================================

A sender broadcasts a value, but it may be Byzantine and tell different
peers different things. Bracha's protocol makes delivery consistent anyway:
peers *echo* what they received, become *ready* for a value once a large
quorum echoed it (or once ``t + 1`` peers are ready for it), and *deliver*
once ``2t + 1`` peers are ready. With ``n > 3t``, all correct peers deliver
the same value, or none delivers at all.

What to look for
----------------

Naively trusting the sender splits the correct peers. Bracha's quorums never
do, for any split the faulty sender and its accomplices try, as long as at
most a third are faulty. One faulty peer too many breaks agreement. Block
gossip uses the same idea: a peer forwards what enough others vouch for.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# An equivocating sender
# ----------------------
# Sender 0 is faulty and tells peers 1-3 "a" and peers 4-6 "b".
import itertools

import matplotlib.pyplot as plt

import blockchainkit as bk

proposals = ["a", "a", "a", "a", "b", "b", "b"]
naive = {p: proposals[p] for p in range(1, 7)}
print("trust the sender:", naive)
assert len(set(naive.values())) == 2

result = bk.network.reliable_broadcast(7, {0}, proposals)
print("Bracha:", result.delivered)
assert result.agreement and result.totality

# %%
# Every split, every set of faulty peers
# --------------------------------------
# Check all faulty sets of size up to t and all ways to split the peers.
outcomes = {"all deliver": 0, "none deliver": 0, "disagree": 0}
for faulty in itertools.chain.from_iterable(itertools.combinations(range(7), f) for f in (1, 2)):
    if 0 not in faulty:
        continue
    for split in itertools.product("ab", repeat=7):
        r = bk.network.reliable_broadcast(7, faulty, list(split))
        delivered = set(r.delivered.values())
        if not r.agreement:
            outcomes["disagree"] += 1
        elif delivered == {None}:
            outcomes["none deliver"] += 1
        else:
            outcomes["all deliver"] += 1
print(outcomes)
assert outcomes["disagree"] == 0

# %%
# One faulty peer too many
# ------------------------
# With n = 4 the protocol tolerates t = 1. Two colluding faulty peers can
# make each correct peer see a different echo quorum.
broken = bk.network.reliable_broadcast(4, {0, 3}, ["a", "a", "b", "b"])
print(broken.delivered)
assert not broken.agreement

fig, ax = plt.subplots(figsize=(6, 3.5))
ax.bar(outcomes.keys(), outcomes.values(), color=["#16a34a", "#94a3b8", "#dc2626"])
ax.set(ylabel="runs", title="n = 7, faulty sender plus up to one accomplice")
fig.tight_layout()

# %%
# Exercise
# --------
# The echo threshold is ``ceil((n + t + 1) / 2)``. Show that two sets of
# that size among n peers share at least ``t + 1`` peers, so at least one
# correct peer, which echoes only one value. What goes wrong with a simple
# majority threshold?
