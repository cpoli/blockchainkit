"""
Proof of stake: a stake-weighted proposer lottery (Peercoin 2012)
=================================================================

Weighting proposer selection by stake changes the resource used to allocate
influence. This sampler isolates that one mechanism; it has no voting,
slashing, randomness beacon, or finality and is not a full PoS protocol.

What to look for
----------------

Compare observed selection frequencies with stake proportions. More trials tend to bring
them closer; splitting one stake among names does not increase its combined expected
share.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
See :doc:`/exercises/consensus` for a worked solution to the exercise.
"""

# %%
from collections import Counter

import matplotlib.pyplot as plt

import blockchainkit as bk

stakes = {"alice": 10, "bob": 30, "carol": 60}
rounds = 10_000
proposers = bk.consensus.StakeSampler(stakes, seed=42).sample(rounds)
assert proposers == bk.consensus.StakeSampler(stakes, seed=42).sample(rounds)
counts = Counter(proposers)
expected = [stake / sum(stakes.values()) for stake in stakes.values()]
observed = [counts[name] / rounds for name in stakes]
print("Observed selection fractions:", dict(zip(stakes, observed, strict=True)))

# %%
# Stake concentration is visible even when the lottery is fair
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4))
xs = list(range(len(stakes)))
ax.bar([x - 0.18 for x in xs], expected, 0.36, label="Stake fraction")
ax.bar([x + 0.18 for x in xs], observed, 0.36, label="Observed proposer fraction")
ax.set(
    xticks=xs,
    xticklabels=list(stakes),
    ylabel="Fraction",
    title="Seeded proposer sampling over 10,000 rounds",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Split Carol's stake across ten names. Does her total expected influence
# change? Why is choosing a proposer insufficient to decide between two
# conflicting blocks that proposer might sign? Why is a public seed unsuitable
# as the sole randomness mechanism for a live consensus protocol?
