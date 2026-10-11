r"""
The instability of Bitcoin without the block reward (Carlsten et al. 2016)
==========================================================================

When the subsidy is gone, a block earns only the fees it collects. Fees
arrive steadily, blocks at exponentially distributed intervals, so a
block's reward is proportional to the time since the previous one, and as
variable as that time. Carlsten, Kalodner, Weinberg and Narayanan showed two
consequences.

Right after a block the mempool is nearly empty, so the next block is worth
less than the electricity to find it, and rational miners pause: a *mining
gap* of

.. math::

   t^* = \max\left(0, \frac{c - S}{f}\right)

seconds, for a cost :math:`c` per expected block, a subsidy :math:`S` and
fees arriving at :math:`f` per second. And when the tip block claimed more
fees than are left, a miner gains by forking it and *undercutting*: it
claims only part of those fees, leaving the rest as a bribe for whoever
builds on its block instead.
"""

# %%
import statistics

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Reward variance
# ---------------

FEE_RATE = 0.0005  # Fees per second: 0.3 BTC per 600-second block on average.
subsidized = bk.economics.simulate_block_rewards(3.125, FEE_RATE, blocks=5_000, seed=1)
fees_only = bk.economics.simulate_block_rewards(0.0, FEE_RATE, blocks=5_000, seed=1)
for label, rewards in (("with subsidy", subsidized), ("fees only", fees_only)):
    variation = statistics.pstdev(rewards) / statistics.mean(rewards)
    print(
        f"{label}: mean {statistics.mean(rewards):.3f} BTC, "
        f"coefficient of variation {variation:.2f}"
    )
assert statistics.pstdev(fees_only) / statistics.mean(fees_only) > 0.9

fig, (left, middle, right) = plt.subplots(1, 3, figsize=(14, 4.2))
left.hist(subsidized, bins=50, color="#2563eb", alpha=0.7, label="subsidy 3.125 + fees")
left.hist(fees_only, bins=50, color="#dc2626", alpha=0.7, label="fees only")
left.set(xlabel="block reward (BTC)", ylabel="blocks", yscale="log")
left.set_title("Fee-only rewards are as variable as block times")
left.legend()

# %%
# The mining gap
# --------------

costs = [0.1 * i for i in range(1, 11)]
for subsidy, color in ((0.0, "#dc2626"), (0.25, "#d97706"), (3.125, "#2563eb")):
    gaps = [bk.economics.mining_gap(subsidy, FEE_RATE, c) / 60 for c in costs]
    middle.plot(costs, gaps, "o-", color=color, label=f"subsidy {subsidy}")
middle.set(xlabel="mining cost per expected block (BTC)", ylabel="idle minutes after a block")
middle.set_title("Miners pause until fees accumulate")
middle.legend()
assert bk.economics.mining_gap(0.0, FEE_RATE, 0.25) == 500  # Most of a block interval.
assert bk.economics.mining_gap(3.125, FEE_RATE, 1.0) == 0

# %%
# Undercutting a wealthy block
# ----------------------------
#
# A 20% miner sees a tip that claimed ``tip`` BTC of fees while 0.05 BTC
# wait in the mempool. It forks the tip, keeping 80% of all the fees.

tips = [0.05 * i for i in range(1, 41)]
for subsidy, color in ((0.0, "#dc2626"), (3.125, "#2563eb")):
    gains = []
    for tip in tips:
        payoff = bk.economics.undercutting_payoffs(0.2, tip, 0.05, kept=0.8, subsidy=subsidy)
        gains.append(payoff["undercut"] / payoff["honest"] - 1)
    right.plot(tips, gains, color=color, label=f"subsidy {subsidy}")
right.axhline(0, color="black", linestyle=":")
right.set(xlabel="fees claimed by the tip (BTC)", ylabel="relative gain from undercutting")
right.set_title("Without a subsidy, forking pays handsomely")
right.legend()
fig.tight_layout()

whale = bk.economics.undercutting_payoffs(0.2, 1.0, 0.05, kept=0.8)
print("fee-only undercut of a 1 BTC block:", {k: round(v, 3) for k, v in whale.items()})
assert whale["undercut"] > 10 * whale["honest"]

plt.show()

# %%
# Exercise
# --------
# Undercutting works only if other miners prefer the undercutting branch.
# For a tip of 1 BTC and 0.05 BTC pending, what is the largest fraction
# ``kept`` for which they do? What happens to the next miner's incentive if
# everyone undercuts?
