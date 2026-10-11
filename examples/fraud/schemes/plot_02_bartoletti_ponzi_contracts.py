r"""
Bartoletti et al.: dissecting Ponzi schemes on Ethereum (2017)
==============================================================

Bartoletti, Carta, Cimoli and Saia collected 184 Ponzi schemes running as
Ethereum contracts and sorted them by how they pay. The commonest is the
*chain*: each deposit is queued, owed a multiple of itself, and paid out of
later deposits in order of arrival, as in Doubler and Rubixi. Its source
is public, and the victims who read it see exactly that:

.. code-block:: solidity

   function enter() payable {
       participants.push(Participant(msg.sender, msg.value * 2));
       owner.transfer(msg.value / 10);
       while (this.balance >= participants[payoutIdx].payout) {
           participants[payoutIdx].etherAddress.transfer(participants[payoutIdx].payout);
           payoutIdx++;
       }
   }

Paying :math:`m` times every deposit needs the deposits to keep growing,
and once they stop, a fraction of about :math:`1 - 1/m` of the investors
is never paid. A public ledger makes the scheme measurable: the payouts
leave in the very transactions that bring in new deposits, and most
investors end below what they paid.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Thirty investors join a doubler
# -------------------------------

world = bk.contracts.World()
investors = [f"investor{k:02}" for k in range(30)]
for name in investors:
    world.fund(name, 1_000)
scheme = world.deploy("owner", bk.fraud.ChainPonzi, 200, 10, name="Doubler")
receipts = [world.transact(name, scheme, value=100) for name in investors]
assert all(r.success for r in receipts)
gains = [world.balance(name) - 1_000 for name in investors]
print("paid in full:", world.view(scheme, "paid"), "of", world.view(scheme, "investors"))
print("owner's take:", world.balance("owner"))
assert sum(g > 0 for g in gains) < len(investors) / 2

fig, ax = plt.subplots(figsize=(8, 4))
colors = ["#16a34a" if g > 0 else "#dc2626" for g in gains]
ax.bar(range(len(gains)), gains, color=colors)
ax.axhline(0, color="black", linewidth=0.8)
ax.set(xlabel="order of arrival", ylabel="gain")
ax.set_title("The early double their money; everyone after them pays for it")
fig.tight_layout()

# %%
# What the block explorer shows
# -----------------------------
# Every payout to an investor leaves in the same transaction as another
# investor's deposit, and most investors are in loss: the signature of a
# Ponzi scheme.

flows = bk.fraud.value_flows(receipts)
features = bk.fraud.ponzi_features(flows, scheme, owner="owner")
print(features)
assert features.looks_like_ponzi and features.paid_from_deposits == 1.0

plt.show()

# %%
# Exercise
# --------
# Change the multiplier to 150%. How many of the 30 investors are now paid,
# and what does the fraction :math:`1 - 1/m` predict? Why does the owner's
# fee make the actual number smaller?
