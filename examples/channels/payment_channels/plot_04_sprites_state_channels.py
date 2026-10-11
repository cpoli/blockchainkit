r"""
Sprites and general state channels (Miller et al., 2017)
========================================================

With contracts, a channel can be a judge rather than a set of transactions.
An adjudicator contract holds both deposits; the parties sign successive
versions of any state; and at the end one of them submits the latest. If
it submits an old version, the other has a dispute period to submit a
newer one, and the contract pays out the highest version it saw.

Sprites also shortened how long a multi-hop payment locks collateral. In
Lightning each hop's expiry exceeds the next one's by :math:`\Delta`, so
over :math:`n` hops the first hop's coins are locked for about
:math:`n\Delta`. In Sprites every hop asks one *preimage manager* contract
whether the preimage was published by a common deadline, so every hop
expires at the same time:

.. math::

   \sum_i a_i\, n_i\Delta \quad\text{(Lightning)} \qquad\text{vs.}\qquad
   \sum_i a_i\, \Delta \quad\text{(Sprites)}.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts import World
from blockchainkit.crypto import public_key, sha256

# %%
# A dispute settled by the adjudicator
# ------------------------------------

world = World()
world.fund("alice", 100)
keys = [public_key(7), public_key(5)]
channel = world.deploy(
    "alice", bk.channels.StateChannel, keys, ["alice", "bob"], [100, 0], 20, value=100
)


def signed(version, balances):
    return [bk.channels.sign_state(k, channel, version, balances) for k in (7, 5)]


states = {v: [100 - 10 * v, 10 * v] for v in range(8)}  # Alice pays Bob 10 per version.
stale = world.transact("alice", channel, "submit", 2, states[2], signed(2, states[2]))
assert stale.success  # Alice submits version 2, when version 7 exists.
world.advance(5)
assert world.transact("bob", channel, "submit", 7, states[7], signed(7, states[7])).success
world.advance(15)
assert world.transact("bob", channel, "settle").success
print("payouts:", world.balance("alice"), world.balance("bob"))
assert (world.balance("alice"), world.balance("bob")) == (30, 70)

# %%
# One preimage manager for every hop
# ----------------------------------

manager = world.deploy("deployer", bk.channels.PreimageManager)
deadline = world.block_number + 10
world.advance(3)
world.transact("carol", manager, "publish", b"invoice 42")  # The recipient publishes.
assert world.view(manager, "published_by", sha256(b"invoice 42"), deadline)

# %%
# Collateral locked as the path grows
# -----------------------------------

delta, amount = 40, 1_000
hops = range(1, 21)
lightning, sprites = [], []
for n in hops:
    amounts = [amount] * n
    staggered = bk.channels.htlc_expiries(n, delta=delta)
    shared = bk.channels.sprites_expiries(n, delta=delta)
    lightning.append(bk.channels.collateral_time(amounts, staggered))
    sprites.append(bk.channels.collateral_time(amounts, shared))
assert lightning[-1] / sprites[-1] == (20 + 1) / 2  # (n + 1) / 2 times as much.

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(hops, lightning, "o-", color="#dc2626", label="Lightning: staggered expiries")
ax.plot(hops, sprites, "s-", color="#16a34a", label="Sprites: one shared deadline")
ax.set(xlabel="hops in the route", ylabel="coins x blocks locked, worst case")
ax.set_title("Sprites lock collateral for a constant time per hop")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Bob must answer within the dispute period. Using
# :class:`~blockchainkit.channels.systems.state_channels.StateChannel`, find
# the last block at which his newer state is still accepted after Alice's
# stale submission, and explain what a longer period costs an honest party
# who wants to close.
