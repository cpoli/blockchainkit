r"""
The Parity library freeze: selfdestruct behind DELEGATECALL (November 2017)
===========================================================================

After the July hack, Parity deployed a fixed library whose ``initWallet``
runs only on uninitialized storage. Every wallet initialized itself at
deployment, so no wallet could be taken over again. But the library was a
contract too, with storage of its own, and nobody had initialized it.

On 6 November 2017 a user called ``initWallet`` on the library itself,
became its sole owner, and called ``kill``, which ran ``selfdestruct``. The
library's code was gone. A ``DELEGATECALL`` to an address without code
does not fail: it runs nothing and returns success. Every wallet built on
the library kept its ether and lost every function that could move it;
about 513,774 ether were frozen for good.

The rule it teaches: code reached by ``DELEGATECALL`` is part of every
caller, so a library must be initialized, or better have no state and no
``selfdestruct`` at all.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts.visualizers import plot_call_tree

# %%
# Three wallets on the patched library
# ------------------------------------

ALICE, BOB, USER = 11, 13, 199  # Fixed teaching keys.
owners = [bk.crypto.public_key(ALICE), bk.crypto.public_key(BOB)]
world = bk.contracts.World()
library = world.deploy("parity", bk.contracts.PatchedWalletLibrary, name="library")
wallets = []
for index, amount in enumerate((300, 500, 700)):
    wallet = world.deploy("alice", bk.contracts.Wallet, library, owners, 2, name=f"wallet {index}")
    world.fund(wallet, amount)
    wallets.append(wallet)
before = [world.balance(w) for w in wallets]

reinit = world.transact("attacker", wallets[0], "init_wallet", [bk.crypto.public_key(USER)], 1)
assert reinit.error == "already initialized"  # The July bug is fixed.

# %%
# Initialize the library itself, then kill it
# -------------------------------------------

assert world.transact("devops199", library, "init_wallet", [bk.crypto.public_key(USER)], 1).success
kill = [bk.contracts.approve_action(USER, library, 0, "kill", "devops199")]
assert world.transact("devops199", library, "kill", "devops199", kill).success
assert world.code(library) is None

approvals = [
    bk.contracts.approve_action(k, wallets[0], 0, "execute", "alice", 300) for k in (ALICE, BOB)
]
attempt = world.transact("alice", wallets[0], "execute", "alice", 300, approvals)
print(
    "withdrawal 'succeeded':",
    attempt.success,
    "result:",
    attempt.result,
    "alice received:",
    world.balance("alice"),
)
assert attempt.success and world.balance("alice") == 0
assert [world.balance(w) for w in wallets] == before

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 3.5), gridspec_kw={"width_ratios": [1, 1.6]})
left.bar([world.name(w) for w in wallets], before, color="#64748b")
left.set(ylabel="ether", title="Balances, forever out of reach")
plot_call_tree(attempt, names=world.name, ax=right)
right.set_title("A signed withdrawal delegates to nothing")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Give ``PatchedWalletLibrary`` a constructor that initializes the library's
# own storage with no owners it could ever satisfy (for example a threshold
# no signer can meet). Repeat the attack. Which call now fails?
