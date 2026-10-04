"""
Eclipse attacks on Bitcoin's peer table (Heilman et al. 2015)
=============================================================

A Bitcoin node chooses its outbound connections from a table of addresses it
has heard about. Heilman, Kendler, Zohar and Goldberg showed that an attacker
who floods that table with its own addresses, and waits for a restart, can
own every connection. The *eclipsed* node then sees only what the attacker
shows it: it can be fed a fake chain or have its blocks withheld. Bitcoin's
defense is *bucketing*, which the paper's countermeasures strengthened: an
address's bucket depends on its network group, and each group can reach
only a few buckets.

What to look for
----------------

Without bucketing, a flood of 5000 attacker addresses from four network
groups fills nearly the whole table, and most sets of eight connections are
entirely the attacker's. With bucketing, the same flood is confined to at
most 16 of the 64 buckets, and choosing a bucket before an entry makes an
all-attacker selection vanishingly rare.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# Flood a table with and without bucketing
# ----------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

results = {}
for label, per_group in (("unbucketed", None), ("bucketed", 4)):
    table = bk.network.AddressManager(
        buckets=64, bucket_size=16, buckets_per_group=per_group, seed=1
    )
    for i in range(1000):  # Honest addresses, each from its own group.
        table.add(f"honest-{i}", f"group-{i}")
    for i in range(5000):  # The attacker controls four groups.
        table.add(f"attacker-{i}", f"attacker-group-{i % 4}")
    share = sum(a.startswith("attacker") for a in table.addresses) / len(table.addresses)
    eclipsed = (
        sum(all(a.startswith("attacker") for a in table.select(8)) for _ in range(2000)) / 2000
    )
    buckets = {table.bucket_of(f"attacker-{i}", f"attacker-group-{i % 4}") for i in range(5000)}
    results[label] = (share, eclipsed)
    print(f"{label}: attacker share {share:.2f} in {len(buckets)} buckets, eclipsed {eclipsed:.4f}")
assert results["unbucketed"][1] > 0.5
assert len(buckets) <= 4 * 4 and results["bucketed"][1] == 0

# %%
# More connections help only against a small share
# ------------------------------------------------
# If each connection were an independent draw from a table in which a
# fraction f of the entries are the attacker's, all of them would be
# attackers with probability f**k. Against a poisoned table, extra
# connections barely help; against a defended one, each extra connection
# multiplies the attacker's odds down.
outbound = range(1, 21)
shares = {
    "unbucketed table": results["unbucketed"][0],
    "half": 0.5,
    "bucketed table": results["bucketed"][0],
}
assert bk.network.eclipse_probability(shares["unbucketed table"], 20) > 0.5

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
eclipsed = [value for _, value in results.values()]
left.bar(results.keys(), eclipsed, color=["#dc2626", "#16a34a"])
left.set(ylabel="P(all 8 connections are attackers)", title="Bucketing (simulated)")
for label, f in shares.items():
    right.semilogy(
        outbound,
        [bk.network.eclipse_probability(f, k) for k in outbound],
        "o-",
        markersize=3,
        label=f"{label}, f = {f:.2f}",
    )
right.set(xlabel="outbound connections k", ylabel="f ** k", title="Independent-draw model")
right.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# In the bucketed table, a selection picks a random nonempty bucket first.
# If the attacker owns 16 of 64 buckets outright, what is the probability
# that all eight picks land in its buckets? Compare with the simulation.
