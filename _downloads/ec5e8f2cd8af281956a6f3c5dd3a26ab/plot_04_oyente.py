r"""
Oyente: symbolic execution finds the BeautyChain overflow in bytecode (2016)
============================================================================

Oyente, by Luu, Chu, Olickel, Saxena and Hobor, ran symbolic execution on
deployed EVM bytecode, with the Z3 solver deciding which paths were
feasible. Run over 19,366 contracts on the main network, it flagged about
8,800 as vulnerable, including the DAO. Working on bytecode means checking
what actually runs, not what the source was meant to say.

Here the same idea runs over the stack machine of :mod:`blockchainkit.vm`.
Storage slot ``k`` starts as the symbol ``s<k>`` and the argument as
``value``; arithmetic wraps modulo :math:`2^{256}`. The bug is stated as
a condition on a finished path: a recipient's balance grows while the
sender's does not shrink,

.. math::

   \mathrm{slot}_1 \ge s_1 \;\wedge\; \mathrm{slot}_2 > s_2 .

On the BeautyChain-style ``batch_transfer``, the solver finds
:math:`\mathrm{value} = 2^{255}`, the value of the April 2018 attack; with
the SafeMath check no input satisfies the condition.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.constants import WORD_MODULUS
from blockchainkit.contracts.visualizers import plot_symbolic_paths

# %%
# Explore the bytecode
# --------------------

bug = "slot1 >= s1 and slot2 > s2"
reports = {}
for checked in (False, True):
    program = bk.vm.batch_transfer(1, [2, 3], checked=checked)
    result = bk.contracts.symbolic_bytecode(program, arguments=("value",))
    witnesses = []
    for path in result.paths:
        if path.outcome == "stop":
            query = (*path.conditions, bk.contracts.expression(bug, **path.state))
            witness = bk.contracts.solve(query, modulus=WORD_MODULUS)
            if witness is not None:
                witnesses.append(witness)
    reports[checked] = (result, witnesses)
    print(f"checked={checked}: {result.outcomes}, bug inputs {witnesses}")

attack = reports[False][1][0]
assert attack["value"] == 2**255 and not reports[True][1]

# %%
# Confirm the witness concretely
# ------------------------------

storage = {1: attack["s1"], 2: attack["s2"], 3: 0}
run = bk.vm.execute(bk.vm.batch_transfer(1, [2, 3]), arguments=(attack["value"],), storage=storage)
print(dict(run.storage))
assert run.storage[2] == run.storage[3] == 2**255 and run.storage[1] == 0

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
plot_symbolic_paths(reports[False][0], ax=left)
left.set_title("batch_transfer: 3 paths")
plot_symbolic_paths(reports[True][0], ax=right)
right.set_title("with the SafeMath check: 4 paths")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# With three recipients the overflowing ``value`` is no longer
# :math:`2^{255}`, and the default candidates miss it. Find a value that
# makes ``3 * value`` wrap to a small number, and pass it to ``solve``
# through ``candidates``. A worked solution is in :doc:`/exercises/contracts`.
