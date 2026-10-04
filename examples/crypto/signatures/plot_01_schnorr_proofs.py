"""
Schnorr: knowledge, signatures, and the danger of nonce reuse
=============================================================

An interactive prover commits R=kG, receives c, and responds s=k+cx.
The verifier checks sG=R+cQ. Hashing the transcript and message supplies a
Fiat--Shamir-style challenge for our educational signature construction.

What to look for
----------------

Check a signature, then watch reuse of a secret signing value reveal the private key. A
simulated conversation record also shows why a live unpredictable challenge matters.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

See :doc:`/tutorials/course` for prerequisites and :doc:`/tutorials/solutions` for worked answers.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

c = bk.crypto
private, nonce = 42, 17
public = c.public_key(private)
first = c.sign(b"pay Bob", private, nonce=nonce)
second = c.sign(b"pay Carol", private, nonce=nonce)
assert c.verify(b"pay Bob", first, public)
c1 = c.challenge(b"pay Bob", first.commitment, public)
c2 = c.challenge(b"pay Carol", second.commitment, public)
recovered = c.recover_reused_nonce_key(first, second, c1, c2)
assert recovered == private
print("Reused nonce exposes private key:", recovered)

# %%
# Simulate an accepting transcript without the private key
# --------------------------------------------------------
# Pick c and s first, then compute R=sG-cQ. This shows why a transcript
# alone is not proof of a live interaction; the order of messages matters.
challenge, response = 11, 123
commitment = c.add(
    c.multiply(response, c.SECP256K1.generator, c.SECP256K1),
    c.multiply(-challenge, public, c.SECP256K1),
    c.SECP256K1,
)
assert commitment is not None
assert c.verify_transcript(public, commitment, challenge, response)
assert not c.verify_transcript(public, commitment, challenge + 1, response)
print("Simulated transcript verifies; changing the challenge fails.")

# %%
fig, ax = plt.subplots(figsize=(9, 3.4))
ax.axis("off")
ax.text(0.02, 0.8, "Prover knows x", fontsize=13, weight="bold")
ax.text(0.72, 0.8, "Verifier knows Q=xG", fontsize=13, weight="bold")
for y, label, reverse in [
    (0.6, "R = kG", False),
    (0.4, "unpredictable challenge c", True),
    (0.2, "s = k + cx (mod n)", False),
]:
    start, end = ((0.72, y), (0.25, y)) if reverse else ((0.25, y), (0.72, y))
    ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.5})
    ax.text(0.485, y + 0.04, label, ha="center")
fig.tight_layout()

# %%
# Exercise
# --------
# Derive x=(s1-s2)/(c1-c2) modulo n. Why must the challenges differ?
# Explain the honest-verifier zero-knowledge intuition, and why this example
# is neither a general zero-knowledge proof system nor a BIP-340 implementation.
