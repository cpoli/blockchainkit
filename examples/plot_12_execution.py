"""
Programmable state: determinism, bounded work, and atomic failure
=================================================================

A replicated machine must produce the same state transition at every node.
Execution limits stop a program from consuming unbounded instruction steps.
This small stack machine has unit instruction costs, not Ethereum gas prices.

What to look for
----------------

Compare successful execution with an exhausted instruction budget. Success returns new
storage; failure preserves the original storage. An infinite loop stops when its budget
runs out.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

See :doc:`/course` for prerequisites and :doc:`/solutions` for worked answers.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

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
# For this straight-line program only, replay each prefix from the SAME initial
# state to expose its intermediate result. This is not a debugger for jumps:
# truncating a branching program can change whether its targets are valid.
trace = []
for length in range(1, len(program) + 1):
    partial = bk.vm.execute(program[:length], storage=initial)
    opcode, operand = program[length - 1]
    trace.append(
        [
            opcode + (" " + str(operand) if operand is not None else ""),
            str(list(partial.stack)),
            partial.storage.get(0, 0),
            partial.gas_used,
        ]
    )
assert trace[-1][2] == result.storage[0]
assert initial == {0: 10}
fig, ax = plt.subplots(figsize=(9, 3.5))
ax.axis("off")
table = ax.table(
    cellText=trace,
    colLabels=["Instruction", "Stack (top at right)", "Working slot 0", "Gas"],
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2)
ax.set_title("Intermediate working state; commit only if the whole program succeeds")
fig.tight_layout()
