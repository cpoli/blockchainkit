r"""
Verified source code, and why a verified source can still deceive (2016)
========================================================================

Block explorers let a contract's author publish its source and *verify*
it: the explorer compiles the source and checks that the bytecode matches
the code at the address. Solidity's metadata hash, added in December 2016,
made the match exact, and a green "verified" badge came to read as "safe".
It certifies only which code sits at one address. A buyer who checks the
verified source of an upgradeable token reads a proxy:

.. code-block:: solidity

   contract Proxy {
       // keccak256("eip1967.proxy.implementation") - 1
       bytes32 constant IMPLEMENTATION_SLOT = 0x3608...bbc;

       fallback() external payable {
           address impl = StorageSlot.getAddressSlot(IMPLEMENTATION_SLOT).value;
           (bool ok, ) = impl.delegatecall(msg.data);
           require(ok);
       }
   }

The behavior lives at whatever address the slot holds, and the admin can
change it at any time. The code that runs is

.. math::

   \text{code}(\text{proxy}) \circ \text{code}\big(\text{storage}_{\text{proxy}}[\text{slot}]\big),

and only the first factor is verified.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A verified proxy in front of a plain token
# ------------------------------------------

world = bk.contracts.World()
v1 = world.deploy("dev", bk.fraud.UpgradeableToken, name="token v1")
token = world.deploy("dev", bk.contracts.EIP1967Proxy, v1, name="token")
world.transact("dev", token, "initialize", 1_000_000)
world.transact("dev", token, "transfer", "buyer", 250_000)  # The buyer pays off-chain.
print("verified:", bk.fraud.verify_source(world, token, bk.contracts.EIP1967Proxy))
print("runs:", bk.fraud.effective_code(world, token).__name__)
assert world.transact("dev", token, "seize", "buyer", 1).error is not None  # No such function.

# %%
# The same badge, different code
# ------------------------------

v2 = world.deploy("dev", bk.fraud.SeizableToken, name="token v2")
world.transact("dev", token, "upgrade_to", v2)
assert bk.fraud.verify_source(world, token, bk.contracts.EIP1967Proxy)  # Still verified.
print("now runs:", bk.fraud.effective_code(world, token).__name__)
seized = world.transact("dev", token, "seize", "buyer", 250_000)
print("seize:", seized.success, "buyer holds", world.view(token, "balance_of", "buyer"))
assert seized.success and world.view(token, "balance_of", "buyer") == 0

fig, ax = plt.subplots(figsize=(7, 3))
ax.barh(["before the upgrade", "after the upgrade"], [250_000, 0], color=["#16a34a", "#dc2626"])
ax.set(xlabel="buyer's tokens", title="The verified address never changed")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# List three other ways in which a contract with a verified source can run
# code its reader never saw. Which of them can a reader detect from the
# verified source alone?
