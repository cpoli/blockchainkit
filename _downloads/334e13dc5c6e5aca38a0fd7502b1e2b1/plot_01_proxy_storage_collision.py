r"""
Upgradeable proxies and storage collisions (2018)
=================================================

Deployed code cannot change, so upgradeable contracts split in two. A
*proxy* keeps the address, the ether and the storage, and forwards every
call with ``DELEGATECALL`` to an *implementation* that holds the code.
Upgrading points the proxy at new code, and the state stays.

Both contracts now read one storage through two layouts. Field :math:`i`
of a layout lives in slot :math:`i`, so if the proxy keeps its
implementation address in slot 0 and the implementation keeps its owner
there, setting the owner overwrites the implementation pointer. EIP-1967
moves the proxy's own fields to slots chosen by a hash,

.. math::

   \mathrm{slot} = H(\texttt{"eip1967.proxy.implementation"}) - 1,

far from any compiled layout. Upgrades must keep the old fields in order
and only append: a version that reorders them silently reinterprets the
stored values.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts.systems.proxies import ADMIN_SLOT, IMPLEMENTATION_SLOT
from blockchainkit.contracts.visualizers import plot_storage

# %%
# A naive proxy: the owner lands on the implementation pointer
# ------------------------------------------------------------

world = bk.contracts.World()
box = world.deploy("dev", bk.contracts.BoxV1, name="BoxV1")
naive = world.deploy("dev", bk.contracts.NaiveProxy, box, name="naive proxy")
print("owner before initialize:", world.name(world.view(naive, "owner")))
world.transact("alice", naive, "initialize")
stored = world.transact("alice", naive, "store", 42)
print("store succeeded:", stored.success, "-> retrieve:", world.view(naive, "retrieve"))
assert world.read(naive, "implementation") == "alice"  # Overwritten by the owner.
assert stored.success and world.view(naive, "retrieve") is None  # Calls now reach nothing.
naive_storage = world.storage(naive)

# %%
# An EIP-1967 proxy, a compatible upgrade, and a reordered one
# ------------------------------------------------------------

proxy = world.deploy("dev", bk.contracts.EIP1967Proxy, box, name="EIP-1967 proxy")
world.transact("alice", proxy, "initialize")
world.transact("alice", proxy, "store", 42)
world.transact("dev", proxy, "upgrade_to", world.deploy("dev", bk.contracts.BoxV2))
assert (world.view(proxy, "retrieve"), world.view(proxy, "owner")) == (42, "alice")
world.transact("dev", proxy, "upgrade_to", world.deploy("dev", bk.contracts.BoxV2Reordered))
swapped = (world.view(proxy, "retrieve"), world.view(proxy, "owner"))
print("after a reordered upgrade: value", swapped[0], "owner", swapped[1])
assert swapped == ("alice", 42)

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 3))
plot_storage(
    naive_storage,
    fields={0: "implementation | owner", 1: "admin | value", 2: "initialized"},
    title="Naive proxy: collisions",
    ax=left,
)
plot_storage(
    world.storage(proxy),
    fields={
        IMPLEMENTATION_SLOT: "implementation (EIP-1967)",
        ADMIN_SLOT: "admin (EIP-1967)",
        0: "owner",
        1: "value",
        2: "initialized",
        3: "changes",
    },
    title="EIP-1967 proxy: separate slots",
    ax=right,
)
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# In the naive proxy, slot 1 is both the proxy's ``admin`` and the
# implementation's second field. Write an implementation whose layout is
# ``("unused", "value")`` and whose ``store(value)`` anyone may call. What can
# Mallory do with it, and why is that worse than a lost implementation
# pointer? A worked solution is in :doc:`/exercises/contracts`.
