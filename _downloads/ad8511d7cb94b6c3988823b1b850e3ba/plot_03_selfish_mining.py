"""
Selfish mining: majority is not enough (Eyal and Sirer 2014)
============================================================

Bitcoin was thought incentive-compatible: a miner earns its share of blocks
by publishing them. Eyal and Sirer showed a pool can earn more by keeping
blocks secret and releasing them only to overtake or tie the honest chain,
wasting honest work. Above a threshold hashrate, between 0 and 1/3
depending on how ties break, selfish mining pays.

What to look for
----------------

The simulated state machine matches the closed-form revenue. With
gamma = 0 (ties go to honest blocks) the threshold is 1/3; when the pool
wins every tie, any pool profits.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Revenue against hashrate
# ------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

alphas = np.linspace(0.02, 0.48, 24)
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(alphas, alphas, "--", color="black", label="honest mining: revenue = alpha")
for gamma, color in ((0.0, "#2563eb"), (0.5, "#16a34a"), (1.0, "#ea580c")):
    exact = [bk.consensus.selfish_mining_revenue(a, gamma) for a in alphas]
    ax.plot(alphas, exact, color=color, label=f"selfish, gamma = {gamma}")
    sims = [
        bk.consensus.simulate_selfish_mining(a, gamma, blocks=40_000, seed=7).revenue
        for a in alphas[::4]
    ]
    ax.plot(alphas[::4], sims, "o", color=color)
    threshold = bk.consensus.selfish_mining_threshold(gamma)
    ax.axvline(threshold, color=color, linestyle=":", alpha=0.7)
ax.set(
    xlabel="pool hashrate alpha",
    ylabel="pool share of blocks",
    title="Selfish mining pays above (1 - gamma)/(3 - 2 gamma)",
)
ax.legend(fontsize=8)
fig.tight_layout()

# %%
result = bk.consensus.simulate_selfish_mining(0.4, 0.0, blocks=200_000, seed=1)
assert result.revenue > 0.4
print(f"a 40% pool gets {result.revenue:.1%} of the blocks")

# %%
# Exercise
# --------
# Selfish mining lowers the total rate of blocks on the main chain. Explain
# why difficulty retargeting (the next experiment) turns that into profit
# for the pool in absolute terms, not just as a share.
