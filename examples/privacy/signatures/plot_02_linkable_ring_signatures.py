r"""
Linkable ring signatures and key images (2004)
==============================================

A ring signature is too anonymous for money: a spender could sign twice
with the same coin and nobody could tell. Liu, Wei and Wong added a *key
image* :math:`I = H_p(P)^x`, fixed by the signer's key pair but revealing
nothing about which key it is. Every signature by the key carries the same
image, and the same response proves both

.. math::

   L_i = g^{r_i} P_i^{c_i}, \qquad R_i = H_p(P_i)^{r_i} I^{c_i},

so the image cannot be faked. A ledger stores the images of spent coins
and rejects a repeat. CryptoNote, and Monero after it, hash the public key
rather than the ring into :math:`H_p`, so the images link across rings.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

G = bk.crypto.TEACHING_GROUP

# %%
# A ledger of spent key images
# ----------------------------

secrets = list(range(1_001, 1_011))
outputs = [G.public(x) for x in secrets]
spent: set[int] = set()


def accept(message, ring, signature):
    if not bk.privacy.lsag_verify(message, ring, signature):
        return "invalid"
    if signature.key_image in spent:
        return "double spend"
    spent.add(signature.key_image)
    return "accepted"


first_ring = [outputs[i] for i in (0, 3, 4, 7)]
second_ring = [outputs[i] for i in (2, 4, 8, 9)]
pay_bob = bk.privacy.lsag_sign(b"pay bob", first_ring, 2, secrets[4], seed=1)
pay_eve = bk.privacy.lsag_sign(b"pay eve", second_ring, 1, secrets[4], seed=2)
pay_cat = bk.privacy.lsag_sign(b"pay cat", second_ring, 3, secrets[9], seed=3)
results = [accept(b"pay bob", first_ring, pay_bob), accept(b"pay eve", second_ring, pay_eve)]
results.append(accept(b"pay cat", second_ring, pay_cat))
print(results)
assert results == ["accepted", "double spend", "accepted"]
assert bk.privacy.linked(pay_bob, pay_eve) and not bk.privacy.linked(pay_eve, pay_cat)

# %%
# The image reveals nothing of the key
# ------------------------------------

images = [bk.privacy.key_image(x) for x in secrets]
fig, ax = plt.subplots(figsize=(6, 4))
ax.scatter([p / G.p for p in outputs], [i / G.p for i in images], color="#2563eb")
ax.set(xlabel="public key / p", ylabel="key image / p", xlim=(0, 1), ylim=(0, 1))
ax.set_title("Key images are unrelated to their public keys")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Why must the key image use :math:`H_p(P)` rather than :math:`g`, that is,
# why would :math:`I = g^x` be a disaster?
# A worked solution is in :doc:`/exercises/privacy`.
