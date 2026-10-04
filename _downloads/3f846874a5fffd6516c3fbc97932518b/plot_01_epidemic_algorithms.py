"""
Epidemic algorithms: push, pull and push-pull (Demers et al. 1987)
==================================================================

Demers and colleagues at Xerox PARC kept the replicas of a database
consistent by letting each replica periodically call a random other one and
exchange updates, like an infection passing between people. They compared
*push* (the caller sends what it knows), *pull* (the caller asks for what it
lacks), and both together.

What to look for
----------------

Push starts fast but finishes slowly: near the end, an informed caller
mostly reaches peers that already know, so the uninformed fraction shrinks
only by a constant factor per round. Pull is the reverse: an uninformed peer
stays uninformed only if it calls another uninformed peer, so once most
peers know, the uninformed fraction *squares* each round. Push-pull gets
both phases and finishes first.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# Spread one update among 4096 replicas
# -------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.network.visualizers import plot_rumor_spread

n = 4096
modes = ("push", "pull", "push-pull")
runs = {mode: bk.network.spread_rumor(n, mode=mode, seed=3) for mode in modes}
for mode, run in runs.items():
    print(f"{mode:9s} {run.rounds} rounds")
assert runs["push-pull"].rounds < runs["pull"].rounds < runs["push"].rounds

# %%
# Pull squares the residue
# ------------------------
# If a fraction s is uninformed at the start of a round, an uninformed peer
# calls another uninformed peer with probability about s.
residue = [1 - count / n for count in runs["pull"].informed]
for before, after in zip(residue, residue[1:], strict=False):
    if 0 < before < 0.5:
        print(f"{before:.4f} -> {after:.4f}   (s**2 = {before**2:.4f})")
        assert abs(after - before**2) < 0.02

# %%
# Push shrinks it by a constant factor
# ------------------------------------
# An uninformed peer escapes every one of about n informed callers with
# probability (1 - 1/n)**n, close to 1/e.
residue = [1 - count / n for count in runs["push"].informed]
late = [
    after / before
    for before, after in zip(residue, residue[1:], strict=False)
    if 0.01 < before < 0.2
]
print([round(ratio, 2) for ratio in late])
assert all(0.25 < ratio < 0.5 for ratio in late)

fig, ax = plt.subplots(figsize=(7, 4))
plot_rumor_spread(runs, ax=ax)
fig.tight_layout()

# %%
# Exercise
# --------
# Demers et al. also studied *rumor mongering*: a peer stops pushing once it
# has called k peers that already knew. Implement it with a loop around
# random calls and measure the *residue*, the fraction never informed, for
# k = 1, 2, 3.
