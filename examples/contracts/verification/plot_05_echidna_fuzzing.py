r"""
Echidna: property-based fuzzing finds a self-transfer bug (2020)
================================================================

Echidna, from Trail of Bits, tests a contract the way QuickCheck tests a
function. The author writes *properties*, functions that must always return
true; the fuzzer sends random sequences of transactions, with random
senders and arguments, checks every property after each one, and *shrinks*
any failing sequence to a short counterexample.

The token below caches both balances before writing either. A transfer to
oneself therefore writes the sender's reduced balance, then overwrites it
with the old balance plus the amount: money from nothing. Total supply is
the property:

.. math::

   \sum_{a} \mathrm{balance}(a) = \mathrm{supply}.

Fuzzing finds the bug within a few transactions and shrinks the sequence
to a self-transfer, preceded at most by the payment that gave the sender
tokens. The rate at which random sequences hit it grows with their
length, which is why fuzzers run long campaigns.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts import Contract

# %%
# A token with a caching bug, and its property
# --------------------------------------------


class CachedToken(Contract):
    layout = ("supply", "balances")

    def constructor(self, supply):
        self.write("supply", supply)
        self.write("balances", self.sender, supply)

    def transfer(self, to, amount):
        source, target = self.read("balances", self.sender), self.read("balances", to)
        self.require(source >= amount, "insufficient balance")
        self.write("balances", self.sender, source - amount)
        self.write("balances", to, target + amount)

    def total(self):
        return sum(self.entries("balances").values())


def setup(world):
    return world.deploy("alice", CachedToken, 100)


def supply_conserved(world, token):
    return world.view(token, "total") == world.read(token, "supply")


accounts = ["alice", "bob", "carol"]
functions = {"transfer": [accounts, [0, 1, 10, 50, 200]]}
result = bk.contracts.fuzz(setup, functions, supply_conserved, senders=accounts, seed=2)
print(result)
assert result.failed and len(result.sequence) <= 2
last = result.sequence[-1]
assert last.sender == last.args[0] and last.args[1] > 0

# %%
# How often does a random sequence find it?
# -----------------------------------------

depths = [1, 2, 4, 8, 16]
rates = []
for depth in depths:
    found = sum(
        bk.contracts.fuzz(
            setup, functions, supply_conserved, senders=accounts, runs=1, depth=depth, seed=seed
        ).failed
        for seed in range(60)
    )
    rates.append(found / 60)
print(dict(zip(depths, rates, strict=True)))
assert rates[-1] > rates[0]

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(depths, rates, "o-", color="#2563eb")
ax.set(
    xscale="log",
    xticks=depths,
    xticklabels=depths,
    xlabel="transactions per random sequence",
    ylabel="fraction of sequences breaking the property",
    ylim=(0, 1),
    title="Longer sequences reach the bug more often",
)
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Fix ``transfer`` by reading the recipient's balance *after* writing the
# sender's. Does the fuzzer still find a counterexample? What does a clean
# run of 100 sequences prove, and what does it not?
