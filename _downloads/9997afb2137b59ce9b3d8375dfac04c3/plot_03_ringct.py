r"""
RingCT: hiding the input and the amounts together (2016)
========================================================

Shen Noether's Ring Confidential Transactions combined Monero's ring
signatures with confidential amounts. Each ring member is a one-time key
:math:`P_i` and an amount commitment :math:`C_i`. A second column proves
the amounts balance for the same member that signs: its keys are

.. math::

   Z_i = \frac{C_i}{g^{\text{fee}} \prod_j C^{\text{out}}_j},

which is :math:`h^z` for the real input alone, when its amount equals the
outputs plus the fee. One ring of challenges over both columns, an MLSAG
signature, proves the signer knows the key of some :math:`P_i` and the
:math:`z` of the same :math:`Z_i`. The key image of :math:`P_i` blocks a
second spend.
"""

# %%
import dataclasses

import matplotlib.pyplot as plt

import blockchainkit as bk

G = bk.crypto.TEACHING_GROUP

# %%
# Spending one of eleven outputs
# ------------------------------

secrets = list(range(5_001, 5_012))
amounts = [12, 40, 7, 90, 25, 60, 3, 44, 18, 75, 33]
blindings = [900 + i for i in range(11)]
ring = [
    (G.public(x), bk.crypto.pedersen_commit(v, r))
    for x, v, r in zip(secrets, amounts, blindings, strict=True)
]
real = 5
tx = bk.privacy.ringct_spend(
    ring, real, secrets[real], amounts[real], blindings[real], [(45, 111), (13, 222)], fee=2, bits=8
)
assert bk.privacy.verify_ringct(tx)
print("valid RingCT spend; key image", tx.signature.key_image)

# %%
# What the signature rules out
# ----------------------------

assert not bk.privacy.verify_ringct(dataclasses.replace(tx, fee=1))
try:
    bk.privacy.ringct_spend(ring, 3, secrets[3], amounts[3], blindings[3], [(45, 1), (13, 2)], 2)
except ValueError as error:
    print("member 3 holds 90, not 60:", error)
again = bk.privacy.ringct_spend(
    ring, real, secrets[real], amounts[real], blindings[real], [(58, 333)], fee=2, bits=8, seed=9
)
assert again.signature.key_image == tx.signature.key_image
print("a second spend of the same output repeats the key image")

# %%
# Every member gets two responses
# -------------------------------

fig, ax = plt.subplots(figsize=(7, 3.5))
for column, name in enumerate(("key column", "amount column")):
    ax.scatter(range(11), [r[column] / G.q for r in tx.signature.responses], label=name)
ax.set(xlabel="ring member", ylabel="response / q", ylim=(0, 1))
ax.set_title("Which member was spent, and for how much? Hidden")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Why does RingCT need the second column at all? Show that a transaction
# with a correct key-column signature but outputs worth more than the
# real input fails verification.
# A worked solution is in :doc:`/exercises/privacy`.
