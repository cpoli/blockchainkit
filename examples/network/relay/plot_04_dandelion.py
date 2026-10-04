"""
Dandelion: hiding where a transaction came from (Bojja Venkatakrishnan et al. 2017)
===================================================================================

When a peer broadcasts its own transaction by diffusion, it is usually the
first to send it, so spy nodes that connect widely can guess the origin by
noting which peer delivered each transaction to them first. Bojja
Venkatakrishnan, Fanti and Viswanath proposed Dandelion: first pass the
transaction along a random path (the *stem*), each hop continuing with a
fixed probability, and only then diffuse it (the *fluff*). Spies then see
the end of the stem.

What to look for
----------------

With 10% spies, the first-spy estimator names the true origin about half as
often under Dandelion as under diffusion. Precision does not reach zero:
when the origin's first stem hop happens to be a spy, the spy knows exactly
who sent it.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# 10% spies on a 300-peer network
# -------------------------------
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

graph = bk.network.watts_strogatz(300, 8, 0.3, seed=4)
spies = set(Random(5).sample(range(300), 30))
precision = {
    mode: bk.network.first_spy_precision(graph, spies, mode=mode, trials=600, seed=1)
    for mode in ("diffusion", "dandelion")
}
print(precision)
assert precision["dandelion"] < 0.7 * precision["diffusion"]

# %%
# Longer stems
# ------------
# The stem continues with probability q at each hop, so its expected length
# is 1 / (1 - q).
qs = [0.0, 0.5, 0.75, 0.9]
stem = [
    bk.network.first_spy_precision(
        graph, spies, mode="dandelion", stem_probability=q, trials=600, seed=2
    )
    for q in qs
]
print([round(p, 3) for p in stem])
assert stem[-1] < stem[0]

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
left.bar(precision.keys(), precision.values(), color=["#dc2626", "#16a34a"])
left.set(ylabel="P(origin identified)", title="First-spy estimator")
right.plot([1 / (1 - q) for q in qs], stem, "o-")
right.set(xlabel="expected stem length", ylabel="P(origin identified)", title="Dandelion")
fig.tight_layout()

# %%
# Exercise
# --------
# Precision is roughly bounded below by the spy fraction: the chance the
# first stem hop is a spy. Vary the number of spies and plot both modes.
# Why does the original design route stems over a line-shaped anonymity
# graph rather than the full peer graph?
