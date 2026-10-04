"""
Chaum's blind signatures: authenticate a message the signer cannot see (1982)
=============================================================================

Chaum's construction separates authorization from knowledge of a message.
This experiment exposes RSA's multiplicative blinding identity with tiny
integers; a usable payment system needs encoding, issuance, and spent-token rules.

What to look for
----------------

Follow the original message, its hidden form, and the final signature. The final check
succeeds after removing the hiding factor; this is only the signing step of a payment
system.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
See :doc:`/tutorials/solutions` for a worked answer to the exercise.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

key = bk.crypto.rsa_keypair()
message, factor = 42, 7
blinded = bk.crypto.rsa_blind(message, factor, key)
blind_signature = key.decrypt(blinded)  # Private exponentiation by the signer.
signature = bk.crypto.rsa_unblind(blind_signature, factor, key)
assert key.encrypt(signature) == message
assert signature == key.decrypt(message)
print(f"Message {message}; blinded request {blinded}; final signature {signature}")

# %%
# The signer sees the middle column, not the blinding factor
# ----------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 3.8))
ax.set(xlim=(0, 1), ylim=(0, 1))
ax.axis("off")
labels = [
    (0.15, 0.65, f"Holder\nm = {message}\nr = {factor}"),
    (0.5, 0.65, f"Signer receives\nm r^e mod n\n= {blinded}"),
    (0.85, 0.65, f"Signer returns\n(blinded)^d\n= {blind_signature}"),
    (0.5, 0.15, f"Holder removes r\ns = {signature}\ns^e mod n = {message}"),
]
for x, y, label in labels:
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.6", "fc": "#eef2ff", "ec": "#6366f1"},
    )
for start, end in [
    ((0.26, 0.65), (0.37, 0.65)),
    ((0.64, 0.65), (0.74, 0.65)),
    ((0.85, 0.44), (0.63, 0.22)),
]:
    ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.5})
ax.set_title("Authorization and message visibility are different properties")
fig.tight_layout()

# %%
# Exercise
# --------
# Try an r that shares a factor with n. Why can it not be removed? Explain
# why blind signatures alone do not prevent spending the same token twice.
