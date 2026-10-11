r"""
Floyd and Hoare: proving a withdrawal correct with assertions (1967-1969)
=========================================================================

Floyd attached an assertion to every arrow of a flowchart and asked that
each instruction carry a true assertion to a true one. Hoare compressed the
idea into the triple :math:`\{P\}\,S\,\{Q\}`: if P holds before S runs and S
finishes, Q holds afterwards. The rule for an assignment runs backwards,

.. math::

   \{Q[e/x]\}\; x := e\; \{Q\},

so a postcondition can be pushed back through the code until it becomes a
condition on the inputs, the *weakest precondition*. Proving the triple
then means showing that P implies it.

The program below withdraws from a balance and credits the receiver. The
property to prove is conservation: the balance plus what was received never
changes. With unbounded integers the weakest precondition reduces to the
property itself, so it holds; with 4-bit words, a credit that wraps around
breaks a different property, and a check over every state finds the
counterexample.
"""

# %%
import itertools

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The weakest precondition of conservation
# ----------------------------------------

withdraw = """
require(amount <= balance)
balance = balance - amount
received = received + amount
"""
conservation = "balance + received == total"
wp = bk.contracts.weakest_precondition(withdraw, conservation)
print("wp =", bk.contracts.to_source(wp))

domain = {name: range(8) for name in ("balance", "amount", "received")}
domain["total"] = range(16)
result = bk.contracts.check_triple(conservation, withdraw, conservation, domain)
print(result)
assert result.holds and result.checked > 0

# P implies the weakest precondition in every state: the two checks agree.
for values in itertools.product(*domain.values()):
    env = dict(zip(domain, values, strict=True))
    if bk.contracts.evaluate(bk.contracts.parse_expression(conservation), env):
        assert bk.contracts.evaluate(wp, env)

# %%
# Wrapping words break "the receiver never loses"
# -----------------------------------------------
# The receiver should end with at least the amount. With 4-bit words a
# large credit wraps around to a small number.

gains = "received >= amount"
bits = 4
small = {name: range(2**bits) for name in ("balance", "amount", "received")}
unbounded = bk.contracts.check_triple("1", withdraw, gains, small)
wrapped = bk.contracts.check_triple("1", withdraw, gains, small, modulus=2**bits)
print("unbounded:", unbounded.holds, " 4-bit words:", wrapped.counterexample)
assert unbounded.holds and not wrapped.holds

grid = [[0] * 2**bits for _ in range(2**bits)]
for received, amount in itertools.product(range(2**bits), repeat=2):
    env = {"balance": 15, "amount": amount, "received": received}
    _, final = bk.contracts.run_program(withdraw, env, modulus=2**bits)
    grid[received][amount] = int(final["received"] < amount)

fig, ax = plt.subplots(figsize=(5.5, 4.5))
image = ax.imshow(grid, origin="lower", cmap="Reds")
ax.set(
    xlabel="amount",
    ylabel="received before",
    title="Where the postcondition fails (4-bit words)",
)
fig.colorbar(image, ax=ax, label="1 = receiver ends below the amount")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Compute ``weakest_precondition(withdraw, "balance >= 0")``. Which part of
# it does the ``require`` contribute, and what happens to the result if you
# delete the ``require`` line? A worked solution is in
# :doc:`/exercises/contracts`.
