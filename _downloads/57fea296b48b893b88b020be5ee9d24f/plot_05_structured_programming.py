"""
Structured programming: sequence, selection, iteration (Böhm and Jacopini 1966)
===============================================================================

Böhm and Jacopini proved that any flowchart can be rewritten using only
three constructs: doing things in sequence, choosing between two branches,
and repeating while a condition holds. On a stack machine those are simply
straight-line code, a conditional jump (``JZ``) and a backward jump
(``JMP``). The assembler lets us write them with labels instead of
addresses.

What to look for
----------------

The loop computes ``1 + 2 + ... + n`` and agrees with Gauss's formula. The
backward jump is what makes iteration possible, and also what makes the
running time depend on the input: the gas used grows linearly with n.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# A loop written with labels
# --------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

source = """
# Sum 1 + 2 + ... + n, with n in slot 0 and the sum in slot 1.
loop:                # iteration: test, body, jump back
    LOAD 0
    JZ done          # selection: leave when n reaches 0
    LOAD 1
    LOAD 0
    ADD
    STORE 1          # sequence: sum = sum + n
    LOAD 0
    PUSH 1
    SUB
    STORE 0          # n = n - 1
    JMP loop
done:
    STOP
"""
program = bk.vm.assemble(source)
for address, instruction in enumerate(program):
    print(address, instruction)

sizes = [0, 1, 5, 10, 20, 40, 80]
gas = []
for n in sizes:
    result = bk.vm.execute(program, storage={0: n})
    assert result.storage.get(1, 0) == n * (n + 1) // 2
    gas.append(result.gas_used)
print(gas)
assert all(
    b - a == (sizes[i + 1] - sizes[i]) * 11
    for i, (a, b) in enumerate(zip(gas, gas[1:], strict=False))
)

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(sizes, gas, "o-")
ax.set(xlabel="n", ylabel="gas used", title="11 instructions per iteration")
fig.tight_layout()

# %%
# Exercise
# --------
# Add a selection inside the body so that only even numbers are added.
# (The machine has no MOD: compute ``n - 2 * (n / 2)``.) Which of the three
# constructs did you use, and where?
