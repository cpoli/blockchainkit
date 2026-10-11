r"""
Schelling's focal points: coordinating without communicating (1960)
===================================================================

Two people must meet in a city on the same day, without having agreed where
or when. Any place and time is a good answer if both choose it, so game
theory alone predicts nothing. Schelling found that most people choose the
same one anyway, because it stands out: noon, at the main station. Such a
*focal point* lets players coordinate because each expects the others to
pick it.

Suppose each of :math:`k` players picks the focal option with probability
:math:`s`, its *salience*, and otherwise picks any of :math:`n` options at
random. All of them coincide with probability

.. math::

   P = \left(s + \frac{1-s}{n}\right)^k + (n - 1)\left(\frac{1-s}{n}\right)^k.

Without salience, coordination collapses as players are added; with even a
moderately salient answer it does not. Blockchain oracles and voting games
rely on the truth being such an answer.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Chance against salience
# -----------------------

options = 10
for salience in (0.0, 0.5):
    measured = bk.economics.play_coordination(5, options, salience, rounds=20_000, seed=1)
    exact = bk.economics.coordination_probability(5, options, salience)
    print(f"salience {salience}: five players meet {measured:.2%} of the time (exact {exact:.2%})")
    assert abs(measured - exact) < 0.01

assert bk.economics.coordination_probability(5, options, 0.0) < 1e-3
assert bk.economics.coordination_probability(5, options, 0.5) > 0.03

fig, ax = plt.subplots(figsize=(7, 4.5))
players = range(2, 21)
for salience, color in ((0.0, "#64748b"), (0.3, "#2563eb"), (0.6, "#16a34a"), (0.9, "#dc2626")):
    chances = [bk.economics.coordination_probability(k, options, salience) for k in players]
    ax.semilogy(players, chances, "o-", color=color, label=f"salience {salience}")
ax.set(
    xlabel="players",
    ylabel="probability that all choose alike",
    title=f"Coordinating on one of {options} options",
)
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# With 20 players and 10 options, what salience gives an even chance that
# everyone coincides? Why does a large group need a much more obvious focal
# point than a pair?
# A worked solution is in :doc:`/exercises/economics`.
