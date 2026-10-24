r"""
CoinJoin: many payers, one transaction (2013)
=============================================

Gregory Maxwell observed that the inputs of a Bitcoin transaction need
not belong to one person. In a CoinJoin, several users each contribute an
input and name an output; each checks the joint transaction and signs only
its own input. If the mixed outputs all have one *denomination* :math:`d`,
an observer cannot tell whose is whose, and the common-input heuristic now
merges strangers.

Change is the weak point. Each change output is an input minus :math:`d`,

.. math::

   \text{change}_i = a_i - d ,

which usually points straight back at its input. Only the equal outputs
are anonymous: :math:`n` of them hide each participant among :math:`n`.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# One round
# ---------

participants = [("ann", "a1", 10), ("bob", "b1", 13), ("cat", "c1", 17), ("dan", "d1", 10)]
round_ = bk.privacy.coinjoin(participants, 10, seed=1)
for address, amount in round_.transaction.outputs:
    print(f"{address}  {amount:>3}")
print("anonymity set of the 10-coin outputs:", round_.anonymity_set)
links = bk.privacy.link_change(round_.transaction, 10)
assert all(round_.owners[c] == round_.owners[i] for c, i in links.items())
print("change linked to its input:", {round_.owners[c] for c in links})

clusters = bk.privacy.cluster_addresses([round_.transaction])
score = bk.privacy.score_clusters(clusters, round_.owners)
assert score.false_merges == 1
print("the input heuristic merges", len(clusters[0]), "addresses of 4 users into one cluster")

# %%
# Larger rounds
# -------------
# Inputs between 10 and 30 coins, denomination 10.

rng = Random(4)
sizes = [2, 5, 10, 20, 50]
anonymous, linked = [], []
for n in sizes:
    people = [(f"u{i}", f"in{i}", rng.randrange(10, 31)) for i in range(n)]
    r = bk.privacy.coinjoin(people, 10, seed=n)
    anonymous.append(r.anonymity_set)
    linked.append(len(bk.privacy.link_change(r.transaction, 10)) / n)
# A change output that happens to equal the denomination joins the set too.
assert all(a >= n for a, n in zip(anonymous, sizes, strict=True))

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(sizes, linked, marker="o", color="#dc2626")
ax.set(xlabel="participants", ylabel="fraction of change outputs linked", ylim=(0, 1.05))
ax.set_title("Equal outputs hide among n; change points back to its input")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# In a round of three with inputs 15, 15 and 25 and denomination 10, which
# change outputs can :func:`~blockchainkit.privacy.systems.coinjoin.link_change`
# link? What does that suggest about choosing inputs?
# A worked solution is in :doc:`/exercises/privacy`.
