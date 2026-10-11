r"""
Kate-Zaverucha-Goldberg commitments: one point per polynomial (2010)
====================================================================

Kate, Zaverucha and Goldberg committed to a whole polynomial with a single
group element, :math:`C = [f(\tau)]G`, computed from published powers
:math:`[\tau^i]G` of a secret :math:`\tau`. To prove :math:`f(z) = y`, the
prover commits to the quotient :math:`q(X) = (f(X) - y)/(X - z)`, which is a
polynomial exactly when the claim is true, and the verifier checks the
division at the hidden point with a pairing:

.. math::

   e(C - [y]G,\ G) = e([q(\tau)]G,\ [\tau]G - [z]G).

Commitment and proof are one point each, whatever the degree. KZG is the
polynomial commitment inside PLONK, and Ethereum's blob commitments
(EIP-4844).
"""

# %%
from dataclasses import replace

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Commit, open, verify
# --------------------

srs = bk.proofs.trusted_setup(64, secret=987654321)  # The secret is "forgotten" from here on.
f = [3, 1, 4, 1, 5, 9, 2, 6]
commitment = bk.proofs.kzg_commit(f, srs)
opening = bk.proofs.kzg_open(f, 10, srs)
print("f(10) =", opening.value)
assert opening.value == bk.proofs.poly_eval(f, 10)
assert bk.proofs.kzg_verify(commitment, opening, srs)

# %%
# Binding: a false value, or another polynomial, fails
# ----------------------------------------------------

assert not bk.proofs.kzg_verify(commitment, replace(opening, value=opening.value + 1), srs)
other = bk.proofs.poly_add(f, bk.proofs.vanishing_polynomial([10]))  # Same value at 10.
assert bk.proofs.poly_eval(other, 10) == opening.value
assert bk.proofs.kzg_commit(other, srs) != commitment
assert not bk.proofs.kzg_verify(bk.proofs.kzg_commit(other, srs), opening, srs)

# %%
# Size does not grow with the degree
# ----------------------------------

degrees = [1, 2, 4, 8, 16, 32, 64]
for d in degrees:
    poly = list(range(1, d + 2))
    c, o = bk.proofs.kzg_commit(poly, srs), bk.proofs.kzg_open(poly, 7, srs)
    assert bk.proofs.kzg_verify(c, o, srs)

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(degrees, [d + 1 for d in degrees], "o-", color="#dc2626", label="coefficients (sending f)")
ax.plot(degrees, [2] * len(degrees), "o-", color="#2563eb", label="commitment + opening (points)")
ax.set_xscale("log", base=2)
ax.set(
    xlabel="degree", ylabel="field or group elements", title="KZG: constant-size evaluation proofs"
)
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Open f at two points with *one* witness: divide f minus the line through
# (z1, y1) and (z2, y2) by (X - z1)(X - z2), and check the pairing equation
# with the commitment to that vanishing polynomial in place of [tau - z]G.
# A worked solution is in :doc:`/exercises/proofs`.
