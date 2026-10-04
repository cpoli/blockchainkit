"""
Smart contracts: the vending machine (Szabo 1994)
=================================================

Nick Szabo coined *smart contract* for terms of an agreement enforced by a
mechanism rather than by courts, and gave the vending machine as the
primordial example: anyone who inserts enough money gets the item and the
change, and nobody can take the goods without paying. A blockchain contract
is such a machine whose code and state every node can check.

What to look for
----------------

Every outcome follows from the code: a sale moves exactly one item and the
price, underpaying or buying from an empty machine changes nothing, and the
machine's books always balance: revenue equals price times items sold.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Run a day of customers
# ----------------------
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

machine = bk.vm.vending_machine()
STOCK, PRICE, REVENUE = 0, 1, 2
storage = {STOCK: 10, PRICE: 3, REVENUE: 0}
rng = Random(4)
history = []
for _ in range(25):
    payment = rng.randint(0, 6)
    try:
        result = bk.vm.execute(machine, arguments=(payment,), storage=storage)
        storage = dict(result.storage)
        history.append(("sale", payment, result.stack[0]))
    except bk.vm.VMError:
        history.append(("refused", payment, payment))  # Nothing happened; money returned.
    sold = 10 - storage[STOCK]
    assert storage.get(REVENUE, 0) == sold * storage[PRICE]
sales = [h for h in history if h[0] == "sale"]
print(len(sales), "sales;", storage)
assert all(change == paid - 3 for _, paid, change in sales)
assert storage[STOCK] == 0 or all(h[1] < 3 for h in history if h[0] == "refused")

fig, ax = plt.subplots(figsize=(8, 3.5))
colors = {"sale": "#16a34a", "refused": "#dc2626"}
for i, (kind, paid, _) in enumerate(history):
    ax.bar(i, paid, color=colors[kind])
ax.axhline(3, color="black", linestyle="--", label="price")
ax.set(xlabel="customer", ylabel="payment", title="Green: sale, red: refused (nothing changes)")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Add an owner withdrawal: a second program that moves the revenue out and
# resets it to zero. What stops a customer from running it? (This machine
# has no notion of a caller; what would the contract need to know?)
