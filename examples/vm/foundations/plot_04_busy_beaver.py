"""
The busy beaver: the longest a small machine can run (Radó 1962)
================================================================

Radó asked: among all Turing machines with n states that halt when started
on a blank tape, which runs longest? Call that number of steps S(n). For
n = 2, a search over every machine gives S(2) = 6. But S grows faster than
any computable function: S(3) = 21, S(4) = 107, and S(5) = 47,176,870,
proved only in 2024. Knowing S(n) would solve the halting problem for
n-state machines, so no algorithm computes it.

What to look for
----------------

The exhaustive search finds the 2-state champion, which halts after 6 steps
with 4 ones on the tape. Its step count is reached long before the search's
budget, but proving that the remaining "unknown" machines never halt is
exactly what the search cannot do.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
See :doc:`/exercises/vm` for a worked solution to the exercise.
"""

# %%
# Search all 20,736 two-state machines
# ------------------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

result = bk.vm.busy_beaver(2, max_steps=50)
print(result.steps, "steps,", result.ones, "ones:", result.machine)
print(result.counts)
assert (result.steps, result.ones) == (6, 4)

# %%
# How long halting machines run
# -----------------------------
lengths = [
    run.steps
    for run in (
        bk.vm.run_turing_machine(rules, max_steps=50) for rules in bk.vm.enumerate_machines(2)
    )
    if run.outcome == "halted"
]
assert max(lengths) == 6

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
left.hist(lengths, bins=np.arange(0.5, 7.5), color="#7c3aed", edgecolor="white")
left.set(xlabel="steps to halt", ylabel="machines", title="Halting 2-state machines")
known = {1: 1, 2: 6, 3: 21, 4: 107, 5: 47_176_870}
right.semilogy(list(known), list(known.values()), "o-")
right.set(xlabel="states n", ylabel="S(n)", title="Busy beaver values (known)")
fig.tight_layout()

# %%
# Exercise
# --------
# ``bk.vm.run_turing_machine`` reproduces the 3-state champion's 21 steps
# from its rule table (see the history page). Why does a gas limit of 22
# steps let you *run* it but not *know* that no other 3-state machine runs
# longer?
