r"""
FRI: fast Reed-Solomon proximity testing (2018)
===============================================

How can a verifier tell that a million committed values are evaluations of
a polynomial of degree below :math:`d`, reading only a few of them?
Ben-Sasson, Bentov, Horesh and Riabzev fold the problem in half each
round. Writing :math:`f(X) = f_e(X^2) + X f_o(X^2)`, a random
:math:`\alpha` gives a polynomial of half the degree on a domain of half
the size,

.. math::

   f'(x^2) = \frac{f(x) + f(-x)}{2} + \alpha\,\frac{f(x) - f(-x)}{2x},

and after :math:`\log_2 d` folds a low-degree function has become a
constant. The prover commits to every layer with a Merkle tree; the
verifier checks each fold at a few random positions. FRI needs only a hash
function: it is the engine of STARKs, and of Plonky2 and RISC Zero.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.proofs.visualizers import plot_proof_sizes

# %%
# Degree below the bound passes, above it fails
# ---------------------------------------------
# Evaluations on a coset of 512 points: a blowup of 8 over the bound 64.

within = bk.proofs.evaluate_on_domain(range(1, 65), 512, offset=31)  # Degree 63.
beyond = bk.proofs.evaluate_on_domain(range(1, 66), 512, offset=31)  # Degree 64.
for label, values in (("degree 63", within), ("degree 64", beyond)):
    proof = bk.proofs.fri_prove(values, 64, num_queries=16)
    ok = bk.proofs.fri_verify(proof, domain_size=512, degree_bound=64, num_queries=16)
    print(f"{label}: {len(proof.roots)} folding layers, accepted {ok}")
    assert ok == (label == "degree 63")

# %%
# The proof grows with log**2 of the domain
# -----------------------------------------
# Each of 16 queries opens two values and their paths in each of log2(d)
# layers.

points = []
for log_n in range(6, 15, 2):
    n = 2**log_n
    proof = bk.proofs.fri_prove(
        bk.proofs.evaluate_on_domain(range(n // 8), n, offset=31), n // 8, num_queries=16
    )
    assert bk.proofs.fri_verify(proof, domain_size=n, degree_bound=n // 8, num_queries=16)
    points.append((n, proof.size))
print("domain size and proof bytes:", points)

ax = plot_proof_sizes(
    {"sending all evaluations": [(n, 8 * n) for n, _ in points], "FRI, 16 queries": points},
    xlabel="evaluations committed",
)
ax.set_title("FRI proofs grow polylogarithmically")
plt.show()

# %%
# Exercise
# --------
# With blowup 8, a function far from every low-degree polynomial passes each
# query with probability at most about 1/8 + small terms. How many queries
# give 80 bits of soundness, and how large is the proof for a domain of 2**14?
