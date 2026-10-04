"""
FLP: no deterministic consensus in an asynchronous network (1985)
=================================================================

Fischer, Lynch and Paterson proved that no deterministic protocol can always
reach agreement in an asynchronous system where even one process may crash.
The adversary does not need to crash anyone: it only chooses the order in
which messages arrive, and can keep the system undecided forever.

What to look for
----------------

Ben-Or's protocol with its coin replaced by a fixed rule, here "process p
adopts p mod 2", never decides against a scheduler that keeps every process
from seeing a strict majority: the values stay split two against two in
every round. Give the processes real coins and the same scheduler loses.
FLP says *every* deterministic protocol has some such schedule. Practical
protocols escape it with randomness (Ben-Or) or timing assumptions
(partial synchrony).

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# A deterministic protocol, stalled forever
# -----------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk


def parity(process, round_):
    return process % 2


stalled = bk.consensus.ben_or([0, 0, 1, 1], faults=1, coin=parity, max_rounds=500)
assert not stalled.decided and stalled.rounds == 500
print("adversarial schedule, deterministic rule: no decision after 500 rounds")

# %%
# Change one ingredient at a time
# -------------------------------
cases = {
    "deterministic rule": bk.consensus.ben_or([0, 0, 1, 1], faults=1, coin=parity, max_rounds=500),
    "random coin": bk.consensus.ben_or([0, 0, 1, 1], faults=1, seed=3, max_rounds=500),
}
for label, run in cases.items():
    print(label, "->", "decided" if run.decided else "stalled", f"({run.rounds} rounds)")
assert [run.decided for run in cases.values()] == [False, True]
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.bar(cases.keys(), [run.rounds for run in cases.values()], color=["#dc2626", "#16a34a"])
ax.set(
    ylabel="rounds run (500 = gave up)", title="Same adversarial schedule, deterministic vs random"
)
fig.tight_layout()

# %%
# Exercise
# --------
# Try ``coin=lambda p, r: r % 2`` (every process adopts the same bit). It
# decides against this scheduler. Why does that not contradict FLP? (The
# theorem promises a stalling schedule for every deterministic protocol, not
# that this particular scheduler finds it.)
