r"""
The sum-check protocol: verifying a sum of 2**n terms (1990)
============================================================

Lund, Fortnow, Karloff and Nisan showed that a prover can convince a
verifier of a sum over the whole Boolean cube,

.. math::

   H = \sum_{b \in \{0,1\}^n} f(b),

while the verifier evaluates :math:`f` only once. In round :math:`i` the
prover sends the univariate polynomial
:math:`g_i(X) = \sum f(r_1, \dots, r_{i-1}, X, b_{i+1}, \dots, b_n)`; the
verifier checks :math:`g_i(0) + g_i(1)` against the previous claim and
fixes :math:`X` to a random :math:`r_i`. A lie must be repeated at the
random point, where by Schwartz-Zippel it survives with probability at most
:math:`d/|\mathbb{F}|` per round.

Here :math:`f` arithmetizes a Boolean formula, so :math:`H` counts its
satisfying assignments: the #SAT problem that LFKN placed in interactive
proofs.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Counting the solutions of a formula
# -----------------------------------

rng = Random(5)
n = 10
clauses = tuple(
    tuple(rng.choice([1, -1]) * v for v in rng.sample(range(1, n + 1), 3)) for _ in range(30)
)
formula = bk.proofs.CNF(n, clauses)


def f(point):
    return formula.evaluate(point, bk.proofs.FIELD_PRIME)


run = bk.proofs.sumcheck(f, n, formula.degree, seed=1)
print(f"the prover claims {run.claim} solutions; accepted: {run.accepted}")
assert run.accepted and run.claim == formula.count_solutions()
print(f"{n} rounds of degree {formula.degree}; the verifier evaluated f once, not {2**n} times")

# %%
# A false claim survives only by luck
# -----------------------------------
# Over a small field the cheating prover's luck is measurable, and stays
# below n d / p.

small = bk.proofs.CNF(4, ((1, 2), (-2, 3), (3, 4), (-1, -4)))
primes = [97, 193, 389, 769, 1543]
measured, bounds = [], []
for p in primes:
    true = small.count_solutions()
    runs = [
        bk.proofs.sumcheck(
            lambda x, p=p: small.evaluate(x, p), 4, small.degree, p, claim=true + 1, seed=s
        )
        for s in range(2000)
    ]
    measured.append(sum(r.accepted for r in runs) / len(runs))
    bounds.append(4 * small.degree / p)
    assert measured[-1] <= bounds[-1] + 0.01
print("acceptance of a false count:", [round(m, 3) for m in measured])

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.loglog(primes, measured, "o", color="#2563eb", label="false claims accepted")
ax.loglog(primes, bounds, color="#dc2626", label="bound n d / p")
ax.set(xlabel="field size", ylabel="probability", title="Sum-check soundness error")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Count the evaluations of f made by the honest prover and by the verifier
# for the four-variable formula above, by wrapping f in a counter. How do
# they grow with n?
# A worked solution is in :doc:`/exercises/proofs`.
