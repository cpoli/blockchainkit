r"""
King's symbolic execution: every path of a fee schedule (1976)
==============================================================

James King proposed running a program on symbols instead of numbers. Every
variable holds an expression over the inputs, and each branch on such an
expression forks the run in two. Each path then carries a *path condition*,
the conjunction of the decisions it took:

.. math::

   \mathrm{pc} = c_1 \wedge \neg c_2 \wedge \dots

Any input satisfying the path condition drives a concrete run down exactly
that path, so solving the condition of a path that fails an assertion
produces a bug-triggering input, without guessing.

The program charges a fee that depends on the amount. Its check only
requires ``amount <= balance``, forgetting the fee. Symbolic execution
finds five paths, and solving the two that fail the assertion yields inputs
that leave a negative balance.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts.visualizers import plot_symbolic_paths

# %%
# Explore every path
# ------------------

program = """
require(amount <= balance)
if amount > 100:
    fee = 2
else:
    fee = 1
balance = balance - amount - fee
assert balance >= 0
"""
result = bk.contracts.symbolic_execute(program)
print(result.outcomes)
for path in result.paths:
    condition = " and ".join(bk.contracts.to_source(c) for c in path.conditions)
    print(f"{path.outcome:9s} if {condition}")
assert result.outcomes == {"reverted": 1, "assertion": 2, "ok": 2}

# %%
# Solve the failing paths
# -----------------------
# The solver tries boundary values: 0, 1, 2, and every constant in the
# condition with its neighbors.

for path in result.paths:
    if path.outcome == "assertion":
        witness = bk.contracts.solve(path.conditions)
        outcome, final = bk.contracts.run_program(program, witness)
        print(witness, "->", outcome, "balance", final["balance"])
        assert outcome == "assertion" and final["balance"] < 0

fixed = program.replace("amount <= balance", "amount + 2 <= balance")
fixed_paths = bk.contracts.symbolic_execute(fixed).paths
assert all(
    bk.contracts.solve(path.conditions) is None
    for path in fixed_paths
    if path.outcome == "assertion"
)

fig, ax = plt.subplots(figsize=(7, 4))
plot_symbolic_paths(result, ax=ax)
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Add a third fee tier (``amount > 1000`` pays 5). How many paths does
# symbolic execution find now, and how many does a program with ``n``
# independent ``if`` statements have in the worst case?
