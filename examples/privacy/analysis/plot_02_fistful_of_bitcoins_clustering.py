r"""
A Fistful of Bitcoins: clustering addresses by owner (2013)
===========================================================

Meiklejohn, Pomarole, Jordan, Levchenko, McCoy, Voelker and Savage showed
that fresh addresses hide much less than they seem. Two heuristics group
addresses that one user controls:

- the inputs of one transaction share an owner, who signed them all;
- a transaction's *change* goes to a fresh address: if exactly one output
  address has never been seen before, it is the sender's.

Each heuristic adds edges to a graph of addresses, and the clusters are
its connected components (found with union-find). Buying a few things from
a service then names its whole cluster.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.privacy.visualizers import plot_cluster_sizes

# %%
# A toy economy with known owners
# -------------------------------
# Payees reuse a receiving address 90% of the time, as shops do.

history = bk.privacy.simulate_payments(150, 1_500, reuse=0.9, seed=13)
print(f"{len(history.transactions)} transactions, {len(history.owners)} addresses, 150 users")
inputs_only = bk.privacy.cluster_addresses(history.transactions)
with_change = bk.privacy.cluster_addresses(history.transactions, change=True)
for name, clusters in (("inputs only", inputs_only), ("with change", with_change)):
    score = bk.privacy.score_clusters(clusters, history.owners)
    print(
        f"{name:12}: {score.clusters} clusters, {score.identified} users identified, "
        f"{score.false_merges} false merges"
    )
assert len(with_change) < len(inputs_only)

# %%
# When payees never reuse addresses
# ---------------------------------
# Two fresh outputs make the change ambiguous, and the heuristic abstains.

careful = bk.privacy.simulate_payments(150, 1_500, reuse=0.0, seed=13)
careful_clusters = bk.privacy.cluster_addresses(careful.transactions, change=True)
print("no reuse:", bk.privacy.score_clusters(careful_clusters, careful.owners))

fig, ax = plt.subplots(figsize=(6, 4))
plot_cluster_sizes(inputs_only, ax=ax, label="inputs only")
plot_cluster_sizes(with_change, ax=ax, label="inputs and change")
ax.set_title("Change outputs merge clusters into users")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A user always spends exactly one coin per payment. Which heuristic still
# links that user's addresses, and when does it abstain?
# A worked solution is in :doc:`/exercises/privacy`.
