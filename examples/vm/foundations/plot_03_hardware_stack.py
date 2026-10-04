"""
Stack hardware: a bounded stack (Burroughs B5000, Barton 1961)
==============================================================

Robert Barton designed the Burroughs B5000 around a hardware stack: programs
compiled from Algol were sequences of stack operations, with no general
registers to allocate. A real stack has finite size, so the machine must
know how deep a computation goes. The EVM limits its stack to 1024 words
for the same reason.

What to look for
----------------

The same sum needs very different stack depths depending on its shape:
``((1 + 2) + 3) + ...`` never holds more than two values, while
``1 + (2 + (3 + ...))`` holds every operand at once. With a small stack
limit, the right-nested form overflows.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Two shapes of the same sum
# --------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.vm.visualizers import plot_stack_height

n = 12
left = "(" * (n - 2) + "1 + 2" + "".join(f") + {k}" for k in range(3, n + 1))
right = "".join(f"{k} + (" for k in range(1, n)) + str(n) + ")" * (n - 1)
traces = {}
for name, expression in (("left-nested", left), ("right-nested", right)):
    result = bk.vm.execute(bk.vm.compile_expression(expression), trace=True)
    assert result.stack == (n * (n + 1) // 2,)
    traces[name] = result.trace
peaks = {name: max(len(step.stack) for step in trace) for name, trace in traces.items()}
print(peaks)
assert peaks == {"left-nested": 2, "right-nested": n}

# %%
# A hardware limit
# ----------------
try:
    bk.vm.execute(bk.vm.compile_expression(right), stack_limit=8)
except bk.vm.VMError as error:
    print("right-nested with 8 slots:", error)
assert bk.vm.execute(bk.vm.compile_expression(left), stack_limit=8).stack == (78,)

fig, ax = plt.subplots(figsize=(7, 4))
for name, trace in traces.items():
    plot_stack_height(trace, label=name, ax=ax)
ax.axhline(8, color="black", linestyle="--")
ax.set_title("Same sum, different stack needs")
fig.tight_layout()

# %%
# Exercise
# --------
# For a balanced tree of additions over 2**k numbers, what is the peak stack
# height? (This is the Ershov or Strahler number of the expression tree.)
