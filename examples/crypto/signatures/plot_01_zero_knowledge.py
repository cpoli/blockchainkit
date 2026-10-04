"""
Zero-knowledge proofs: convincing without revealing (Goldwasser, Micali and Rackoff 1985)
=========================================================================================

Goldwasser, Micali and Rackoff asked how much *knowledge* a proof conveys.
In the Schnorr identification protocol the prover sends R = kG, the verifier
replies with a random challenge c, and the prover answers s = k + c*x. The
verifier checks sG = R + cQ and learns that the prover knows x, but nothing
else: a *simulator* can produce transcripts that look identical without x.

What to look for
----------------

An honest run verifies. A simulated transcript, built backwards by choosing
c and s first, verifies too, so a recorded transcript proves nothing to a
third party. Soundness comes only from the order of messages: R first,
unpredictable c second.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# An honest interactive proof
# ---------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

curve = bk.crypto.SECP256K1
x = 42  # The prover's secret.
Q = bk.crypto.public_key(x)
k = 17  # The prover's one-time commitment secret.
R = bk.crypto.public_key(k)
c = 123_456  # The verifier's random challenge, chosen after seeing R.
s = (k + c * x) % curve.order
assert bk.crypto.verify_transcript(Q, R, c, s)

# %%
# A simulator needs no secret
# ---------------------------
# Choose c and s first, then solve for R = sG - cQ.
c_sim, s_sim = 11, 98_765
R_sim = bk.crypto.simulate_transcript(Q, c_sim, s_sim)
assert bk.crypto.verify_transcript(Q, R_sim, c_sim, s_sim)
assert not bk.crypto.verify_transcript(Q, R_sim, c_sim + 1, s_sim)
print("A simulated transcript verifies; the verifier learns nothing it could not make itself.")

# %%
# Who sends what, and in which order
# ----------------------------------
fig, ax = plt.subplots(figsize=(9, 3.4))
ax.axis("off")
ax.text(0.02, 0.8, "Prover knows x", fontsize=13, weight="bold")
ax.text(0.72, 0.8, "Verifier knows Q=xG", fontsize=13, weight="bold")
for y, label, reverse in [
    (0.6, "1. commitment R = kG", False),
    (0.4, "2. unpredictable challenge c", True),
    (0.2, "3. response s = k + cx (mod n)", False),
]:
    start, end = ((0.72, y), (0.25, y)) if reverse else ((0.25, y), (0.72, y))
    ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.5})
    ax.text(0.485, y + 0.04, label, ha="center")
fig.tight_layout()

# %%
# Exercise
# --------
# A cheating prover who could predict c would choose s and c first and send
# R = sG - cQ. Explain why a random c, sent after R, stops this, and estimate
# the cheater's success probability with a 256-bit challenge.
