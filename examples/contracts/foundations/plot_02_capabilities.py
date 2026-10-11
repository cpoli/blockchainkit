r"""
Miller's capabilities: purses, and the tx.origin confused deputy (1997-2006)
============================================================================

In an object-capability system, the only way to act on something is to
hold a reference to it. Mark Miller's E language built distributed money
on this rule: to pay, hand over a purse holding exactly the payment; the
recipient can take that and nothing else. There is no ambient authority,
no global "who is calling" to consult.

Ambient authority causes the *confused deputy* (Hardy, 1988): a program
holding authority for one party is tricked into using it for another.
Ethereum's ``tx.origin``, the account that signed the transaction, is
ambient: a wallet that checks it pays out whenever its owner's transaction
passes through, even when the owner was lured into calling an attacker's
contract. Checking ``msg.sender``, the immediate caller, closes the hole.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts.visualizers import plot_call_tree

# %%
# Paying with a purse
# -------------------

mint = bk.contracts.Mint("carol-bucks")
alice, bob = mint.make_purse(100), mint.make_purse(0)
payment = alice.sprout()
payment.deposit(25, alice)  # Alice moves 25 into a purse she will hand over.
bob.deposit(25, payment)  # Bob holds only the payment purse...
try:
    bob.deposit(1, payment)
except ValueError as error:
    print("Bob cannot take more:", error)  # ...so he cannot reach Alice's 75.
assert (alice.balance, bob.balance) == (75, 25)

# %%
# The confused deputy
# -------------------

theft = {}
for wallet_code in (bk.contracts.OriginWallet, bk.contracts.SenderWallet):
    world = bk.contracts.World()
    world.fund("alice", 100)
    wallet = world.deploy("alice", wallet_code, name="alice's wallet")
    world.transact("alice", wallet, value=100)
    phisher = world.deploy("mallory", bk.contracts.AirdropPhisher, name="airdrop")
    receipt = world.transact("alice", phisher, "claim_airdrop", wallet)
    theft[wallet_code.__name__] = (world, receipt, world.balance("mallory"))
    print(f"{wallet_code.__name__}: Mallory gets {world.balance('mallory')}")
assert theft["OriginWallet"][2] == 100 and theft["SenderWallet"][2] == 0

fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 4.5))
for ax, name in ((top, "OriginWallet"), (bottom, "SenderWallet")):
    world, receipt, _ = theft[name]
    plot_call_tree(receipt, names=world.name, ax=ax)
    ax.set_title(f"{name}: {ax.get_title()}")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# ``SenderWallet`` still authorizes by identity. Write a wallet contract that
# instead pays whoever presents a secret it was given at deployment. Which of
# the two designs is closer to a capability, and what new risk does it bring?
