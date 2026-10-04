"""
Small-world networks: a few shortcuts (Watts and Strogatz 1998)
===============================================================

A ring lattice, where each peer knows its nearest neighbors, is highly
clustered: your neighbors know each other. But messages crawl around it,
taking about ``n / 2k`` hops. Watts and Strogatz rewired each link to a
random peer with a small probability and found that a handful of shortcuts
collapses path lengths almost to those of a random graph while clustering
barely changes: a *small world*, like "six degrees of separation".

What to look for
----------------

On the log scale of the rewiring probability, the path length L falls long
before the clustering C does. Around 1% rewiring, paths are already short
and the network is still clustered. Gossip benefits directly: it crosses
the network in a few hops.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# Reproduce the 1998 figure
# -------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk
from blockchainkit.network.visualizers import plot_graph

n, k = 400, 10
lattice = bk.network.ring_lattice(n, k)
L0, C0 = lattice.average_path_length(), lattice.clustering()
betas = np.logspace(-4, 0, 13)
L, C = [], []
for beta in betas:
    g = bk.network.watts_strogatz(n, k, float(beta), seed=1)
    L.append(g.average_path_length() / L0)
    C.append(g.clustering() / C0)
i = int(np.argmin(abs(betas - 0.01)))
print(f"beta = {betas[i]:.3f}: L/L0 = {L[i]:.2f}, C/C0 = {C[i]:.2f}")
assert L[i] < 0.5 and C[i] > 0.9

# %%
# Gossip on the two graphs
# ------------------------
rounds = {
    name: bk.network.spread_rumor(g, seed=2).rounds
    for name, g in [
        ("lattice", lattice),
        ("1% rewired", bk.network.watts_strogatz(n, k, 0.01, seed=1)),
    ]
}
print(rounds)
assert rounds["1% rewired"] < 0.6 * rounds["lattice"]

fig, (left, mid, right) = plt.subplots(1, 3, figsize=(12, 4))
left.semilogx(betas, L, "o", label="L(p) / L(0)")
left.semilogx(betas, C, "s", label="C(p) / C(0)")
left.set(xlabel="rewiring probability p", title="Short paths, still clustered")
left.legend()
plot_graph(bk.network.ring_lattice(30, 4), ax=mid)
plot_graph(bk.network.watts_strogatz(30, 4, 0.1, seed=3), ax=right)
mid.set_title("lattice")
right.set_title("10% rewired")
fig.tight_layout()

# %%
# Exercise
# --------
# Watts and Strogatz explained the gap with one shortcut: it cuts the path
# between many pairs at once, but changes the clustering of only the two
# nodes it touches. Check this by rewiring a single edge of the lattice by
# hand and recomputing L and C.
