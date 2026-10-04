"""
The Fiat-Shamir heuristic: from interaction to signatures (1986)
================================================================

Fiat and Shamir removed the live verifier: compute the challenge as a hash
of the commitment and the message, c = H(R, Q, m). If the hash behaves like
a random function, the prover cannot choose R after knowing c, and the
transcript becomes a non-interactive proof bound to the message: a
signature.

What to look for
----------------

The hashed challenge changes completely with the message. The simulator
trick from the zero-knowledge example fails, because R must be fixed before
the hash reveals c. Schnorr signatures, EdDSA, and most zero-knowledge proof
systems used by blockchains rely on this transformation.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# The challenge is a hash of everything said so far
# -------------------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

x, k = 42, 17
Q, R = bk.crypto.public_key(x), bk.crypto.public_key(k)
c_bob = bk.crypto.challenge(b"pay Bob", R, Q)
c_carol = bk.crypto.challenge(b"pay Carol", R, Q)
assert c_bob != c_carol
print("challenge for 'pay Bob':  ", hex(c_bob)[:20], "...")
print("challenge for 'pay Carol':", hex(c_carol)[:20], "...")

# %%
# Simulation no longer works
# --------------------------
# A forger picks s and c, sets R = sG - cQ, but the hash then demands a
# different c for that R.
s_forged, c_forged = 98_765, 11
R_forged = bk.crypto.simulate_transcript(Q, c_forged, s_forged)
assert bk.crypto.challenge(b"pay Mallory", R_forged, Q) != c_forged
forgery = bk.crypto.SchnorrSignature(R_forged, s_forged)
assert not bk.crypto.verify(b"pay Mallory", forgery, Q)

# %%
# Searching for a lucky challenge on a tiny curve
# -----------------------------------------------
# On a 19-element curve a forger succeeds when the hash happens to hit the
# chosen c: about 1 time in 19. On secp256k1, 1 time in 2**256.
toy = bk.crypto.TOY_CURVE
Q_toy = bk.crypto.public_key(5, toy)
hits = []
for attempt in range(400):
    s_try, c_try = attempt % (toy.order - 1) + 1, 3
    if s_try == c_try * 5 % toy.order:
        continue  # s = c*x would make R the point at infinity.
    R_try = bk.crypto.simulate_transcript(Q_toy, c_try, s_try, toy)
    message = f"attempt {attempt}".encode()
    hits.append(bk.crypto.challenge(message, R_try, Q_toy, toy) == c_try)
rate = sum(hits) / len(hits)
assert 0.01 < rate < 0.12
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.bar(
    ["measured forgery rate", "1 / group order"],
    [rate, 1 / toy.order],
    color=["#dc2626", "#64748b"],
)
ax.set(ylabel="probability", title="Forging = guessing the hash output")
fig.tight_layout()

# %%
# Exercise
# --------
# Bind less into the hash: compute c = H(R, m) without Q. Read the
# documentation of :func:`blockchainkit.crypto.systems.signatures.challenge` and explain what
# including the public key and curve parameters protects against.
