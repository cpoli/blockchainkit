"""
Ethereum: a replicated computer metered by gas (Buterin 2014)
=============================================================

Ethereum turned a blockchain into a shared computer: every node runs every
contract call and must reach the same state. Since no one can predict
whether an arbitrary program halts, each call carries a gas budget; every
instruction spends some, and running out aborts the call and undoes its
effects. Words are 256 bits, wide enough for hashes and keys.
This small stack machine uses unit instruction costs, not Ethereum's prices.

What to look for
----------------

Compare successful execution with an exhausted gas budget. Success returns
new storage; failure preserves the original storage. An infinite loop stops
when its budget runs out, so every call terminates.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
See :doc:`/exercises/vm` for a worked solution to the exercise.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.vm.visualizers import plot_execution_trace

# Increment persistent slot zero by five.
program = [("LOAD", 0), ("PUSH", 5), ("ADD", None), ("STORE", 0), ("STOP", None)]
initial = {0: 10}
result = bk.vm.execute(program, storage=initial)
assert result.storage[0] == 15
assert bk.vm.execute(program, storage=initial) == result
assert initial == {0: 10}
print("Storage after success:", dict(result.storage), "; gas used:", result.gas_used)

# %%
# Failed executions do not modify the caller's state
# --------------------------------------------------
try:
    bk.vm.execute(program, storage=initial, gas_limit=3)
except bk.vm.VMError as error:
    print("Execution rejected:", error)
else:
    raise AssertionError("expected out-of-gas failure")
assert initial == {0: 10}
try:
    bk.vm.execute([("JMP", 0)], gas_limit=20)
except bk.vm.VMError:
    print("An infinite loop was stopped by its gas budget.")

# %%
limits = list(range(8))
committed = []
for limit in limits:
    try:
        execution = bk.vm.execute(program, storage=initial, gas_limit=limit)
        committed.append(execution.storage[0])
    except bk.vm.VMError:
        committed.append(initial[0])
fig, ax = plt.subplots(figsize=(7, 4))
ax.step(limits, committed, where="mid", marker="o", color="#7c3aed")
ax.axvline(5, linestyle="--", color="#64748b", label="Five instructions, including STOP")
ax.set(
    xlabel="Gas limit",
    ylabel="Committed slot 0 value",
    title="State changes only after successful execution",
    ylim=(8, 17),
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Implement a branch that stores one value when two numbers are equal and
# another value otherwise. Check both branches, stack underflow, and 256-bit
# wraparound. The VM is an independent component; it is not embedded in the
# transfer-only ledger's transaction format.

# %%
# Trace the stack after each instruction
# --------------------------------------
# ``trace=True`` records the machine state after every executed instruction.
# Storage in the trace is the *working* copy: it is committed only if the whole
# program succeeds. The trace follows jumps too, so it works for loops.
traced = bk.vm.execute(program, storage=initial, trace=True)
assert traced.trace[-1].storage == dict(result.storage)
assert initial == {0: 10}
ax = plot_execution_trace(traced.trace)
ax.figure.tight_layout()
