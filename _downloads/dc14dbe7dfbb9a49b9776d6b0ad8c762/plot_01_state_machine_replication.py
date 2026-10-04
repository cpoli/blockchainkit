"""
State-machine replication: same inputs, same order, same state (Lamport 1978, Schneider 1990)
=============================================================================================

If every replica starts in the same state and applies the same commands in
the same order, deterministic execution keeps them identical. Lamport
introduced the idea; Schneider's tutorial made it the standard recipe for
fault tolerance. A blockchain is exactly this: consensus agrees on the
order of transactions, and every node executes them.

What to look for
----------------

Replicas that apply the same log agree. Applying the same commands in a
different order generally gives a different state, because the commands do
not commute. And one nondeterministic input, here each replica reading its
own clock, makes replicas diverge even with the same log.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Three commands on one counter
# -----------------------------
import itertools

import matplotlib.pyplot as plt

import blockchainkit as bk

commands = {
    "add 5": bk.vm.assemble("LOAD 0\nPUSH 5\nADD\nSTORE 0"),
    "double": bk.vm.assemble("LOAD 0\nPUSH 2\nMUL\nSTORE 0"),
    "minus 3": bk.vm.assemble("LOAD 0\nPUSH 3\nSUB\nSTORE 0"),
}


def replay(log, storage=None):
    state = dict(storage or {0: 1})
    for name in log:
        state = dict(bk.vm.execute(commands[name], storage=state).storage)
    return state[0]


log = ["add 5", "double", "minus 3"]
replicas = [replay(log) for _ in range(3)]
print("same log:", replicas)
assert len(set(replicas)) == 1

orders = {" > ".join(order): replay(order) for order in itertools.permutations(log)}
print(orders)
assert len(set(orders.values())) > 1

# %%
# Nondeterminism breaks replication
# ---------------------------------
# A command that stores "the current time" as each replica sees it.
clocks = [1000, 1002, 999]
stamped = [
    bk.vm.execute(bk.vm.assemble("STORE 1"), arguments=(clock,), storage={0: 1}).storage[1]
    for clock in clocks
]
print("timestamps:", stamped)
assert len(set(stamped)) == 3

fig, ax = plt.subplots(figsize=(7, 3.5))
ax.barh(list(orders), list(orders.values()), color="#7c3aed")
ax.set(xlabel="final counter", title="Same commands, different orders")
fig.tight_layout()

# %%
# Exercise
# --------
# Blockchains put the time into the block header, chosen once by the
# proposer and agreed by consensus. Rewrite the timestamp command so all
# replicas take the time from the log instead of their clocks.
