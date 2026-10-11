r"""
eltoo: channel updates without penalties (Decker, Russell and Osuntokun, 2018)
==============================================================================

Lightning's penalty punishes mistakes as hard as theft: restore an old
backup, publish it, and lose the channel. eltoo replaces punishment with
replacement. Every state is an *update* transaction, which can spend the
funding output or any earlier update, and a *settlement*, which pays that
state's balances after a delay. An old update on chain is simply
overwritten by a newer one, and only the last update ever settles.

Updates can attach to any earlier update because they are signed with
``SIGHASH_NOINPUT``, which leaves the spent output out of the signature;
and only *later* updates can attach, because each update output demands a
lock time above its own state number:

.. math::

   \text{update } m \text{ spends update } n \iff m \ge n + 1.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Twelve updates, and a stale publication
# ---------------------------------------

channel = bk.channels.EltooChannel(("alice", "bob"), (7, 5), (100, 100), delay=144)
for state in range(12):
    channel.pay("alice" if state % 3 else "bob", 10)
print("latest balances:", channel.balances)

channel.publish(state=4, height=1_000)  # Alice publishes an old state...
try:
    channel.publish(state=2, height=1_001)  # ...and cannot go further back.
except ValueError as error:
    print("state 2 rejected:", error)
channel.publish(height=1_002)  # Bob overwrites it with the latest.
settlement = channel.settle(height=1_002 + 144)
assert dict(settlement.payouts) == channel.balances and settlement.state == 12

# %%
# The cost of publishing an old state, by mistake or on purpose
# -------------------------------------------------------------
# Compare Lightning, where a watching counterparty takes everything, with
# eltoo, where the stale state is replaced and costs nothing but fees.

lightning = bk.channels.LightningChannel(("alice", "bob"), (7, 5), (100, 100), delay=144)
for state in range(12):
    lightning.pay("alice" if state % 3 else "bob", 10)
honest = lightning.balances["alice"]
lightning.publish("alice", state=4, height=1_000)
lost = honest - lightning.penalize(height=1_001).payouts["alice"]
print(f"stale state 4: Alice loses {lost} in Lightning, 0 in eltoo")
assert lost == honest

fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(["Lightning", "eltoo"], [lost, 0], color=["#dc2626", "#16a34a"])
ax.set(ylabel="coins Alice loses", title="Publishing an old state: penalty or replacement")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# In eltoo each party keeps only the latest update and settlement. What must
# a Lightning party keep to be able to punish every revoked state, and how
# does the hash chain of per-commitment secrets keep that small?
