r"""
FTX, commingled customer funds, and proof of liabilities (2022)
===============================================================

In November 2022 FTX, then one of the largest exchanges, could not meet a
rush of withdrawals and filed for bankruptcy. Its affiliated trading firm,
Alameda Research, had been allowed a negative balance on the exchange and
had spent billions of dollars of customer deposits. The books still showed
every customer's balance; the coins were gone. With reserves :math:`R` and
liabilities :math:`L`, a run pays the first customers in full and the rest
nothing once

.. math::

   \rho = \frac{R}{L} < 1, \qquad
   \text{paid in a run} = \min(R, L) = \rho L .

A proof of reserves alone could not have shown this, since reserves were
real and large; only reserves set against a proof of the liabilities can.
Exchanges began publishing Merkle-sum-tree proofs of liabilities weeks
after the collapse.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# An exchange lends deposits to its affiliate
# -------------------------------------------

world = bk.contracts.World()
customers = [f"customer{k:02}" for k in range(20)]
for name in customers:
    world.fund(name, 1_000)
exchange = world.deploy("operator", bk.fraud.Custodian, "affiliate", 15_000, name="exchange")
for name in customers:
    world.transact(name, exchange, "deposit", value=1_000)
print("before:", world.view(exchange, "reserves"), "held for", world.view(exchange, "liabilities"))
world.transact("operator", exchange, "lend_to_affiliate", 12_000)
reserves, liabilities = world.view(exchange, "reserves"), world.view(exchange, "liabilities")
print(f"after: reserves {reserves:,}, owed {liabilities:,}")

# %%
# Reserves against a proof of liabilities
# ---------------------------------------

tree = bk.fraud.liability_tree(world.view(exchange, "balances"), salt=b"2022-11")
ratio = bk.fraud.reserve_ratio(reserves, tree.total)
print(f"proof of liabilities: total {tree.total:,}, reserve ratio {ratio:.0%}")
assert tree.total == liabilities and ratio == 0.4

# %%
# The run
# -------

results = [world.transact(name, exchange, "withdraw", 1_000) for name in customers]
paid = [r.success for r in results]
print("withdrawals paid:", sum(paid), "of", len(paid), "->", results[-1].error)
assert sum(paid) == ratio * len(customers)

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(
    range(len(paid)),
    [1_000 if ok else 0 for ok in paid],
    color=["#16a34a" if ok else "#dc2626" for ok in paid],
)
ax.set(xlabel="order in the queue", ylabel="ether recovered")
ax.set_title(f"A run on an exchange with a reserve ratio of {ratio:.0%}")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The affiliate returns its loan the day before a published proof of
# reserves, then borrows it again. Which checks pass, and what would a proof
# of reserves need to rule this out?
# A worked solution is in :doc:`/exercises/fraud`.
