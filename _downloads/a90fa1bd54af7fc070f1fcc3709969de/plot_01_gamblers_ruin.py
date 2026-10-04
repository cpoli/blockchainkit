"""
The gambler's ruin: catching up from behind (Pascal, Fermat and Huygens 1656)
=============================================================================

Pascal posed, and Huygens published, the problem of a gambler who wins each
round with probability q and stops when ruined or ahead. The chance of ever
recovering a deficit of z is (q/p)**z when q < p. Nakamoto used exactly
this random walk for an attacker trying to overtake the honest chain from z
blocks behind.

What to look for
----------------

Simulated random walks match (q/p)**z. An attacker with less than half the
hashrate falls exponentially further from success with every block of lead,
and at q = 1/2 the walk always catches up eventually.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Simulate the race
# -----------------
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk


def caught_up(q, deficit, rng, horizon=500):
    for _ in range(horizon):
        if deficit <= 0:
            return True
        deficit += -1 if rng.random() < q else 1
    return deficit <= 0


rng = Random(1656)
deficits = range(0, 9)
fig, ax = plt.subplots(figsize=(7, 4))
for q, color in ((0.1, "#2563eb"), (0.25, "#16a34a"), (0.4, "#ea580c")):
    simulated = [sum(caught_up(q, z, rng) for _ in range(2000)) / 2000 for z in deficits]
    exact = [bk.consensus.eventual_catch_up(q, z) for z in deficits]
    assert all(abs(a - b) < 0.04 for a, b in zip(simulated, exact, strict=True))
    ax.semilogy(deficits, exact, "-", color=color, label=f"q = {q}: (q/p)**z")
    ax.semilogy(deficits, [max(s, 1e-4) for s in simulated], "o", color=color)
ax.set(
    xlabel="blocks behind z",
    ylabel="probability of ever catching up",
    title="Exponentially unlikely, unless q >= 1/2",
)
ax.legend()
fig.tight_layout()

# %%
assert bk.consensus.eventual_catch_up(0.5, 20) == 1.0

# %%
# Exercise
# --------
# The model assumes the race never ends. Why does that make (q/p)**z an
# overestimate of the attacker's chances against a merchant who waits only
# for z confirmations? (The next example answers this.)
