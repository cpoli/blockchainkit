r"""
Mimblewimble: transactions with no addresses, and cut-through (2016)
====================================================================

A pseudonymous author, "Tom Elvis Jedusor", noticed that in confidential
transactions the blinding factor can be the key. An output is just
:math:`C = g^v h^r`, owned by whoever knows :math:`r`. When a transaction
balances, outputs over inputs leave :math:`h^{k}`, and a Schnorr signature
under this *excess* :math:`E = h^k`, kept in a *kernel*, proves it is
:math:`h` to a known power and not hidden coins.

Since only products matter, transactions merge into one, and an output
spent within the merged set cancels with its input. Nodes can drop it and
still check the whole chain with

.. math::

   \frac{\prod \text{outputs}}{\prod \text{inputs}} \, g^{\text{fees} - \text{minted}}
   = \Big(\prod_k E_k\Big) h^{\text{offset}} .
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A short chain
# -------------

coinbase = bk.privacy.mimblewimble_transaction([], [(60, 101)], minted=60, seed=1)
pay = bk.privacy.mimblewimble_transaction([(60, 101)], [(35, 202), (24, 303)], fee=1, seed=2)
onward = bk.privacy.mimblewimble_transaction([(35, 202)], [(20, 404), (15, 505)], seed=3)
back = bk.privacy.mimblewimble_transaction([(24, 303), (20, 404)], [(44, 606)], seed=4)
chain = [coinbase, pay, onward, back]
assert all(bk.privacy.verify_mimblewimble(tx) for tx in chain)

block = bk.privacy.aggregate(chain)
compact = bk.privacy.cut_through(block)
assert bk.privacy.verify_mimblewimble(block) and bk.privacy.verify_mimblewimble(compact)
print(f"merged: {len(block.inputs)} inputs, {len(block.outputs)} outputs")
print(
    f"after cut-through: {len(compact.inputs)} inputs, {len(compact.outputs)} outputs, "
    f"{len(compact.kernels)} kernels"
)

# %%
# Forged coins do not balance
# ---------------------------

forged = bk.privacy.MimblewimbleTransaction(
    compact.inputs,
    (*compact.outputs, bk.crypto.pedersen_commit(1, 7)),
    compact.kernels,
    compact.offset,
    compact.minted,
)
assert not bk.privacy.verify_mimblewimble(forged)

# %%
# Growth with and without cut-through
# -----------------------------------
# A coin passed hand to hand: each payment spends the last output.

lengths = range(1, 41)
history = [coinbase]
kept_all, kept_cut = [], []
for n in lengths:
    history.append(
        bk.privacy.mimblewimble_transaction([(60, 101 + n - 1)], [(60, 101 + n)], seed=n)
    )
    merged = bk.privacy.aggregate(history)
    kept_all.append(len(merged.inputs) + len(merged.outputs))
    cut = bk.privacy.cut_through(merged)
    kept_cut.append(len(cut.inputs) + len(cut.outputs))
assert kept_cut[-1] == 1

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(lengths, kept_all, label="every input and output")
ax.plot(lengths, kept_cut, label="after cut-through")
ax.set(xlabel="payments", ylabel="commitments stored")
ax.set_title("Spent outputs vanish; only kernels grow")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Without the offset, how could an observer split a merged block back into
# its transactions? Try it on two of the transactions above.
# A worked solution is in :doc:`/exercises/privacy`.
