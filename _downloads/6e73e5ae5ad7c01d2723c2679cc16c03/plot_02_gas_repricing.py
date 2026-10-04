"""
Gas repricing after denial-of-service attacks (EIP-150, 2016)
=============================================================

Gas is meant to be proportional to the work an instruction costs every
node. In September 2016 attackers found instructions that were cheap in gas
but slow to execute, because they read state from disk, and filled blocks
with them, slowing nodes to a crawl. EIP-150 ("Tangerine Whistle") raised
their prices: reading storage went from 50 to 200 gas, and ``EXTCODESIZE``
and ``CALL`` from 20 and 40 to 700.

What to look for
----------------

An attacker picks the instruction with the most real work per unit of gas.
Under the old schedule, a block of storage reads takes several times longer
to process than a block of arithmetic with the same gas; after repricing the
gap shrinks. A gas schedule is a security parameter.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
See :doc:`/exercises/vm` for a worked solution to the exercise.
"""

# %%
# Fill a block with each program
# ------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

# Teaching estimate of each instruction's real cost, in arithmetic units:
# reading storage means a disk access.
REAL_COST = {"LOAD": 100}
before = {"LOAD": 50, "ADD": 3, "DROP": 2, "PUSH": 3, "JMP": 8}
after = {**before, "LOAD": 200}

programs = {
    "arithmetic": bk.vm.assemble("PUSH 1\ntop:\n    PUSH 1\n    ADD\n    JMP top"),
    "storage reads": bk.vm.assemble("top:\n    LOAD 0\n    DROP\n    JMP top"),
}


def block_work(program, schedule, gas=200_000):
    """Real work done by one block's worth of gas spent looping on ``program``."""
    try:
        bk.vm.execute(program, gas_limit=gas, gas_costs=schedule, trace=True)
    except bk.vm.VMError as error:  # Every loop ends by running out of gas.
        return sum(REAL_COST.get(step.opcode, 1) for step in error.trace)
    raise AssertionError("the loop should run out of gas")


work = {
    name: {label: block_work(p, s) for label, s in (("before", before), ("after", after))}
    for name, p in programs.items()
}
ratio = {
    label: work["storage reads"][label] / work["arithmetic"][label] for label in ("before", "after")
}
print(work)
print({label: round(r, 1) for label, r in ratio.items()})
assert ratio["before"] > 2 * ratio["after"]

fig, ax = plt.subplots(figsize=(6, 4))
x = range(2)
for i, name in enumerate(programs):
    ax.bar(
        [j + 0.4 * i - 0.2 for j in x], [work[name]["before"], work[name]["after"]], 0.4, label=name
    )
ax.set_xticks(list(x), ["before EIP-150", "after EIP-150"])
ax.set(ylabel="real work per 200,000-gas block", title="Same gas, different work")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Choose a LOAD price that makes the two programs equally expensive per unit
# of real work. Why did EIP-150 not simply set every price that way, and
# what did EIP-2929 (2021) change about pricing storage reads?
