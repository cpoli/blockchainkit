"""
The CAP theorem: consistency or availability (Brewer 2000, Gilbert and Lynch 2002)
==================================================================================

Brewer conjectured, and Gilbert and Lynch proved, that a replicated service
cannot guarantee both *consistency* (every read returns the latest write)
and *availability* (every request to a live replica gets an answer) when
the network may *partition*. During a split, each side must either refuse
requests or answer without the other side.

What to look for
----------------

The same sequence of requests runs against two policies on five replicas
split 2 to 3. The consistent register refuses every request on the minority
side, and every read it does answer is up to date. The available register
answers everything, but returns stale values during the split and silently
discards one side's write when the partition heals. Bitcoin is on the
available side: both halves of a split keep extending their own chain, and
the shorter chain's blocks are discarded at reconnection.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# One workload, two policies
# --------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk


def workload(mode):
    register = bk.network.ReplicatedRegister(5, mode=mode, initial="v0")
    register.partition([0, 1], [2, 3, 4])
    register.write(0, "left")
    register.read(1)
    register.read(3)
    register.write(3, "right")
    register.read(0)
    register.read(4)
    register.heal()
    register.read(0)
    return register


latest = {}
for mode in ("consistent", "available"):
    register = workload(mode)
    print(mode)
    for op in register.history:
        print(f"  {op.kind:5s} at replica {op.replica}: {op.value!s:6s} ok={op.ok}")
    latest[mode] = register

consistent, available = (latest[m].history for m in ("consistent", "available"))
assert [op.ok for op in consistent] == [False, False, True, True, False, True, True]
assert all(op.ok for op in available)

# %%
# Count the anomalies
# -------------------
# A read is stale if some earlier successful write is not visible in it.


def anomalies(history):
    refused = sum(not op.ok for op in history)
    stale, last = 0, "v0"
    for op in history:
        if op.kind == "write" and op.ok:
            last = op.value
        elif op.kind == "read" and op.ok and op.value != last:
            stale += 1
    return refused, stale


counts = {mode: anomalies(latest[mode].history) for mode in latest}
print(counts)
assert counts["consistent"] == (3, 0)
assert counts["available"][1] >= 2
assert latest["available"].values() == ("right",) * 5  # "left" was lost at healing.

fig, ax = plt.subplots(figsize=(6, 3.5))
x = range(2)
ax.bar([i - 0.2 for i in x], [counts[m][0] for m in counts], 0.4, label="refused")
ax.bar([i + 0.2 for i in x], [counts[m][1] for m in counts], 0.4, label="stale reads")
ax.set_xticks(list(x), list(counts))
ax.set(ylabel="requests", title="Pick one during a partition")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Partition the five replicas into three groups of sizes 2, 2 and 1. What
# can the consistent register still do? Relate the answer to why PBFT and
# Bitcoin behave so differently during a network split.
