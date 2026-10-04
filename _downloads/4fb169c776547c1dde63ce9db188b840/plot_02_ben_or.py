"""
Randomized consensus: agreeing by flipping coins (Ben-Or 1983)
==============================================================

Michael Ben-Or showed that asynchronous processes can reach agreement despite
crashes if they may flip coins. In each round they exchange values, propose
any value held by a strict majority, and adopt a proposal they see, or flip
a coin if they see none. A decision follows once enough processes propose
the same value.

What to look for
----------------

Against a scheduler that delivers messages to keep processes split, the
protocol still decides: eventually the coins all land the same way. The
number of rounds is random, with an exponential tail.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
See :doc:`/exercises/consensus` for a worked solution to the exercise.
"""

# %%
# Decide despite an adversarial scheduler
# ---------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

run = bk.consensus.ben_or([0, 0, 1, 1], faults=1, seed=1983)
assert run.decided and len(set(run.decisions.values())) == 1
print(f"decided {set(run.decisions.values())} after {run.rounds} rounds")

# %%
# Unanimous inputs decide in one round
# ------------------------------------
assert bk.consensus.ben_or([1, 1, 1, 1], faults=1).rounds == 1

# %%
# How many rounds?
# ----------------
rounds = [bk.consensus.ben_or([0, 0, 1, 1], faults=1, seed=s).rounds for s in range(400)]
assert all(bk.consensus.ben_or([0, 1, 0, 1], faults=1, seed=s).decided for s in range(50))
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.hist(rounds, bins=range(1, max(rounds) + 2), color="#2563eb", edgecolor="white")
ax.axvline(sum(rounds) / len(rounds), color="black", linestyle="--", label="mean")
ax.set(
    xlabel="rounds to decide (4 processes, adversarial delivery)",
    ylabel="runs",
    title="Termination with probability one",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# The adversary here stalls unless all four coins agree, which happens with
# probability 2/16 per round. Derive the expected number of rounds and
# compare it with the histogram's mean.
