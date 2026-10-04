"""
Nothing at stake: why proof of stake needs penalties (Buterin 2014)
===================================================================

A proof-of-work miner must divide its hashrate between competing forks; a
proof-of-stake validator can sign every fork at no cost and collect the
reward whichever one wins. If everyone does that, forks never resolve.
Buterin's Slasher proposal made such double-signing punishable: evidence
of two conflicting signatures destroys the validator's deposit.

What to look for
----------------

Without a penalty, signing both forks pays more than any honest choice.
Once the penalty exceeds the reward lost by picking one side, picking a
side wins. Every modern proof-of-stake protocol has slashing.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Payoffs without slashing
# ------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

free = bk.consensus.fork_voting_payoffs(0.6, reward=1.0, penalty=0.0)
print("no penalty:", free)
assert free["both"] > free["A"] > free["B"]

# %%
# Payoffs as the penalty grows
# ----------------------------
penalties = np.linspace(0, 1.5, 61)
rows = [bk.consensus.fork_voting_payoffs(0.6, 1.0, p) for p in penalties]
fig, ax = plt.subplots(figsize=(7, 4))
for strategy, color in (("A", "#2563eb"), ("B", "#64748b"), ("both", "#dc2626")):
    ax.plot(penalties, [r[strategy] for r in rows], color=color, label=f"vote {strategy}")
crossover = 1.0 - 0.6
ax.axvline(crossover, color="black", linestyle=":", label="penalty = reward lost by choosing")
ax.set(
    xlabel="slashing penalty",
    ylabel="expected payoff",
    title="Slashing makes choosing a fork the best response",
)
ax.legend()
fig.tight_layout()
assert (
    bk.consensus.fork_voting_payoffs(0.6, 1.0, 0.5)["A"]
    > bk.consensus.fork_voting_payoffs(0.6, 1.0, 0.5)["both"]
)

# %%
# Exercise
# --------
# Slashing only works while the deposit can still be taken. Explain the
# long-range attack: why could keys of validators who withdrew long ago be
# used to forge an alternative history, and what "weak subjectivity" asks
# new nodes to trust?
