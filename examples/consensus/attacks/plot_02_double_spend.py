"""
How many confirmations? Nakamoto's double-spend calculation (2008)
==================================================================

Section 11 of the Bitcoin whitepaper asks how long a merchant should wait.
While the honest chain adds z blocks, the attacker's secret chain grows by
a Poisson-distributed amount with mean z q/p; from each possible lead the
gambler's ruin gives the chance to catch up. The whitepaper tabulates the
result, and concludes that the risk drops exponentially with z.

What to look for
----------------

The function reproduces the whitepaper's table, and a Monte-Carlo race
between two chains agrees. Six confirmations against a 10% attacker leave
about a 0.02% risk; against 30% it takes 24.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
See :doc:`/exercises/consensus` for a worked solution to the exercise.
"""

# %%
# The whitepaper's table
# ----------------------
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

for z, expected in ((0, 1.0), (1, 0.2045873), (2, 0.0509779), (5, 0.0009137), (10, 0.0000012)):
    assert abs(bk.consensus.attacker_success_probability(0.1, z) - expected) < 5e-8
print("q = 0.1, z = 6:", f"{bk.consensus.attacker_success_probability(0.1, 6):.7f}")


# %%
# A Monte-Carlo double-spend race
# -------------------------------
def attack_succeeds(q, z, rng, horizon=300):
    honest = attacker = 0
    while honest < z:  # The merchant waits for z blocks.
        if rng.random() < q:
            attacker += 1
        else:
            honest += 1
    for _ in range(horizon):  # Then the attacker keeps racing.
        if attacker > honest:
            return True
        if rng.random() < q:
            attacker += 1
        else:
            honest += 1
    return attacker > honest


rng = Random(2008)
zs = range(0, 11)
fig, ax = plt.subplots(figsize=(7, 4))
for q, color in ((0.1, "#2563eb"), (0.3, "#ea580c")):
    exact = [bk.consensus.attacker_success_probability(q, z) for z in zs]
    simulated = [sum(attack_succeeds(q, z, rng) for _ in range(3000)) / 3000 for z in zs]
    ax.semilogy(zs, exact, "-", color=color, label=f"q = {q}, whitepaper formula")
    ax.semilogy(
        zs, [max(s, 3e-4) for s in simulated], "o", color=color, label=f"q = {q}, simulated"
    )
ax.set(
    xlabel="confirmations z",
    ylabel="attacker success probability",
    title="Waiting longer makes double spends exponentially rarer",
)
ax.legend(fontsize=8)
fig.tight_layout()

# %%
# Exercise
# --------
# Find the smallest z with risk below 0.1% for q = 0.1, 0.2 and 0.3. Why does
# the required z grow so quickly as q approaches 1/2?
