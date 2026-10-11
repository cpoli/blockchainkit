r"""
Halo: recursive proof composition without a trusted setup (2019)
================================================================

A proof that a previous proof verified, applied at every block, would let
anyone check a whole chain from one short proof. That needs verification
cheap enough to run inside a proof. Inner-product arguments have no
trusted setup, but verifying one costs a multi-exponentiation as long as
the committed vector. Bowe, Grigg and Hopwood noticed that the expensive
part is a commitment to the polynomial

.. math::

   g(X) = \prod_{j=1}^{k} \left(1 + c_j X^{2^{k-j}}\right),

which anyone can evaluate in :math:`O(\log n)` from the round challenges
:math:`c_j`. So the verifier *defers* it: it keeps the claim as an
accumulator, merges accumulators by opening a random combination at a random
point (which is another cheap check with its own deferred claim), and pays
the :math:`O(n)` cost once, at the end. Zcash's Orchard (2022) and Mina
rest on this idea.
"""

# %%
import math

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A chain of 12 steps, each verified cheaply
# ------------------------------------------

n = 64
gens = bk.proofs.ipa_generators(n)
accumulator = None
for step in range(12):
    poly = [(step + 1) * i + 7 for i in range(n)]
    opening = bk.proofs.ipa_open(poly, 100 + step, gens)
    claim = bk.proofs.ipa_defer(bk.proofs.ipa_commit(poly, gens), opening, gens)
    assert claim is not None  # The cheap checks passed; G_final is still unchecked.
    group = [claim] if accumulator is None else [accumulator, claim]
    accumulator = bk.proofs.verify_accumulation(group, bk.proofs.accumulate(group, gens), gens)
    assert accumulator is not None
assert bk.proofs.decide(accumulator, gens)
print("12 openings verified with one final O(n) check")

# %%
# A bad claim survives the cheap checks but not the end
# -----------------------------------------------------

fake = bk.proofs.HaloAccumulator(claim.challenges, claim.g_final * 4 % bk.crypto.TEACHING_GROUP.p)
merged = bk.proofs.verify_accumulation([fake], bk.proofs.accumulate([fake], gens), gens)
assert merged is None or not bk.proofs.decide(merged, gens)
print("a tampered accumulator is rejected by the final decision")

# %%
# Group exponentiations: verify everything, or defer
# --------------------------------------------------
# A full check costs about n + 2 log2 n + 3 exponentiations; a deferred check
# and one accumulation step about 2 (2 log2 n + 3) + 2, and the decision n
# once.

rounds = int(math.log2(n))
steps = range(1, 65)
full = [s * (n + 2 * rounds + 3) for s in steps]
deferred = [s * (2 * (2 * rounds + 3) + 2) + n for s in steps]
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(steps, full, color="#dc2626", label="verify every opening fully")
ax.plot(steps, deferred, color="#2563eb", label="Halo: defer and accumulate")
ax.set(xlabel="proofs in the chain", ylabel="group exponentiations")
ax.set_title(f"Amortizing inner-product verification, n = {n}")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Check that ``challenge_polynomial(c, x)`` equals the inner product of the
# coefficient vector s, built from the challenges, with (1, x, x**2, ...): the
# fact that lets the verifier skip computing G_final.
