r"""
Decker and Wattenhofer's duplex micropayment channels (2015)
============================================================

A Spilman channel pays one way and is spent once its capacity has gone to
the payee. Decker and Wattenhofer pair two of them, one in each direction,
and *reset* the pair when one side runs dry, re-funding both from the
current balances. Without penalties, the newest pair must beat every older
one to the chain, and an *invalidation tree* of relative lock times sees to
that: at every level, each replacement lowers the lock time by
:math:`\delta`, so where two branches part, the newer one is valid first
and spends the shared parent. A tree of depth ``d`` with ``s`` lock-time
values per level holds ``s^d`` resets, and closing waits for up to

.. math::

   d\,(s - 1)\,\delta

blocks.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The newest branch always wins
# -----------------------------

depth, steps, delta = 2, 4, 6
locks = [
    bk.channels.invalidation_locktimes(s, depth=depth, steps=steps, delta=delta)
    for s in range(steps**depth)
]
print("state 5 lock times:", locks[5], " state 6:", locks[6])
rng = Random(3)
for _ in range(100):
    published = rng.sample(range(steps**depth), 3)
    winner = bk.channels.first_confirmed(published, depth=depth, steps=steps, delta=delta)
    assert winner == max(published)

# %%
# Ping-pong payments until the tree is used up
# --------------------------------------------

channel = bk.channels.DuplexChannel(
    ("alice", "bob"), (50, 50), depth=depth, steps=steps, delta=delta
)
payments = 0
try:
    while True:
        channel.pay("alice", 40)
        channel.pay("bob", 40)
        payments += 2
except ValueError as error:
    print(f"after {payments} payments and {channel.resets} resets: {error}")
assert channel.resets == steps**depth - 1

# %%
# Capacity against closing delay
# ------------------------------
# More levels give exponentially more resets, but closing waits for the
# lock times of every level.

shapes = [(d, s) for d in (1, 2, 3, 4) for s in (2, 4, 8, 16)]
for d, s in shapes:
    worst = sum(bk.channels.invalidation_locktimes(0, depth=d, steps=s, delta=delta))
    assert worst == d * (s - 1) * delta

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
left.plot(range(steps**depth), [sum(lock) for lock in locks], "o-", color="#2563eb")
left.set(xlabel="reset number", ylabel="blocks to close (sum of lock times)")
left.set_title("Newer states close sooner")
for d, color in zip((1, 2, 3, 4), ("#2563eb", "#16a34a", "#d97706", "#dc2626"), strict=True):
    points = [(s**d, d * (s - 1) * delta) for dd, s in shapes if dd == d]
    right.plot(*zip(*points, strict=True), "o-", color=color, label=f"depth {d}")
right.set_xscale("log")
right.set(xlabel="resets the tree supports", ylabel="worst-case blocks to close")
right.set_title("Deeper trees: more resets for the same delay")
right.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# With ``delta = 6`` blocks, which shape of tree supports a million resets
# while closing within a day (144 blocks)? Compare with Lightning, whose
# number of updates is not limited by its delay at all.
# A worked solution is in :doc:`/exercises/channels`.
