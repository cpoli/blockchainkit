r"""
Bulletproofs: range proofs without a trusted setup (2018)
=========================================================

Confidential transactions hide amounts in Pedersen commitments
:math:`V = g^v h^\gamma`, which add: inputs balance outputs if the
commitments' product does. But the arithmetic is modulo the group order, so
an output of :math:`-1000` would mint coins unless every amount is proved
to lie in :math:`[0, 2^n)`. Bünz, Bootle, Boneh, Poelstra, Wuille and
Maxwell reduced the range check to one inner product
:math:`t = \langle l, r \rangle`, and proved the inner product by halving
the vectors each round, sending two group elements per halving. The proof
is

.. math::

   2 \log_2 n + 4 \text{ group elements and } 5 \text{ scalars},

with generators hashed into the group: no trusted setup. Monero adopted
Bulletproofs in 2018, cutting its transaction sizes by about 80%.
"""

# %%
from dataclasses import replace

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A confidential transfer that balances
# -------------------------------------

G = bk.crypto.TEACHING_GROUP
inputs = bk.proofs.range_commitment(500, 11)
outputs = [bk.proofs.range_commitment(320, 5), bk.proofs.range_commitment(180, 6)]
assert inputs == outputs[0] * outputs[1] % G.p  # Commitments multiply as amounts add.
proofs = [bk.proofs.range_proof(v, b, 32, seed=i) for i, (v, b) in enumerate([(320, 5), (180, 6)])]
assert all(bk.proofs.verify_range_proof(proof, 32) for proof in proofs)
print("both outputs proved in [0, 2**32) without revealing them")

# %%
# Minting from a negative output is impossible
# --------------------------------------------
# 500 = 1500 + (-1000): the commitments balance modulo q, but -1000 is
# q - 1000, far outside the range, and no proof exists for it.

negative = G.q - 1000
assert bk.proofs.range_commitment(1500, 5) * bk.proofs.range_commitment(negative, 6) % G.p == inputs
try:
    bk.proofs.range_proof(negative, 6, 32)
except ValueError as error:
    print("proving -1000:", error)
forged = bk.proofs.range_proof(1000, 6, 32)  # A proof for +1000 does not transfer.
assert not bk.proofs.verify_range_proof(
    replace(forged, commitment=bk.proofs.range_commitment(negative, 6)), 32
)

# %%
# Logarithmic size
# ----------------

bits = [2, 4, 8, 16, 32, 64]
sizes = []
for n in bits:
    proof = bk.proofs.range_proof(2**n - 1, 3, n)
    assert bk.proofs.verify_range_proof(proof, n)
    sizes.append(sum(proof.size))
print("elements sent:", dict(zip(bits, sizes, strict=True)))

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(
    bits, [4 * n for n in bits], "o-", color="#dc2626", label="one commitment and proof per bit"
)
ax.plot(bits, sizes, "o-", color="#2563eb", label="Bulletproofs")
ax.set_xscale("log", base=2)
ax.set(xlabel="range bits n", ylabel="group elements and scalars sent")
ax.set_title("Range proofs in 2 log2 n + 9 elements")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Prove that a value lies in [0, 1000) rather than a power-of-two range:
# prove that both v and v + 2**16 - 1000 lie in [0, 2**16).
# A worked solution is in :doc:`/exercises/proofs`.
