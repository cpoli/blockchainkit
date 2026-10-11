r"""
CREATE2 and counterfactual addresses (2019)
===========================================

``CREATE`` derives a new contract's address from the deployer and its
nonce, so the address depends on everything the deployer did before.
EIP-1014, by Vitalik Buterin, activated in the Constantinople upgrade of
February 2019, added ``CREATE2``:

.. math::

   \mathrm{address} = H(\mathtt{0xff} \,\|\, \mathrm{deployer} \,\|\,
   \mathrm{salt} \,\|\, H(\mathrm{init\ code}))_{[12:]} .

The address depends only on who deploys, a chosen salt and the code, so it
is known before anything is deployed: it is *counterfactual*. A user can
receive funds at a smart-contract wallet that does not exist yet, and the
wallet is deployed only when it is first needed, by whoever pays for it.
State channels use the same trick for contracts that are deployed only in
a dispute.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Pay first, deploy later
# -----------------------

world = bk.contracts.World()
factory = world.deploy("dev", bk.contracts.Factory, name="factory")
address = world.view(factory, "predict", 7, "alice")
world.fund("bob", 100)
world.transact("bob", address, value=60)
print("before deployment: code", world.code(address), "balance", world.balance(address))
assert world.code(address) is None and world.balance(address) == 60

deployed = world.transact("relayer", factory, "deploy", 7, "alice").result
assert (
    deployed == address == bk.contracts.create2_address(factory, 7, bk.contracts.Forwarder, "alice")
)
assert world.transact("anyone", address, "sweep").result == 60 and world.balance("alice") == 60
assert "already in use" in world.transact("relayer", factory, "deploy", 7, "alice").error

# %%
# What the address depends on
# ---------------------------

creates = [bk.contracts.create_address(factory, nonce) for nonce in range(3)]
salts = [world.view(factory, "predict", salt, "alice") for salt in range(3)]
owners = [world.view(factory, "predict", 7, owner) for owner in ("alice", "bob", "carol")]
assert len(set(creates)) == len(set(salts)) == len(set(owners)) == 3
assert world.view(factory, "predict", 7, "alice") == address  # Reproducible.

fig, ax = plt.subplots(figsize=(8, 3.5))
rows = [
    ("CREATE, nonce 0..2", creates),
    ("CREATE2, salt 0..2", salts),
    ("CREATE2, owner varies", owners),
]
for row, (_, addresses) in enumerate(rows):
    for column, value in enumerate(addresses):
        ax.text(
            column,
            -row,
            value[:12] + "...",
            ha="center",
            va="center",
            family="monospace",
            bbox={"facecolor": "#e0e7ff" if value != address else "#bbf7d0", "pad": 4},
        )
ax.set_yticks([-r for r in range(len(rows))], [label for label, _ in rows])
ax.set(
    xlim=(-0.6, 2.6),
    ylim=(-2.6, 0.6),
    xticks=[],
    title="Every input of the formula moves the address",
)
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The deployed wallet sends everything to its owner. Bob funded Alice's
# address before it existed, trusting that only a Forwarder for Alice can
# ever be deployed there. Which inputs of ``create2_address`` guarantee
# that, and why must the constructor's argument be part of the code hash?
