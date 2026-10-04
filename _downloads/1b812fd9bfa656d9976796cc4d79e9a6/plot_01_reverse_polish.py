"""
Reverse Polish notation: the stack's natural order (Łukasiewicz 1924, Hamblin 1957)
===================================================================================

Łukasiewicz wrote logic with operators before their operands, which needs no
parentheses. Hamblin reversed it for computers: in reverse Polish notation,
``(1 + 2) * 3`` is ``1 2 + 3 *``, and a machine evaluates it by pushing each
number and letting each operator replace the top two values with the
result. Dijkstra's shunting-yard algorithm (1961) translates ordinary
notation into that order. Every stack virtual machine, from Forth to the
EVM, runs programs in this form.

What to look for
----------------

The compiled program is just the RPN sequence, one instruction per token, and
its result matches Python's. The stack height rises with each pending
operand and falls with each operator.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
See :doc:`/exercises/vm` for a worked solution to the exercise.
"""

# %%
# Infix to RPN to instructions
# ----------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.vm.visualizers import plot_execution_trace

expression = "(1 + 2) * 3 - 8 / (4 - 2)"
rpn = bk.vm.to_rpn(expression)
program = bk.vm.compile_expression(expression)
print(" ".join(rpn))
for instruction in program:
    print(instruction)
result = bk.vm.execute(program, trace=True)
assert result.stack == ((1 + 2) * 3 - 8 // (4 - 2),)
assert len(program) == len(rpn)

# %%
# Arithmetic is the machine's
# ---------------------------
# Results wrap modulo 2**256, and / is floor division.
assert bk.vm.execute(bk.vm.compile_expression("0 - 1")).stack == (2**256 - 1,)

fig, ax = plt.subplots(figsize=(9, 4.5))
plot_execution_trace(result.trace, ax=ax)
fig.tight_layout()

# %%
# Exercise
# --------
# Write ``2 * (3 + 4)`` in Polish (prefix) notation and in RPN by hand. Why
# can an RPN evaluator scan left to right with one stack, while a prefix
# evaluator naturally scans right to left?
