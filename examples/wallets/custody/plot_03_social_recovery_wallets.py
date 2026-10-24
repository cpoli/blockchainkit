r"""
Social-recovery wallets (2021)
==============================

Vitalik Buterin argued in January 2021 for wallets that need no seed-phrase
backup. A social-recovery wallet is a contract with one signing key for
daily use and n guardians, any m of whom can replace that key. Losing the
key no longer loses the coins, and a thief with the key alone can be
locked out. If each guardian is independently lost with probability
:math:`p_l` or corrupt with probability :math:`p_c`,

.. math::

   P(\text{theft}) = \sum_{j \ge m} \binom{n}{j} p_c^{\,j} (1 - p_c)^{n-j},

and a lockout needs fewer than m honest guardians: the threshold trades one
risk for the other. Changes to the guardians are delayed, so a thief cannot
replace them before they recover the wallet.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.wallets.visualizers import plot_recovery_risk

# %%
# Losing a key, and getting the wallet back
# -----------------------------------------

world = bk.contracts.World()
world.fund("alice", 100)
guardians = ["sister", "friend", "hardware", "lawyer", "colleague"]
wallet = world.deploy("alice", bk.wallets.SocialRecoveryWallet, "alice", guardians, 3)
world.transact("alice", wallet, value=100)

# A thief copies alice's key and tries to make itself the only guardian.
assert world.transact("alice", wallet, "propose_guardians", ["thief"], 1).success
print(world.transact("alice", wallet, "apply_guardians").error)

# Three guardians move the wallet to alice's new key first.
for g in ("sister", "friend", "hardware"):
    receipt = world.transact(g, wallet, "support_recovery", "alice-new-key")
print("recovered:", receipt.result, "owner:", world.view(wallet, "owner"))
world.advance(bk.wallets.GUARDIAN_DELAY)
print("thief applies:", world.transact("alice", wallet, "apply_guardians").error)
assert world.transact("alice-new-key", wallet, "execute", "bob", 30).success
assert world.balance("bob") == 30

# %%
# Choosing the threshold
# ----------------------

for m in range(1, 6):
    risk = bk.wallets.recovery_risk(5, m, lost=0.1, corrupt=0.05)
    print(f"{m} of 5: lockout {risk.lockout:.2e}, theft {risk.theft:.2e}")
best = bk.wallets.recovery_risk(5, 3, lost=0.1, corrupt=0.05)
assert best.lockout < 0.1 and best.theft < 0.05  # Better than one seed phrase on both counts.

ax = plot_recovery_risk(5, lost=0.1, corrupt=0.05)
ax.set_title("5 guardians against one seed phrase (lost 10%, stolen 5%)")
plt.show()

# %%
# Exercise
# --------
# Which threshold minimizes the sum of the lockout and theft probabilities
# for 5 guardians, each lost with probability 0.1 and corrupt with 0.05?
# A worked solution is in :doc:`/exercises/wallets`.
