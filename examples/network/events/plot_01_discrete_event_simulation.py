"""
Discrete-event simulation: a network on an event queue (GPSS 1961, Simula 1965)
===============================================================================

A discrete-event simulator keeps a queue of future events ordered by time.
It pops the earliest, jumps the clock straight to it, and lets it schedule
new events. Nothing happens between events, so no time is wasted waiting,
and with a seeded random source every run is exactly reproducible.
:class:`~blockchainkit.network.systems.gossip.SimulatedNetwork` simulates gossip this way:
a message sent on a link becomes a delivery event a random number of ticks
later.

What to look for
----------------

Follow arrival times as the message crosses the network. An isolated peer
misses it, and reconnecting the peer requires an explicit retransmission of
old news. Rerunning with the same seed reproduces every arrival time.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
See :doc:`/tutorials/solutions` for a worked answer to the exercise.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

network = bk.network.SimulatedNetwork(["alice", "bob", "carol", "dave"], seed=7)
network.connect("alice", "bob", latency=(2, 4))
network.connect("bob", "carol", latency=(2, 4))
# Dave starts partitioned from the other three peers.
network.broadcast("alice", b"a new block announcement")
network.run(until=10)
assert {event.recipient for event in network.deliveries} == {"alice", "bob", "carol"}

# %%
# Healing requires synchronization, not just a link
# -------------------------------------------------
network.connect("carol", "dave", latency=(2, 2))
network.broadcast("carol", b"a new block announcement")
network.run()
assert network.deliveries[-1].recipient == "dave"
assert network.deliveries[-1].time == 12
print([(event.recipient, event.time) for event in network.deliveries])

# %%
# Same seed, same history
# -----------------------
# The simulator draws latencies from its own seeded generator, so a second
# run with the same operations reproduces every event exactly.


def replay(seed):
    net = bk.network.SimulatedNetwork(["alice", "bob", "carol", "dave"], seed=seed)
    net.connect("alice", "bob", latency=(2, 4))
    net.connect("bob", "carol", latency=(2, 4))
    net.broadcast("alice", b"a new block announcement")
    net.run(until=10)
    net.connect("carol", "dave", latency=(2, 2))
    net.broadcast("carol", b"a new block announcement")
    net.run()
    return net.deliveries


assert replay(7) == network.deliveries

# %%
fig, ax = plt.subplots(figsize=(8, 4))
names = [event.recipient for event in network.deliveries]
times = [event.time for event in network.deliveries]
ax.barh(names, times, color=["#2563eb"] * 3 + ["#ea580c"])
ax.axvline(10, color="black", linestyle="--", label="Partition healed")
ax.scatter(times, names, color="black", zorder=3)
ax.set(
    xlabel="First receipt time (simulation ticks)",
    title="Propagation and explicit resynchronization",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Connect a triangle and check that duplicate paths do not duplicate receipts.
# Disconnect a link while a message is in flight. Then replace fixed latency
# with a range and compare results under the same and different seeds.
