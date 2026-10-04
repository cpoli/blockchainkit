"""
RSA: a public trapdoor (Rivest, Shamir and Adleman 1978)
========================================================

RSA publishes n = p*q and an exponent e; only the holder of p and q can
compute the inverse exponent d. Anyone can raise a message to e; only the
key holder can undo it. The same inverse pair gives digital signatures.

What to look for
----------------

The message 65 encrypts to 2790 and decrypts back. Then textbook RSA's
algebra shows through: multiplying a ciphertext by 2**e doubles the hidden
message. Real RSA adds randomized padding (OAEP, PSS) to break this.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
See :doc:`/exercises/crypto` for a worked solution to the exercise.
"""

# %%
# Encrypt and decrypt
# -------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

key = bk.crypto.rsa_keypair()  # p = 61, q = 53, e = 17: the classic textbook key.
ciphertext = key.encrypt(65)
assert (ciphertext, key.decrypt(ciphertext)) == (2790, 65)
print("n =", key.n, "e =", key.e, "d =", key.d)
print("RSA: 65 ->", ciphertext, "->", key.decrypt(ciphertext))

# %%
# Signatures are the same operation in reverse
# --------------------------------------------
signature = key.decrypt(42)  # Apply the private exponent.
assert key.encrypt(signature) == 42  # Anyone can check with the public one.

# %%
# Textbook RSA is malleable
# -------------------------
# Multiplying a ciphertext by 2**e multiplies the decrypted message by 2.
modified = ciphertext * pow(2, key.e, key.n) % key.n
assert key.decrypt(modified) == 130
print("Malleated ciphertext decrypts to", key.decrypt(modified))

# %%
# A permutation of the residues
# -----------------------------
fig, ax = plt.subplots(figsize=(7, 3.8))
messages = list(range(60))
ax.scatter(messages, [key.encrypt(m) for m in messages], s=18, color="#7c3aed")
ax.set(xlabel="message m", ylabel="ciphertext m**e mod n", title="Textbook RSA permutation")
fig.tight_layout()

# %%
# Exercise
# --------
# Factor n = 3233 by trial division and recompute d. Explain why a
# scrambled-looking plot is not evidence of secure encryption.
