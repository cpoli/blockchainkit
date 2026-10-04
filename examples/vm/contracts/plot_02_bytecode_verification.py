"""
Bytecode verification: check before you run (Gosling 1995)
==========================================================

Java let browsers download and run code from strangers. Its virtual
machine first *verifies* the bytecode: by following every path through the
program without running it, it proves that no instruction can pop from an
empty stack and that every instruction is always reached with the same
stack height. Verified code needs no run-time stack checks and its maximum
stack size is known in advance. Ethereum's EOF format brings similar
validation at deployment.

What to look for
----------------

The verifier accepts the contracts in this package and computes their
maximum stack depth, which matches the deepest stack any run reaches. It
rejects a program with an underflow on a path that a test run happens not
to take, and a loop that grows the stack on every turn.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Verify the library's contracts
# ------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

programs = {
    "vending machine": (bk.vm.vending_machine(), 1),
    "batch transfer": (bk.vm.batch_transfer(1, [2, 3], checked=True), 1),
    "expression": (bk.vm.compile_expression("1 + (2 * (3 + (4 * 5)))"), 0),
}
bounds = {}
for name, (program, arguments) in programs.items():
    report = bk.vm.verify_bytecode(program, arguments=arguments)
    assert report.ok, report.errors
    bounds[name] = report.max_depth
print(bounds)
run = bk.vm.execute(programs["expression"][0], trace=True)
assert max(len(step.stack) for step in run.trace) == bounds["expression"]

# %%
# A bug a test run can miss
# -------------------------
# The ADD after ``zero`` underflows, but only when the input is 0.
buggy = bk.vm.assemble("""
    JZ zero
    PUSH 1
    PUSH 2
    ADD
    STOP
zero:
    ADD
""")
assert bk.vm.execute(buggy, arguments=(1,)).stack == (3,)  # The tested path works.
report = bk.vm.verify_bytecode(buggy, arguments=1)
print(report.errors)
assert not report.ok

growing = bk.vm.assemble("top:\n    PUSH 1\n    JMP top")
print(bk.vm.verify_bytecode(growing).errors)

fig, ax = plt.subplots(figsize=(6, 3.5))
ax.barh(list(bounds), list(bounds.values()), color="#0d9488")
ax.set(xlabel="maximum stack depth, proved before running", title="Verified programs")
fig.tight_layout()

# %%
# Exercise
# --------
# The verifier rejects every program whose stack height depends on the path,
# even some that would never fail. Write such a program, and explain why
# Java accepted this loss of expressiveness.
