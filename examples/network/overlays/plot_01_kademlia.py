"""
Kademlia: routing by XOR distance (Maymounkov and Mazières 2002)
================================================================

A distributed hash table stores each key at the nodes whose identifiers are
closest to it, and lets any node find them without a central index.
Kademlia measures closeness as the XOR of two identifiers. Each node keeps
a *k-bucket* of contacts at every distance scale: a few nodes that share
none of its leading bits, a few that share exactly one, and so on. Every
hop toward a key at least fixes the next differing bit, so a lookup among n
nodes takes about ``log2 n`` hops at most and far fewer on average.
Ethereum's discovery protocol and IPFS use Kademlia.

What to look for
----------------

Every lookup ends at the true closest node. The number of hops grows by a
constant each time n quadruples: logarithmic growth, a straight line on a
log axis. Larger buckets mean fewer hops, at the price of bigger tables.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# Build networks of 64 to 4096 nodes
# ----------------------------------
from random import Random

import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

random = Random(1)
sizes = [64, 256, 1024, 4096]
mean_hops = {1: [], 4: []}
for n in sizes:
    ids = random.sample(range(2**32), n)
    for k in mean_hops:
        network = bk.network.KademliaNetwork(ids, bits=32, k=k, seed=1)
        hops = []
        for _ in range(200):
            target = random.randrange(2**32)
            result = network.lookup(random.choice(ids), target)
            assert result.found == network.closest(target, 1)[0]
            hops.append(result.hops)
        mean_hops[k].append(np.mean(hops))
print({k: [round(float(h), 2) for h in v] for k, v in mean_hops.items()})
steps = np.diff(mean_hops[1])
assert all(0.4 < step < 1.6 for step in steps)  # About one more hop per quadrupling.

# %%
# One lookup, bit by bit
# ----------------------
# Each hop shares a longer prefix with the target.
network = bk.network.KademliaNetwork(ids, bits=32, k=1, seed=1)
target = 0xDEADBEEF
for node in network.lookup(ids[0], target).path:
    shared = 32 - bk.network.xor_distance(node, target).bit_length()
    print(f"{node:032b}  shares {shared:2d} leading bits")

fig, ax = plt.subplots(figsize=(6, 4))
for k, hops in mean_hops.items():
    ax.semilogx(sizes, hops, "o-", base=2, label=f"k = {k}")
ax.set(xlabel="nodes n", ylabel="mean hops", title="Lookups take O(log n) hops")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Real Kademlia queries ``alpha = 3`` contacts in parallel and keeps the
# ``k`` closest it has heard of. Why does that make a lookup robust when
# some contacts are offline, and how would you count its hops?
