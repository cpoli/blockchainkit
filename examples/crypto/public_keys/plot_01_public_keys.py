"""
Public keys: agree on a secret, then invert a trapdoor
======================================================

Diffie--Hellman separates public exchange from a private exponent. RSA
provides a different construction with public and private inverse operations.
Use tiny integers to inspect both ideas; these parameters offer no security.

What to look for
----------------

Compare the two shared-secret calculations: they agree. Then watch a substituted public
key change who shares the secret. In the RSA section, changing encrypted data changes
the recovered message.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

See :doc:`/tutorials/course` for prerequisites and :doc:`/tutorials/solutions` for worked answers.
"""

# %%
# Agree on a shared group element
# -------------------------------
# Neither party sends the shared value. Both reach g**(a*b) modulo p.
import matplotlib.pyplot as plt

import blockchainkit as bk

group = bk.crypto.DHGroup()
alice_secret, bob_secret = 3, 7
alice_public = group.public(alice_secret)
bob_public = group.public(bob_secret)
shared = group.shared(bob_public, alice_secret)
assert shared == group.shared(alice_public, bob_secret)
print(f"Public values: {alice_public}, {bob_public}; shared element: {shared}")

# %%
# Authentication is a separate problem
# ------------------------------------
# Mallory substitutes her own public value. Alice now shares a secret with
# Mallory, not Bob. Real protocols authenticate the exchange and use a KDF.
mallory_secret = 4
alice_mallory = group.shared(group.public(mallory_secret), alice_secret)
assert alice_mallory == group.shared(alice_public, mallory_secret)
assert alice_mallory != shared
print("After key substitution, Alice's shared element is", alice_mallory)

# %%
# RSA and its algebraic weakness without padding
# ----------------------------------------------
key = bk.crypto.rsa_keypair()
ciphertext = key.encrypt(65)
assert (ciphertext, key.decrypt(ciphertext)) == (2790, 65)
# Multiplying a ciphertext by 2**e multiplies the decrypted message by 2.
modified = ciphertext * pow(2, key.e, key.n) % key.n
assert key.decrypt(modified) == 130
print("RSA: 65 ->", ciphertext, "->", key.decrypt(ciphertext))
print("Malleated ciphertext decrypts to", key.decrypt(modified))

# %%
# Inspect modular arithmetic
# --------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
exponents = list(range(1, group.q))
axes[0].scatter(exponents, [group.public(x) for x in exponents], color="#2563eb")
axes[0].set(xlabel="Private exponent", ylabel="Public element", title="DH in a tiny subgroup")
messages = list(range(50))
axes[1].scatter(messages, [key.encrypt(m) for m in messages], s=18, color="#7c3aed")
axes[1].set(xlabel="Message integer", ylabel="Ciphertext integer", title="Textbook RSA permutation")
fig.tight_layout()

# %%
# Exercise
# --------
# Exhaustively recover Alice's exponent from her public value. Why does this
# experiment say nothing about the cost for a carefully chosen large group?
# Explain why a scrambled-looking plot is not evidence of secure encryption.
