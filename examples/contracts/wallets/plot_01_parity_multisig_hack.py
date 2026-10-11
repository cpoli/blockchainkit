r"""
The Parity multisig hack: an unprotected initializer (July 2017)
================================================================

Parity's multisig wallet kept its logic in a shared library. Each wallet
was a small stub holding the ether and the storage, which forwarded every
unknown call to the library with ``DELEGATECALL``: the library's code ran
on the wallet's storage, as the wallet.

The library's ``initWallet``, which writes the list of owners and how many
must approve, had no guard against a second call, and the stub forwarded
it like any other function. On 19 July 2017 an attacker called it on three
wallets, became the sole owner of each, and withdrew 153,037 ether. A
wallet's security reduced to

.. math::

   \text{owners} := \text{whoever called } \texttt{initWallet} \text{ last}.

Here each wallet is 2-of-2: a payment needs Schnorr signatures from both
owners over the wallet, its nonce and the payment. The attacker needs none
of them: re-initializing makes its own key the only owner, with a
threshold of one.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts.visualizers import plot_call_tree

# %%
# A 2-of-2 wallet behind a shared library
# ---------------------------------------

ALICE, BOB, ATTACKER = 11, 13, 99  # Fixed teaching keys.
owners = [bk.crypto.public_key(ALICE), bk.crypto.public_key(BOB)]

world = bk.contracts.World()
library = world.deploy("parity", bk.contracts.WalletLibrary, name="library")
wallet = world.deploy("alice", bk.contracts.Wallet, library, owners, 2, name="wallet")
world.fund("alice", 1_000)
world.transact("alice", wallet, value=1_000)

one = [bk.contracts.approve_action(ALICE, wallet, 0, "execute", "carol", 10)]
assert world.transact("alice", wallet, "execute", "carol", 10, one).error  # Two needed.
both = [bk.contracts.approve_action(k, wallet, 0, "execute", "carol", 10) for k in (ALICE, BOB)]
assert world.transact("alice", wallet, "execute", "carol", 10, both).success

# %%
# The attack: two transactions
# ----------------------------

takeover = world.transact("attacker", wallet, "init_wallet", [bk.crypto.public_key(ATTACKER)], 1)
nonce = world.view(wallet, "nonce")
balance = world.balance(wallet)
approval = [bk.contracts.approve_action(ATTACKER, wallet, nonce, "execute", "attacker", balance)]
drain = world.transact("attacker", wallet, "execute", "attacker", balance, approval)
print("takeover", takeover.success, "drain", drain.success, "stolen", world.balance("attacker"))
assert takeover.success and drain.success and world.balance("attacker") == 990
assert world.balance(wallet) == 0

fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 3.6))
plot_call_tree(takeover, names=world.name, ax=top)
top.set_title("1. init_wallet, forwarded to the library: " + top.get_title())
plot_call_tree(drain, names=world.name, ax=bottom)
bottom.set_title("2. execute, signed by the new 'owner': " + bottom.get_title())
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Deploy the wallet on ``PatchedWalletLibrary`` instead and repeat the
# attack. Which call fails, and with what error? Is every wallet now safe?
# (The next example answers the second question.)
