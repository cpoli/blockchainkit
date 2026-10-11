r"""
STARKs: transparent proofs of computation from hashes (2018)
============================================================

Ben-Sasson, Bentov, Horesh and Riabzev built scalable, transparent
arguments of knowledge: no trusted setup, nothing but a hash function, and
proofs that grow polylogarithmically with the computation. Write the
computation as an execution trace, here the Fibonacci sequence
:math:`a_{i+2} = a_{i+1} + a_i`, interpolate it as a polynomial
:math:`f` over a subgroup :math:`\langle g\rangle`, and turn each rule into
a divisibility:

.. math::

   \frac{f(g^2 X) - f(gX) - f(X)}{\prod_{i < T-2} (X - g^i)}, \qquad
   \frac{f(X) - a_{T-1}}{X - g^{T-1}}

are polynomials exactly when the trace follows the rule and ends at the
claimed value. The prover commits to :math:`f` on a larger domain and proves
with FRI that a random combination of the quotients has low degree.
StarkNet and many zkVMs use this design.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.proofs.visualizers import plot_proof_sizes

# %%
# Proving the 1024th Fibonacci number modulo p
# --------------------------------------------

steps = 1024
result = bk.proofs.fibonacci_trace(steps)[-1]
proof = bk.proofs.stark_prove(steps)
assert bk.proofs.stark_verify(proof, steps=steps, result=result)
print(f"a_{steps - 1} = {result}; proof of {proof.size:,} bytes")

false = bk.proofs.stark_prove(steps, claimed=result + 1)
assert not bk.proofs.stark_verify(false, steps=steps, result=result + 1)
print("a false result fails: its boundary quotient is not a polynomial, and FRI notices")

# %%
# Proof size against computation length
# -------------------------------------
# The proof grows like log**2 of the trace, the trace itself linearly. For
# the tiny traces here the proof is still the larger, by a shrinking
# factor; extrapolated, the lines cross near 2**15 steps, and real STARKs
# prove billions.

points = []
for log_t in range(4, 12):
    t = 2**log_t
    p = bk.proofs.stark_prove(t)
    assert bk.proofs.stark_verify(p, steps=t, result=bk.proofs.fibonacci_trace(t)[-1])
    points.append((t, p.size))
print("trace length and proof bytes:", points)
assert points[-1][1] < 4 * points[0][1]

ax = plot_proof_sizes(
    {"the trace itself (8 bytes a step)": [(t, 8 * t) for t, _ in points], "STARK": points},
    xlabel="steps of computation",
)
ax.set_title("STARK proofs grow with log**2 of the computation")
plt.show()

# %%
# Exercise
# --------
# The low-degree extension lives on a coset ``31 * <w>`` that avoids the
# trace domain ``<g>``. Why? Evaluate the boundary quotient (f(x) - 1)/(x - 1)
# on the subgroup ``<w>`` itself and see which point breaks it.
