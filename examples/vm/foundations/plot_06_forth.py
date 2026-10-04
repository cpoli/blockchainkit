"""
Forth: programming with stack words (Moore 1970)
================================================

Charles Moore's Forth has no named variables in expressions: words such as
``DUP``, ``DROP``, ``SWAP``, ``OVER`` and ``ROT`` rearrange the stack, and each
word is documented by its *stack diagram*: ``OVER ( a b -- a b a )``. Small,
fast and easy to implement, Forth ran telescopes and spacecraft. Bitcoin
Script is described as Forth-like, and the EVM's ``DUP`` and ``SWAP`` families
serve the same purpose.

What to look for
----------------

Each stack word matches its diagram. The polynomial ``a x**2 + b x + c``
is computed by Horner's rule with stack words only, and gives the same
values as Python for every input.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
See :doc:`/exercises/vm` for a worked solution to the exercise.
"""

# %%
# Check every stack diagram
# -------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

diagrams = {
    "DUP": ((1,), (1, 1)),
    "DROP": ((1, 2), (1,)),
    "SWAP": ((1, 2), (2, 1)),
    "OVER": ((1, 2), (1, 2, 1)),
    "ROT": ((1, 2, 3), (2, 3, 1)),
}
for word, (before, after) in diagrams.items():
    assert bk.vm.execute([(word, None)], arguments=before).stack == after
    print(f"{word:4s} ( {' '.join(map(str, before))} -- {' '.join(map(str, after))} )")

# %%
# Horner's rule without variables
# -------------------------------
# ( x -- a*x*x + b*x + c ) as ((a * x) + b) * x + c, keeping x with OVER.
a, b, c = 3, 5, 7
horner = bk.vm.assemble(f"""
    PUSH {a}
    OVER
    MUL         # x a*x
    PUSH {b}
    ADD         # x a*x+b
    MUL         # (a*x+b)*x
    PUSH {c}
    ADD
""")
xs = list(range(0, 11))
values = [bk.vm.execute(horner, arguments=(x,)).stack[0] for x in xs]
assert values == [a * x * x + b * x + c for x in xs]

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(xs, values, "o")
ax.set(xlabel="x", ylabel="result", title=f"{a}x² + {b}x + {c} from stack words")
fig.tight_layout()

# %%
# Exercise
# --------
# Define ``NIP ( a b -- b )`` and ``TUCK ( a b -- b a b )`` from the five
# words above and check them with ``bk.vm.execute``.
