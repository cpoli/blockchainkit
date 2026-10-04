"""
Lamport clocks: ordering events without a shared clock (Lamport 1978)
=====================================================================

Peers' clocks drift, so wall-clock timestamps cannot say which of two events
came first. Lamport replaced physical time with *happened before*: an event
precedes the later events at its own process, a message's send precedes its
receive, and the relation is transitive. A counter that ticks at every event
and jumps past every timestamp it receives respects that order.

What to look for
----------------

Every arrow in the space-time diagram points forward in Lamport time: that
is the clock condition. Ordering events by ``(timestamp, process)`` gives one
total order that all processes can compute alike, which Lamport used for
mutual exclusion and which underlies state-machine replication. But a
smaller timestamp does not prove an event came first: events that are
concurrent still receive ordered numbers.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# Three processes exchange three messages
# ---------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.network.visualizers import plot_space_time

history = [
    [("send", "m1"), ("local", "a"), ("receive", "m3")],
    [("receive", "m1"), ("send", "m2")],
    [("local", "b"), ("receive", "m2"), ("send", "m3")],
]
stamps = bk.network.lamport_timestamps(history)
print(stamps)
assert stamps == ((1, 2, 6), (2, 3), (1, 4, 5))

# %%
# The clock condition
# -------------------
# Each receive is stamped later than its send, and each process's stamps
# increase, so every chain of causes has increasing timestamps.
sends = {
    label: stamps[p][i]
    for p, events in enumerate(history)
    for i, (kind, label) in enumerate(events)
    if kind == "send"
}
for p, events in enumerate(history):
    assert list(stamps[p]) == sorted(set(stamps[p]))
    for i, (kind, label) in enumerate(events):
        if kind == "receive":
            assert stamps[p][i] > sends[label]

# %%
# One total order everyone agrees on
# ----------------------------------
# Break timestamp ties by process number.
order = sorted(
    (stamps[p][i], p, label)
    for p, events in enumerate(history)
    for i, (_, label) in enumerate(events)
)
print([f"P{p}:{label}" for _, p, label in order])

# %%
# The converse fails
# ------------------
# Local event ``b`` (time 1) and local event ``a`` (time 2) are not causally
# related: no chain of messages links them. Their timestamps are ordered
# anyway, so a Lamport timestamp cannot detect concurrency.
assert stamps[2][0] < stamps[0][1]

fig, ax = plt.subplots(figsize=(8, 3.5))
plot_space_time(history, ax=ax)
fig.tight_layout()

# %%
# Exercise
# --------
# Add a message from P0 to P2 sent right after ``a`` and received before
# ``b``. Which timestamps change, and is ``a`` still concurrent with ``b``?
