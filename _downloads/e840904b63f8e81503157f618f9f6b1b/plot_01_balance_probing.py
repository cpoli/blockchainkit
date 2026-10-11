r"""
Balance probing and payment privacy in Lightning (Herrera-Joancomartí et al., 2019)
===================================================================================

Lightning routes a payment over several channels with hash time-locked
contracts: each hop forwards the amount minus its fee, with an expiry a
margin earlier than the one it was offered. The sender sees every
channel's capacity but not how it is split, which is meant to keep
balances, and so payments, private.

Herrera-Joancomartí and co-authors showed that the split leaks. A prober
routes a payment through the target channel with a payment hash nobody can
claim. If the channel cannot forward the amount, the error comes from it;
if it can, the payment fails at the recipient with a different error. No
money moves, and a binary search finds the balance of a channel of
capacity :math:`C` in

.. math::

   \lceil \log_2 (C + 1) \rceil \text{ probes}.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.channels.visualizers import plot_route
from blockchainkit.network import Graph

# %%
# A payment across a random channel network
# -----------------------------------------
# The sender picks a route by capacity. Here one hop lacks the balance, and
# its error tells the sender which one: the leak that probing exploits.

graph = bk.network.watts_strogatz(40, 4, 0.2, seed=6)
network = bk.channels.ChannelNetwork.random(graph, capacity=100_000, seed=6)
route = network.find_route(0, 20, 10_000, height=800_000)
attempt = network.send(route)
print("route:", route.nodes, "success:", attempt.success, "failed at:", attempt.failed_at)
assert attempt.error == "temporary_channel_failure"

# %%
# Probing forty channels
# ----------------------
# The prober opens a well-funded channel to one end of each target
# channel, then probes it.

edges = graph.edges[:40]
spy_graph = Graph(graph.n + 1, [*graph.edges, *((graph.n, u) for u, _ in edges)])
balances = {}
for u, v in graph.edges:
    balances[u, v], balances[v, u] = network.balance(u, v), network.balance(v, u)
for u, _ in edges:
    balances[graph.n, u], balances[u, graph.n] = 10**9, 0
spy = bk.channels.ChannelNetwork(spy_graph, balances)
true, found, probes = [], [], []
for u, v in edges:
    result = bk.channels.probe_balance(spy, graph.n, u, v)
    true.append(spy.balance(u, v))
    found.append(result.low)
    probes.append(result.probes)
assert found == true and max(probes) <= 17
print(f"{len(edges)} balances found exactly, with at most {max(probes)} probes each")

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
plot_route(route, ax=left)
right.scatter(true, found, color="#dc2626")
right.plot([0, 100_000], [0, 100_000], color="#64748b", linestyle="--")
right.set(xlabel="true balance", ylabel="balance found by probing")
right.set_title(f"Every channel's split, {max(probes)} probes each")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A node could hide its balance by refusing some payments it could forward,
# answering ``temporary_channel_failure`` at random. How does that affect
# the binary search, and what does it cost honest senders?
