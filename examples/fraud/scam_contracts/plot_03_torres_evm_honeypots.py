r"""
Torres et al.: honeypot contracts that trap would-be thieves (2019)
===================================================================

A honeypot holds ether and seems to leak it to anyone who spots a flaw in
its source. The reader sends ether to exploit the flaw and loses it.
Torres, Steichen and State found 690 honeypots on Ethereum and sorted them
by technique. Three rest on EVM semantics or on what the block explorer
shows. *Balance disorder*: the reader sees that sending at least the
contract's balance pays out both,

.. code-block:: solidity

   function multiplicate(address adr) payable {
       if (msg.value >= this.balance) adr.transfer(this.balance + msg.value);
   }

but ``this.balance`` already includes ``msg.value``, so with any bait
:math:`b > 0` the condition :math:`v \ge b + v` never holds. *Hidden state
update*: anyone who pays 1 ether may set the password of a gift box, but its
creator closed the box through a contract call that carried no ether, which
the explorer of the time did not list. *Straw man contract*: a bank pays
before updating balances, an apparent reentrancy bug, and logs each
cash-out to a ``Log`` contract; the address given to the constructor holds
different code that reverts every cash-out but the creator's.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

world = bk.contracts.World()
world.fund("creator", 10_000)
losses = {}

# %%
# Balance disorder
# ----------------

pot = world.deploy("creator", bk.fraud.MultiplicatorX3, name="MultiplicatorX3")
world.transact("creator", pot, value=1_000)  # The bait.
world.fund("thief1", 1_500)
world.transact("thief1", pot, "multiplicate", "thief1", value=1_500)
losses["balance disorder"] = 1_500 - world.balance("thief1")
assert losses["balance disorder"] == 1_500

# %%
# Hidden state update
# -------------------
# The creator sets the password and closes the box through a relay; the
# explorer lists only the call that carried ether.

box = world.deploy("creator", bk.fraud.GiftBox, 1_000, name="Gift_1_ETH")
relay = world.deploy("creator", bk.fraud.Relay, name="relay")
digest = bk.crypto.sha256(b"creator's password")
receipts = [
    world.transact("creator", relay, "forward", box, "set_pass", digest, value=1_000),
    world.transact("creator", relay, "forward", box, "pass_has_been_set", digest),
]
listed = bk.fraud.explorer_view(receipts, box)
print("explorer lists:", [(r.function, r.value) for r in listed])
assert [r.function for r in listed] == ["set_pass"]
world.fund("thief2", 1_000)
world.transact("thief2", box, "set_pass", bk.crypto.sha256(b"mine"), value=1_000)
world.transact("thief2", box, "get_gift", b"mine")
losses["hidden state update"] = 1_000 - world.balance("thief2")
assert losses["hidden state update"] == 1_000

# %%
# Straw man contract
# ------------------

trap_log = world.deploy("creator", bk.fraud.TrapLog, name="Log")
bank = world.deploy("creator", bk.fraud.PrivateBank, trap_log, name="Private_Bank")
world.fund("thief3", 1_000)
world.transact("thief3", bank, "deposit", value=1_000)
cash_out = world.transact("thief3", bank, "cash_out", 1_000)
print("cash out:", cash_out.success, "| code at the log address:", world.code(trap_log).__name__)
losses["straw man contract"] = 1_000 - world.balance("thief3")
assert not cash_out.success and losses["straw man contract"] == 1_000

fig, ax = plt.subplots(figsize=(7, 3.5))
ax.barh(list(losses), list(losses.values()), color="#dc2626")
ax.set(xlabel="ether lost by the would-be thief", title="Three EVM-level honeypots")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Before sending ether to the bank, what could the would-be thief have read
# on chain to discover the straw man? Write the check with
# :meth:`~blockchainkit.contracts.systems.world.World.code`.
