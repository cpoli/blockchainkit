r"""
Poon and Dryja's Lightning Network: revocation and penalties (2016)
===================================================================

Lightning ranks a channel's states by punishment rather than by time locks,
so a channel can be updated any number of times. Each party holds its own
commitment transaction, signed by the other. It pays the counterparty at
once, but its holder only after a delay, during which anyone with the
*revocation key* can take the holder's output instead. Moving to a new
state, each party reveals the secret behind its old commitment's
revocation key. Publishing a revoked commitment then forfeits the whole
channel to a counterparty that is watching.

The revocation key adds the holder's per-commitment point to the
counterparty's base point, so it is usable only once both secrets are known:

.. math::

   R_n = S_n + B, \qquad r_n = s_n + b \pmod q.

The secrets are a hash chain used backwards, so the counterparty stores
only the latest one and hashes it to recover every older one.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Twenty payments back and forth
# ------------------------------


def busy_channel(seed):
    rng = Random(seed)
    channel = bk.channels.LightningChannel(("alice", "bob"), (7, 5), (100, 100), delay=144)
    history = [dict(channel.balances)]
    for _ in range(20):
        sender = rng.choice(channel.parties)
        channel.pay(sender, rng.randint(1, min(30, channel.balances[sender])))
        history.append(dict(channel.balances))
    return channel, history


channel, history = busy_channel(5)
best_old = max(range(20), key=lambda s: history[s]["alice"])
print(f"Alice's best revoked state: {best_old}, with {history[best_old]['alice']} coins")

# %%
# Alice publishes it: the penalty when Bob is watching
# ----------------------------------------------------

channel.publish("alice", state=best_old, height=1_000)
penalty = channel.penalize(height=1_010)
print("penalty:", dict(penalty.payouts))
assert penalty.payouts["alice"] == 0 and penalty.payouts["bob"] == 200

# Bob stored one secret, and hashes it to rebuild the secret of any revoked state.
assert all(channel.derive_secret("alice", s) is not None for s in range(20))
assert channel.derive_secret("alice", 20) is None  # The current state is not revoked.

# %%
# If Bob sleeps through the delay, the theft succeeds
# ---------------------------------------------------

alice_if_watched, alice_if_asleep = [], []
for state in range(21):
    alice_if_watched.append(0 if state < 20 else history[20]["alice"])
    alice_if_asleep.append(history[state]["alice"])
channel, _ = busy_channel(5)  # The same channel, rebuilt.
channel.publish("alice", state=best_old, height=1_000)
try:
    channel.sweep(height=1_100)
except ValueError as error:
    print("too early for Alice:", error)
theft = channel.sweep(height=1_144)
assert theft.payouts["alice"] == history[best_old]["alice"]

fig, ax = plt.subplots(figsize=(8, 4))
states = range(21)
ax.plot(states, alice_if_asleep, "o-", color="#dc2626", label="Bob offline for the delay")
ax.plot(states, alice_if_watched, "s-", color="#16a34a", label="Bob watching: penalty")
ax.axhline(history[20]["alice"], color="#64748b", linestyle="--", label="honest close")
ax.set(xlabel="state Alice publishes", ylabel="coins Alice ends with")
ax.set_title("Publishing a revoked state pays only if nobody is watching")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The penalty must be published within ``delay`` blocks of the revoked
# commitment. Using :meth:`~blockchainkit.channels.systems.lightning.LightningChannel.sweep`
# and :meth:`~blockchainkit.channels.systems.lightning.LightningChannel.penalize`,
# find the last height at which Bob can still punish Alice, and explain
# why a shorter delay is riskier for Bob.
# A worked solution is in :doc:`/exercises/channels`.
