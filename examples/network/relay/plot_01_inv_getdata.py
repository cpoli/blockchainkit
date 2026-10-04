"""
Announce, then fetch: Bitcoin's inv/getdata relay (Nakamoto 2009)
=================================================================

The simplest relay floods: every peer forwards a new block over each of its
links, so a peer with eight neighbors may receive it eight times. The first
Bitcoin client instead *announces*: it sends a small ``inv`` message
carrying the block's hash, and sends the block only to peers that ask for it
with ``getdata``. Each peer downloads each block once.

What to look for
----------------

Announcing cuts the traffic by roughly the average degree, and the saving
grows as peers keep more connections. The price is latency: each hop now
needs three one-way messages (inv, getdata, block) instead of one, which is
the delay that compact blocks later attacked.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# A 1 MB block on a random network of 500 peers
# ---------------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

size = 1_000_000
degrees = [4, 8, 16, 32]
flood, announce = [], []
for d in degrees:
    graph = bk.network.watts_strogatz(500, d, 1.0, seed=1)
    assert graph.is_connected()
    flood.append(bk.network.relay_cost(graph, size=size))
    announce.append(bk.network.relay_cost(graph, size=size, mode="announce"))
for d, f, a in zip(degrees, flood, announce, strict=True):
    print(f"degree {d:2d}: flood {f.bytes / 1e6:6.0f} MB, announce {a.bytes / 1e6:4.0f} MB")
assert all(a.bytes < f.bytes / (d / 2) for d, f, a in zip(degrees, flood, announce, strict=True))
assert all(a.completion == 3 * f.completion for f, a in zip(flood, announce, strict=True))

# %%
# Check the count against the simulator
# -------------------------------------
# Every message the simulator hands to a link is counted, including the
# duplicates that receivers discard.
graph = bk.network.watts_strogatz(500, 8, 1.0, seed=1)
network = bk.network.SimulatedNetwork.from_graph(graph)
network.broadcast("0", b"block")
network.run()
assert network.messages_sent == bk.network.relay_cost(graph, size=size).messages
print(network.messages_sent, "full-block copies sent to reach", len(network.deliveries), "peers")

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
left.plot(degrees, [f.bytes / 1e9 for f in flood], "o-", label="flood")
left.plot(degrees, [a.bytes / 1e9 for a in announce], "s-", label="inv/getdata")
left.set(xlabel="links per peer", ylabel="GB sent network-wide", title="Traffic for one block")
left.legend()
right.plot(degrees, [f.completion for f in flood], "o-", label="flood")
right.plot(degrees, [a.completion for a in announce], "s-", label="inv/getdata")
right.set(xlabel="links per peer", ylabel="one-way latencies", title="Time to reach every peer")
right.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Bitcoin relays transactions the same way. Transactions are about 250
# bytes, while an ``inv`` costs 61 bytes. Does announcing still pay off, and
# how would batching many hashes into one ``inv`` change the answer?
