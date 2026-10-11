r"""
Mining games: when honest mining is an equilibrium (Kiayias et al. 2016)
========================================================================

Kiayias, Koutsoupias, Kyropoulou and Tselekounis modeled Bitcoin mining as
a stochastic game in which each miner chooses which block to extend and
when to publish. Honest mining, extending the longest chain and publishing
at once, is the designer's intended behavior; they showed it is a best
response to the others' honesty when every miner is small, but not for a
large one, and that other equilibria then arise.

The experiment computes that best response. Against honest miners, a miner
of share :math:`\alpha` may withhold blocks, publish them to override or tie
the public chain, or give up. As a Markov decision process over the lengths
of the private and public branches (Sapirshtein, Sompolinsky and Zohar),
its best long-run share of the chain is

.. math::

   \rho^*(\alpha, \gamma) = \max_\pi \frac{\text{its blocks}}{\text{all blocks}} \ge \alpha,

and honest mining is an equilibrium exactly when :math:`\rho^* = \alpha`.
Here :math:`\gamma` is the fraction of the others who build on its block
during a tie.
"""

# %%
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

# %%
# The best response against honest miners
# ---------------------------------------

alphas = np.round(np.arange(0.05, 0.46, 0.05), 2)
fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.plot(alphas, alphas, "--", color="black", label="honest: share = alpha")
for gamma, color in ((0.0, "#2563eb"), (0.5, "#16a34a")):
    best = [bk.economics.optimal_mining_revenue(a, gamma, max_lead=8) for a in alphas]
    selfish = [bk.consensus.selfish_mining_revenue(a, gamma) for a in alphas]
    ax.plot(alphas, best, "o-", color=color, label=f"best response, gamma = {gamma}")
    ax.plot(alphas, selfish, ":", color=color, label=f"selfish mining, gamma = {gamma}")
ax.set(xlabel="hashrate alpha", ylabel="share of the chain's blocks")
ax.set_title("Small miners mine honestly; large ones do better by deviating")
ax.legend(fontsize=8)
fig.tight_layout()

# %%
# Where honesty stops being a best response
# -----------------------------------------


def threshold(gamma, low=0.05, high=0.45):
    while high - low > 0.005:
        middle = (low + high) / 2
        if bk.economics.honest_mining_is_equilibrium(middle, gamma, max_lead=8):
            low = middle
        else:
            high = middle
    return low


for gamma in (0.0, 0.5):
    found = threshold(gamma)
    eyal_sirer = bk.consensus.selfish_mining_threshold(gamma)
    print(
        f"gamma = {gamma}: honest up to alpha ~ {found:.3f} "
        f"(selfish mining pays above {eyal_sirer:.3f})"
    )
    assert found <= eyal_sirer + 0.005

assert bk.economics.honest_mining_is_equilibrium(0.2, 0.0, max_lead=8)
assert not bk.economics.honest_mining_is_equilibrium(0.4, 0.0, max_lead=8)

plt.show()

# %%
# Exercise
# --------
# The model caps both branches at ``max_lead`` blocks. Recompute the best
# response of a 40% miner with ``max_lead`` of 4, 8 and 12. Why can a larger
# cap only raise it, and why does it matter more for large miners?
