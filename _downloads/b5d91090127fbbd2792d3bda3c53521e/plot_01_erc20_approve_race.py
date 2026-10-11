r"""
ERC-20 tokens and the approve/transferFrom race (2015)
======================================================

Fabian Vogelsteller and Vitalik Buterin's ERC-20 gave fungible tokens one
interface: ``transfer``, ``balanceOf``, and a two-step delegation, where
``approve(spender, n)`` lets a spender move up to ``n`` tokens with
``transferFrom``. Any wallet or exchange can then handle any token.

``approve`` *overwrites* the allowance. Suppose Alice allowed Bob 100 and
now wants to lower it to 50. Bob sees her transaction waiting in the
mempool and gets a ``transferFrom`` of 100 mined first; her ``approve``
then grants a fresh 50, which he also spends. With the order chosen by the
spender, Alice loses

.. math::

   \text{old} + \text{new} \quad\text{instead of at most}\quad \max(\text{old}, \text{new}).

``decrease_allowance`` changes the allowance relative to what is left, so
if Bob has already spent it, Alice's reduction reverts instead of granting
more.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Alice lowers Bob's allowance from 100 to 50
# -------------------------------------------


def spent_by_bob(fix, bob_first):
    world = bk.contracts.World()
    token = world.deploy("alice", bk.contracts.ERC20, 1_000)
    world.transact("alice", token, "approve", "bob", 100)
    alice_tx = ("decrease_allowance", "bob", 50) if fix else ("approve", "bob", 50)
    if bob_first:
        world.transact("bob", token, "transfer_from", "alice", "bob", 100)
    world.transact("alice", token, *alice_tx)
    # Bob then spends whatever allowance is left.
    remaining = world.view(token, "allowance", "alice", "bob")
    if remaining:
        world.transact("bob", token, "transfer_from", "alice", "bob", remaining)
    return world.view(token, "balance_of", "bob")


outcomes = {
    (fix, bob_first): spent_by_bob(fix, bob_first)
    for fix in (False, True)
    for bob_first in (False, True)
}
print(outcomes)
assert outcomes[(False, False)] == 50 and outcomes[(False, True)] == 150
assert outcomes[(True, False)] == 50 and outcomes[(True, True)] == 100

fig, ax = plt.subplots(figsize=(7, 4))
labels = ["approve(50)", "decrease_allowance(50)"]
width = 0.35
for offset, bob_first, color in ((-width / 2, False, "#16a34a"), (width / 2, True, "#dc2626")):
    heights = [outcomes[(fix, bob_first)] for fix in (False, True)]
    ax.bar(
        [i + offset for i in range(2)],
        heights,
        width,
        color=color,
        label="Bob front-runs" if bob_first else "in Alice's order",
    )
ax.axhline(100, color="#64748b", linestyle=":", label="what Alice ever allowed at once")
ax.set_xticks(range(2), labels)
ax.set(ylabel="tokens Bob ends with", title="Overwriting an allowance invites a race")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Another mitigation is to require the allowance to be zero before it is
# set to a new nonzero value: Alice approves 0, then 50. Can Bob still take
# 150? Write the sequence of transactions and check it with ``World``. A
# worked solution is in :doc:`/exercises/contracts`.
