"""
Cryptographic sortition: a secret, stake-weighted committee (Algorand 2017)
===========================================================================

Algorand chooses a small committee each round by lottery: every unit of
stake is a ticket, and each user privately evaluates a verifiable random
function on the round seed to learn how many of their tickets won. Nobody
can target the committee in advance, because members reveal themselves only
when they vote.

What to look for
----------------

Seats are proportional to stake, and splitting stake into many accounts
earns the same expected seats: there is no Sybil advantage. Committee size
varies from round to round around its expected value.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Run 300 rounds
# --------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

stakes = {"alice": 4000, "bob": 3000, "carol": 2000, "dave": 1000}
total, expected = sum(stakes.values()), 30
seats = {name: [] for name in stakes}
for r in range(300):
    seed = r.to_bytes(4, "big")
    for name, stake in stakes.items():
        seats[name].append(
            bk.consensus.sortition(name.encode(), stake, total, expected, round_seed=seed)
        )
means = {name: np.mean(v) for name, v in seats.items()}
for name, stake in stakes.items():
    assert abs(means[name] - expected * stake / total) < 1.5
committee = np.sum([seats[name] for name in stakes], axis=0)

# %%
# Splitting stake gains nothing
# -----------------------------
split = [
    sum(
        bk.consensus.sortition(
            f"dave-{i}".encode(), 100, total, expected, round_seed=r.to_bytes(4, "big")
        )
        for i in range(10)
    )
    for r in range(300)
]
assert abs(np.mean(split) - means["dave"]) < 1.0

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 3.8))
left.bar(stakes.keys(), [means[n] for n in stakes], color="#2563eb", label="mean seats")
left.plot(
    list(stakes),
    [expected * s / total for s in stakes.values()],
    "o",
    color="black",
    label="expected",
)
left.set(ylabel="seats per round", title="Seats follow stake")
left.legend()
right.hist(committee, bins=20, color="#16a34a", edgecolor="white")
right.axvline(expected, color="black", linestyle="--")
right.set(xlabel="committee size", title=f"Committee size around {expected}")
fig.tight_layout()

# %%
# Exercise
# --------
# The hash here is computed from a private secret, so others cannot check a
# user's claimed seats. What does a verifiable random function add, and why
# must the round seed itself be unpredictable?
