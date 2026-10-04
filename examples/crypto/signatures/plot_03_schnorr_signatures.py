"""
Schnorr signatures: short, fast, and linear (1989-1991)
=======================================================

Schnorr applied Fiat-Shamir to his identification protocol in a group of
prime order, giving signatures (R, s) with s = k + H(R, Q, m) * x. They were
shorter and faster than the alternatives, and their linearity (signatures
add when keys add) later enabled multi-signatures. A patent kept them out
of standards until 2008; Bitcoin adopted them in 2021 (BIP-340).

What to look for
----------------

A signature verifies only for the exact message and key. The verification
equation sG = R + cQ is checked step by step. The format here is a
teaching scheme, not BIP-340's byte encoding.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Sign and verify
# ---------------
import matplotlib.pyplot as plt

import blockchainkit as bk

curve = bk.crypto.SECP256K1
x = 0xC0FFEE
Q = bk.crypto.public_key(x)
nonce = bk.crypto.deterministic_nonce(x, b"pay Bob 10")
signature = bk.crypto.sign(b"pay Bob 10", x, nonce=nonce)
assert bk.crypto.verify(b"pay Bob 10", signature, Q)
assert not bk.crypto.verify(b"pay Bob 11", signature, Q)
assert not bk.crypto.verify(b"pay Bob 10", signature, bk.crypto.public_key(x + 1))

# %%
# The verification equation, by hand
# -----------------------------------
c = bk.crypto.challenge(b"pay Bob 10", signature.commitment, Q)
left = bk.crypto.multiply(signature.response, curve.generator, curve)
right = bk.crypto.add(signature.commitment, bk.crypto.multiply(c, Q, curve), curve)
assert left == right
print("sG == R + cQ:", left == right)

# %%
# Tampering with any part fails
# -----------------------------
from dataclasses import replace

cases = {
    "genuine": bk.crypto.verify(b"pay Bob 10", signature, Q),
    "s + 1": bk.crypto.verify(
        b"pay Bob 10", replace(signature, response=signature.response + 1), Q
    ),
    "other R": bk.crypto.verify(
        b"pay Bob 10", replace(signature, commitment=bk.crypto.public_key(5)), Q
    ),
    "other message": bk.crypto.verify(b"pay Bob 1000", signature, Q),
}
assert list(cases.values()) == [True, False, False, False]
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.bar(cases.keys(), [int(v) for v in cases.values()], color=["#16a34a"] + ["#dc2626"] * 3)
ax.set(ylabel="verifies", yticks=[0, 1], title="A signature binds key, message, R and s")
fig.tight_layout()

# %%
# Exercise
# --------
# Two signers with keys x1, x2 and nonces k1, k2 each compute s_i for the
# same challenge c. Show that (R1 + R2, s1 + s2) verifies for Q1 + Q2. Why
# is that property both useful and dangerous? (See the MuSig example.)
