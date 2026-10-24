r"""
TumbleBit: an untrusted tumbler that cannot link payments (2017)
================================================================

A mixing service, a *tumbler*, takes coins from payers and pays payees.
Heilman, Alshenibr, Baldimtsi, Scafuro and Goldberg made one that can
neither steal nor tell who paid whom. The tumbler promises each payee a
token locked under an RSA *puzzle* :math:`z = \epsilon^e \bmod N`, which
only it can solve. The payee blinds the puzzle with a random :math:`\rho`,

.. math::

   z' = z \rho^{e} \bmod N, \qquad (z')^{d} = \epsilon \rho ,

and a payer pays the tumbler to solve :math:`z'`. Dividing the solution by
:math:`\rho` gives :math:`\epsilon`, which opens the token. The tumbler
saw :math:`z` with the payee and :math:`z'` with the payer: unrelated
numbers, as in Chaum's blind signatures.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Twenty payments through one tumbler
# -----------------------------------

pairs = [(f"payer{i}", f"payee{i}") for i in range(20)]
blinded = bk.privacy.run_tumbler(pairs, seed=1)
plain = bk.privacy.run_tumbler(pairs, blind=False, seed=1)
assert all(blinded.paid) and all(plain.paid)
print("links without blinding:", len(bk.privacy.tumbler_links(plain)))
print("links with blinding:   ", len(bk.privacy.tumbler_links(blinded)))
assert bk.privacy.tumbler_links(blinded) == ()

# %%
# The tumbler's two logs
# ----------------------
# Without blinding the same puzzle appears in both; with blinding, never.

n = bk.privacy.TUMBLER_KEY.n
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, run, title in ((ax1, plain, "unblinded"), (ax2, blinded, "blinded")):
    ax.scatter(
        [z / n for _, z in run.promised],
        [z / n for _, z in run.solved],
        color="#2563eb",
    )
    ax.plot([0, 1], [0, 1], color="#64748b", linestyle=":")
    ax.set(xlabel="puzzle promised to payee i / N", title=f"{title} puzzles")
ax1.set_ylabel("puzzle solved for payer i / N")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Every payment in a TumbleBit epoch has the same size, and all are made
# in the same window. Why do both matter for unlinkability, even though
# the puzzles are blinded?
# A worked solution is in :doc:`/exercises/privacy`.
