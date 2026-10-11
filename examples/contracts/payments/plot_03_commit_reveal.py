r"""
Commit-reveal schemes and on-chain randomness (2016)
====================================================

Every node must compute the same result, so a contract has no secret source
of randomness. Early lotteries drew from the previous block's hash, but a
contract called in the same block reads the same hash, so an attacker
computes the draw first and plays only when it wins. (A miner could also
discard a block whose hash it disliked.)

A *commit-reveal* scheme removes the shortcut. Each player first publishes
:math:`c_i = H(\text{player}, s_i, r_i)` for a secret :math:`s_i` and a
random salt :math:`r_i`; once every commitment is in, the players reveal,
and the draw combines all secrets:

.. math::

   \text{winner} = \Big(\bigoplus_i s_i\Big) \bmod n.

Nobody can choose a secret after seeing the others. The last player to
reveal does see the result first, and may withhold; in this contract that
costs nothing and raises his chance from 1/4 to 7/16. Penalties for not
revealing (as in RANDAO) and verifiable delay functions aim to remove the
bias.
"""

# %%
import random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Predicting the block-hash lottery
# ---------------------------------

world = bk.contracts.World(seed=4)
world.fund("house", 10_000)
world.fund("eve", 100)
lottery = world.deploy("house", bk.contracts.BlockhashLottery, 1, value=1_000)
predictor = world.deploy("eve", bk.contracts.LotteryPredictor)
wins = 0
for _ in range(20):
    world.advance()
    if world.balance(lottery) == 0:
        world.fund(lottery, 1_000)
    wins += bool(world.transact("eve", predictor, "attack", lottery, 1, value=1).result)
print("predictor wins", wins, "of 20")
assert wins == 20

# %%
# A commit-reveal lottery
# -----------------------

rng = random.Random(7)
players = ["alice", "bob", "carol", "dave"]
secrets = {p: (rng.randrange(2**64), rng.randrange(2**64)) for p in players}
world = bk.contracts.World()
for p in players:
    world.fund(p, 10)
game = world.deploy("house", bk.contracts.CommitRevealLottery, 10, 5, 5)
for p in players:
    world.transact(p, game, "commit", bk.contracts.commitment(p, *secrets[p]), value=10)
world.advance(6)
for p in players:
    assert world.transact(p, game, "reveal", *secrets[p]).success
world.advance(5)
winner = world.transact("anyone", game, "settle").result
seed = 0
for secret, _ in secrets.values():
    seed ^= secret
assert winner == players[seed % len(players)] and world.balance(winner) == 40
print("winner", winner)

# %%
# The last revealer's option
# --------------------------
# Dave reveals last, so he computes the draw with and without his secret.
# In this contract a player who withholds stays in the draw, and his stake
# is in the pot either way: withholding is free. Dave reveals only when that
# makes him win, and wins with probability 1/4 + 3/4 * 1/4 = 7/16.


def dave_wins(others, mine, strategic):
    revealed = others[0] ^ others[1] ^ others[2]
    if not strategic or (revealed ^ mine) % 4 == 3:
        return (revealed ^ mine) % 4 == 3
    return revealed % 4 == 3  # Withheld: the draw uses the other three secrets.


trials = 20_000
games = [([rng.randrange(2**64) for _ in range(3)], rng.randrange(2**64)) for _ in range(trials)]
honest = sum(dave_wins(o, m, False) for o, m in games) / trials
strategic = sum(dave_wins(o, m, True) for o, m in games) / trials
print(f"Dave wins {honest:.3f} revealing always, {strategic:.3f} revealing only to win")
assert abs(honest - 1 / 4) < 0.02 and abs(strategic - 7 / 16) < 0.02

# The contract agrees: when Dave withholds, the draw uses the three revealed secrets.
world = bk.contracts.World()
for p in players:
    world.fund(p, 10)
game = world.deploy("house", bk.contracts.CommitRevealLottery, 10, 5, 5)
for p in players:
    world.transact(p, game, "commit", bk.contracts.commitment(p, *secrets[p]), value=10)
world.advance(6)
for p in players[:-1]:
    world.transact(p, game, "reveal", *secrets[p])
world.advance(5)
revealed = secrets["alice"][0] ^ secrets["bob"][0] ^ secrets["carol"][0]
assert world.transact("anyone", game, "settle").result == players[revealed % 4]

fig, ax = plt.subplots(figsize=(7, 4))
labels = ["fair share", "last revealer\nwithholding", "eve, block-hash\nlottery"]
ax.bar(labels, [honest, strategic, wins / 20], color=["#16a34a", "#d97706", "#dc2626"])
ax.set(ylabel="win rate", ylim=(0, 1.05), title="Commit-reveal removes prediction, not all bias")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Change the rules so that a player who does not reveal is excluded from
# the draw and loses the stake to the others. What is Dave's best strategy
# now, and his win rate? A worked solution is in :doc:`/exercises/contracts`.
