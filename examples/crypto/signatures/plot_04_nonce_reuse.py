"""
Nonce reuse in practice, and deterministic nonces (2010-2013)
=============================================================

A Schnorr or ECDSA signature hides the private key behind a one-time nonce.
Reuse the nonce for two messages and two equations in one unknown give the
key away. In 2010 the fail0verflow team recovered Sony's PlayStation 3
signing key this way: the console's ECDSA used a constant nonce. RFC 6979
(2013) removed the random number generator from signing: derive the nonce
deterministically from the key and the message with HMAC.

What to look for
----------------

Two signatures with the same nonce reveal x = (s1 - s2)/(c1 - c2). With
RFC 6979 nonces, each message gets its own nonce automatically, and the
derivation reproduces the RFC's published test vector.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
See :doc:`/tutorials/solutions` for a worked answer to the exercise.
"""

# %%
# Two signatures, one nonce: the key falls out
# --------------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

c = bk.crypto
private, nonce = 42, 17
public = c.public_key(private)
first = c.sign(b"pay Bob", private, nonce=nonce)
second = c.sign(b"pay Carol", private, nonce=nonce)
assert first.commitment == second.commitment  # The tell-tale sign: identical R.
c1 = c.challenge(b"pay Bob", first.commitment, public)
c2 = c.challenge(b"pay Carol", second.commitment, public)
recovered = c.recover_reused_nonce_key(first, second, c1, c2)
assert recovered == private
print("Reused nonce exposes private key:", recovered)

# %%
# Deterministic nonces (RFC 6979)
# -------------------------------
# The RFC's own example: NIST P-256's group order, its private key, "sample".
p256_order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
p256_key = 0xC9AFA9D845BA75166B5C215767B1D6934E50C3DB36E89B127B8A622B120F6721
k = c.deterministic_nonce(p256_key, b"sample", p256_order)
assert k == 0xA6E3C57DD01ABE90086538398355DD4C3B17AA873382B0F24D6129493D8AAD60
print("RFC 6979 test vector reproduced")

nonces = [c.deterministic_nonce(private, f"payment {i}".encode()) for i in range(200)]
assert len(set(nonces)) == 200  # A fresh nonce for every message, no RNG involved.

# %%
# Nonces spread over the whole range
# ----------------------------------
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.hist([n / c.SECP256K1.order for n in nonces], bins=20, color="#2563eb", edgecolor="white")
ax.set(xlabel="nonce / group order", ylabel="messages", title="RFC 6979 nonces for 200 messages")
fig.tight_layout()

# %%
# Exercise
# --------
# Derive x = (s1 - s2)/(c1 - c2) modulo n from s_i = k + c_i x. Why must the
# challenges differ? Why does a deterministic nonce stay safe even when the
# same message is signed twice?
