"""
Atomic transactions: all or nothing (Gray 1981)
===============================================

Jim Gray defined the *transaction*: a group of actions that is atomic
(either all happen or none), consistent, and durable. A bank transfer that
debits one account must also credit the other, or do neither, however it
fails halfway. Ethereum gives every call this property: if execution
fails, every storage write it made is discarded.

What to look for
----------------

The trace shows the debit already written to the *working* storage before
the transfer fails. The committed storage is unchanged all the same: the
failure discarded the half-done write. A successful transfer conserves the
total.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
See :doc:`/exercises/vm` for a worked solution to the exercise.
"""

# %%
# A transfer from slot 0 to slot 1
# --------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.vm.visualizers import plot_execution_trace

transfer = bk.vm.assemble("""
# stack: amount
    LOAD 0           # amount old
    OVER
    OVER             # amount old amount old
    SWAP
    SUB              # amount old old-amount
    STORE 0          # debit first (wraps if the balance is too small)
    OVER             # amount old amount
    LT               # was the balance too small? (old < amount)
    JZ credit
    REVERT
credit:
    LOAD 1
    ADD
    STORE 1
""")
accounts = {0: 100, 1: 20}
ok = bk.vm.execute(transfer, arguments=(30,), storage=accounts)
assert dict(ok.storage) == {0: 70, 1: 50} and sum(ok.storage.values()) == 120

# %%
# Failing halfway
# ---------------
try:
    bk.vm.execute(transfer, arguments=(150,), storage=accounts, trace=True)
except bk.vm.VMError as error:
    failed = error.trace
    print("reverted after", len(failed), "steps; working storage was", failed[-1].storage)
debit = next(step for step in failed if step.opcode == "STORE")
assert debit.storage[0] == (100 - 150) % 2**256  # The debit was written...
assert accounts == {0: 100, 1: 20}  # ...and never committed.

fig, ax = plt.subplots(figsize=(9, 4.5))
plot_execution_trace(failed, ax=ax)
fig.tight_layout()

# %%
# Exercise
# --------
# Move the balance check before the debit. Does the committed outcome change
# for any amount? What does atomicity let a contract get away with here, and
# why is the order of checks and effects still crucial once a contract calls
# out to another one (see the DAO example)?
