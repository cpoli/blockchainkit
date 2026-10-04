"""
The DAO and reentrancy: checks, effects, interactions (2016)
============================================================

The DAO was an Ethereum fund holding about 14% of all ether. Its withdrawal
code sent ether *before* updating the caller's balance. Sending ether to a
contract runs the contract's code, so in June 2016 an attacker's contract
called back into the withdrawal from inside the payment, again and again,
while its balance still showed the original deposit. About 3.6 million
ether were drained, and Ethereum hard-forked to return them.

What to look for
----------------

With the vulnerable order, the attacker withdraws its deposit once per
nested call, until the bank is empty or the call-depth limit stops it. With
the *checks-effects-interactions* order, the re-entrant call finds a zero
balance and the attacker gets back exactly its deposit.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Drain a bank holding 10,000 of other people's funds
# ---------------------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

deposits = [10, 50, 100, 500, 1000]
vulnerable = [bk.vm.drain_bank(10_000, d) for d in deposits]
safe = [bk.vm.drain_bank(10_000, d, checks_effects_interactions=True) for d in deposits]
for d, v, s in zip(deposits, vulnerable, safe, strict=True):
    print(f"deposit {d:5d}: vulnerable steals {v.stolen} in {v.calls} calls, safe {s.stolen}")
assert all(s.stolen == 0 for s in safe)
assert all(
    v.withdrawn == ((10_000 + d) // d) * d for d, v in zip(deposits, vulnerable, strict=True)
)

# %%
# The depth limit
# ---------------
# Ethereum then limited calls to a depth of 1024; tiny deposits run into it.
deep = bk.vm.drain_bank(10**9, 10)
print(deep)
assert deep.calls == 1024 and deep.withdrawn == 10_240

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
left.bar(
    ["pay, then update", "update, then pay"],
    [vulnerable[2].stolen, safe[2].stolen],
    color=["#dc2626", "#16a34a"],
)
left.set(ylabel="stolen", title="Deposit 100, bank 10,000")
right.loglog(deposits, [v.calls for v in vulnerable], "o-", color="#dc2626")
right.set(
    xlabel="attacker deposit",
    ylabel="nested withdraw calls",
    title="Smaller deposit, deeper recursion",
)
fig.tight_layout()

# %%
# Exercise
# --------
# A reentrancy *guard* sets a lock flag on entry and refuses to run while it
# is set. Add a ``guarded`` option to a copy of ``drain_bank``'s loop. Why
# do auditors still recommend checks-effects-interactions as well?
