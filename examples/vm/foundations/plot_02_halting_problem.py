"""
The halting problem: why every call needs a budget (Turing 1936)
================================================================

Turing defined computation with a machine that reads and writes a tape, and
proved that no program can decide, for every machine and input, whether it
eventually halts. Running a machine longer never settles the question: a
machine that has not halted yet may halt later, or never. A blockchain that
lets anyone submit programs therefore cannot check in advance that they
terminate. It bounds them instead, with a step budget.

What to look for
----------------

All 20,736 two-state Turing machines are run from a blank tape with growing
step budgets. Those that halt do so within six steps; some are caught
repeating a configuration, which proves they loop. But a large group stays
*unknown* at every budget: no finite budget sorts them.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Classify every two-state machine
# --------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

machines = list(bk.vm.enumerate_machines(2))
budgets = [2, 4, 6, 10, 20, 50]
counts = {outcome: [] for outcome in ("halted", "looping", "unknown")}
for budget in budgets:
    tally = {outcome: 0 for outcome in counts}
    for rules in machines:
        tally[bk.vm.run_turing_machine(rules, max_steps=budget).outcome] += 1
    for outcome in counts:
        counts[outcome].append(tally[outcome])
print(counts)
assert counts["halted"][2] == counts["halted"][-1]  # Nothing halts after step 6...
assert counts["unknown"][-1] > 0  # ...yet many machines are still undecided.

# %%
# A machine the budget cannot classify
# ------------------------------------
# This one writes 1s rightward forever without repeating a configuration.
runner = {
    ("A", 0): (1, 1, "A"),
    ("A", 1): (1, 1, "A"),
    ("B", 0): (0, 1, "A"),
    ("B", 1): (0, 1, "A"),
}
for budget in (10, 100, 1000):
    print(budget, bk.vm.run_turing_machine(runner, max_steps=budget).outcome)

fig, ax = plt.subplots(figsize=(7, 4))
for outcome, values in counts.items():
    ax.plot(budgets, values, "o-", label=outcome)
ax.set(xlabel="step budget", ylabel="machines", title="20,736 two-state machines")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Write a cheap test that proves the ``runner`` machine never halts: what
# property of its state and the blank tape ahead makes the future repeat?
# Why can no such collection of tests cover every machine?
