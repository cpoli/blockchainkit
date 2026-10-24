r"""
Confidential transactions: amounts that add up unseen (2015)
============================================================

Gregory Maxwell replaced each amount with a Pedersen commitment
:math:`C = g^v h^r`. Commitments multiply as amounts add, so anyone can
check that nothing is created,

.. math::

   \prod_{\text{in}} C_i = g^{\text{fee}} \prod_{\text{out}} C_j ,

without seeing a single amount. Amounts live modulo the group order
:math:`q`, though, so an output of :math:`q - 1`, which is :math:`-1`,
balances an output one coin too large. Every output therefore carries a
*range proof*: a commitment to each bit, with a ring signature over
:math:`\{C_k, C_k / g^{2^k}\}` showing that one of the two is a pure power
of :math:`h`, so the bit is 0 or 1.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

G = bk.crypto.TEACHING_GROUP

# %%
# An honest payment
# -----------------
# 50 coins in; 30 to the payee, 19 back as change, 1 as the fee.

inputs = [bk.crypto.pedersen_commit(50, 1_111)]
payee = bk.privacy.confidential_output(30, 600, seed=1)
change = bk.privacy.confidential_output(19, 511, seed=2)
assert bk.privacy.verify_confidential(inputs, [payee, change], fee=1)
print("valid; each output proves", payee.range_proof.bits, "bits")

# %%
# Inflation through a negative amount
# -----------------------------------
# Outputs of 1,000 and -951 balance the 50 coins in, less the fee of 1.

big = bk.privacy.confidential_output(1_000, 700, seed=3)
minus = bk.crypto.pedersen_commit(G.q - 951, 1_111 - 700)
assert bk.privacy.commitments_balance(inputs, [big.commitment, minus], fee=1)
forged = bk.privacy.ConfidentialOutput(minus, change.range_proof)
assert not bk.privacy.verify_confidential(inputs, [big, forged], fee=1)
try:
    bk.privacy.prove_range(G.q - 951, 411)
except ValueError as error:
    print("no range proof for -951:", error)

# %%
# Proof size
# ----------

bits = [4, 8, 16, 24, 32]
sizes = [
    len(bk.privacy.prove_range(5, 9, b).bit_commitments) * 4 for b in bits
]  # Per bit: a commitment, a challenge and two responses.
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(bits, sizes, marker="o")
ax.set(xlabel="bits of range", ylabel="numbers in the proof")
ax.set_title("Bitwise range proofs grow linearly")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The sender knows every output's blinding factor. Why must the payee
# learn its own output's amount and blinding factor, and how does the
# payee check what it was paid?
# A worked solution is in :doc:`/exercises/privacy`.
