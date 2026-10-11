r"""
Meyer's design by contract: an escrow with checked clauses (1986)
=================================================================

Bertrand Meyer's Eiffel treats every routine as a contract. The caller must
establish the *precondition*; the routine then guarantees the
*postcondition*; and every public routine preserves the class
*invariant*. Checked at run time, a violated clause names the culprit: a
failed precondition is the caller's bug, a failed postcondition or
invariant the supplier's. In Hoare's notation, a routine ``r`` must satisfy

.. math::

   \{\mathrm{pre}_r \wedge \mathrm{INV}\}\; r\; \{\mathrm{post}_r \wedge \mathrm{INV}\}.

Solidity's ``require`` and ``assert`` are the same idea, and a violated
clause reverts the transaction. The escrow below holds deposits for
several accounts; its invariant ties the recorded deposits to the ether
it actually holds. A refund with a rounding bug is stopped by its
postcondition, and a sweep that forgets to update the books is stopped by
the invariant, each before any state changes.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts import Contract, ensures, requires

# %%
# An escrow with a precondition, a postcondition and an invariant
# ---------------------------------------------------------------


class Escrow(Contract):
    layout = ("deposits", "total", "fee")

    def receive(self):
        self.write("deposits", self.sender, self.read("deposits", self.sender) + self.value)
        self.write("total", self.read("total") + self.value)

    @requires(
        lambda self, amount: 0 < amount <= self.read("deposits", self.sender),
        "refund must be within your deposit",
    )
    @ensures(
        lambda self, old, result, amount: (
            self.read("deposits", self.sender) == old("deposits", self.sender) - amount
        ),
        "deposit not reduced by the refund",
    )
    def refund(self, amount):
        fee = amount // 100  # A bug: the fee is charged to the depositor's record twice.
        self.write("deposits", self.sender, self.read("deposits", self.sender) - amount - fee)
        self.write("total", self.read("total") - amount)
        self.call(self.sender, None, value=amount)

    def sweep(self, to):
        self.call(to, None, value=self.ether_balance())  # Forgets to update the books.

    def invariant(self):
        return self.read("total") == self.ether_balance() == sum(self.entries("deposits").values())


world = bk.contracts.World()
for account in ("alice", "bob"):
    world.fund(account, 1_000)
escrow = world.deploy("operator", Escrow)
world.transact("alice", escrow, value=500)
world.transact("bob", escrow, value=300)

attempts = {
    "refund 50": world.transact("alice", escrow, "refund", 50),
    "refund 600": world.transact("alice", escrow, "refund", 600),
    "refund 200": world.transact("alice", escrow, "refund", 200),
    "sweep": world.transact("mallory", escrow, "sweep", "mallory"),
}
for name, receipt in attempts.items():
    print(f"{name:10s} ->", "ok" if receipt.success else receipt.error)
assert attempts["refund 50"].success
assert attempts["refund 600"].error == "refund must be within your deposit"
assert attempts["refund 200"].error == "deposit not reduced by the refund"
assert attempts["sweep"].error == "invariant of Escrow violated"
assert world.balance(escrow) == 750 and world.balance("mallory") == 0

fig, ax = plt.subplots(figsize=(7, 3.5))
names = list(attempts)
ax.barh(
    names,
    [1] * len(names),
    color=["#16a34a" if r.success else "#dc2626" for r in attempts.values()],
)
for row, receipt in enumerate(attempts.values()):
    ax.text(
        0.02,
        row,
        "succeeded" if receipt.success else receipt.error,
        va="center",
        color="white",
        fontsize=9,
    )
ax.set(xticks=[], title="Each clause stops a different fault")
ax.invert_yaxis()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A refund of 50 passed although the code is buggy. For which amounts does
# the postcondition catch the fee bug, and why does that make run-time
# checking weaker than proof?
