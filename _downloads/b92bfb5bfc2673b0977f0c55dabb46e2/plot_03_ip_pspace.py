r"""
Shamir's IP = PSPACE: proving a quantified formula (1990)
=========================================================

Interactive proofs can do much more than NP. Shamir showed that they
capture all of PSPACE, whose complete problem is deciding a fully
quantified Boolean formula such as
:math:`\forall x_1 \exists x_2 \forall x_3 \, \varphi`. Arithmetize
:math:`\varphi`, and turn each quantifier into an operator on polynomials:

.. math::

   \forall_i f = f|_{x_i=0} \cdot f|_{x_i=1}, \qquad
   \exists_i f = 1 - (1 - f|_{x_i=0})(1 - f|_{x_i=1}).

The prover peels the operators off one at a time, as in sum-check. Each
product doubles the degree, so Shen's simplification inserts the
linearization :math:`L_i f = (1 - x_i) f|_{x_i=0} + x_i f|_{x_i=1}` after
every quantifier, which agrees with :math:`f` on bits and keeps every
polynomial the prover sends of degree at most two (or the degree of
:math:`\varphi`).
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A true formula, and a prover who claims otherwise
# -------------------------------------------------
# For all x1, there is an x2 that differs from it, and for all x3 ... the
# matrix is satisfiable whichever way the universal players move.

formula = bk.proofs.CNF(4, ((1, 2), (-1, -2), (3, 4, 2), (-3, -4, -2), (1, 3, 4)))
qbf = bk.proofs.QBF("AEAE", formula)
print("the formula is", qbf.evaluate())
honest = bk.proofs.tqbf_protocol(qbf, seed=2)
liar = bk.proofs.tqbf_protocol(qbf, claim=1 - honest.true_value, seed=2)
print(f"{len(honest.rounds)} rounds; honest accepted {honest.accepted}, liar {liar.accepted}")
assert honest.accepted and not liar.accepted

# %%
# Linearization keeps the degrees small
# -------------------------------------

raw = bk.proofs.tqbf_protocol(qbf, seed=2, linearize=False)
assert raw.accepted and raw.max_degree > honest.max_degree
print("largest degree sent: with linearization", honest.max_degree, "without", raw.max_degree)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), gridspec_kw={"width_ratios": [3, 1]})
labels = [f"{r.operator}{r.variable}" for r in honest.rounds]
ax1.bar(range(len(labels)), [len(r.polynomial) - 1 for r in honest.rounds], color="#2563eb")
ax1.set_xticks(range(len(labels)), labels)
ax1.set(xlabel="operator, outermost first", ylabel="degree sent", title="With linearization")
ax2.bar(
    [f"{r.operator}{r.variable}" for r in raw.rounds],
    [len(r.polynomial) - 1 for r in raw.rounds],
    color="#dc2626",
)
ax2.set(title="Quantifiers only")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Over the field of 13 elements, how often does a prover claiming the wrong
# value convince the verifier? Compare with the bound: rounds times degree,
# divided by 13.
