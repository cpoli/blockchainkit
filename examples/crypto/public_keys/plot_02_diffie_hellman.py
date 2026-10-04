"""
Diffie-Hellman: agreeing on a secret over a public channel (1976)
=================================================================

Diffie and Hellman showed that two people can reach the same secret by
exchanging only public values: each raises the other's public element to
their own private exponent, and both arrive at g**(a*b). An eavesdropper sees
g**a and g**b but would need a discrete logarithm to continue.

What to look for
----------------

Both parties compute the same shared element without ever sending it. Then
a man in the middle substitutes his own public value: the arithmetic still
works, but Alice now shares a secret with Mallory. Agreement on a secret is
not authentication of the other person.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
See :doc:`/exercises/crypto` for a worked solution to the exercise.
"""

# %%
# Agree on a shared group element
# -------------------------------
# Neither party sends the shared value. Both reach g**(a*b) modulo p.
import matplotlib.pyplot as plt

import blockchainkit as bk

group = bk.crypto.DHGroup()  # p = 23, q = 11, g = 2: tiny, so every value is visible.
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
# The same exchange in a group too large to search by hand
# --------------------------------------------------------
big = bk.crypto.TEACHING_GROUP
a, b = 0x1234_5678_9ABC, 0x0FED_CBA9_8765
assert big.shared(big.public(b), a) == big.shared(big.public(a), b)

# %%
# Exponentiation scrambles the subgroup
# -------------------------------------
fig, ax = plt.subplots(figsize=(7, 3.8))
exponents = list(range(1, group.q))
ax.scatter(exponents, [group.public(x) for x in exponents], color="#2563eb")
ax.set(
    xlabel="private exponent x", ylabel="public element g**x mod p", title="DH in a tiny subgroup"
)
fig.tight_layout()

# %%
# Exercise
# --------
# Exhaustively recover Alice's exponent from her public value. Why does this
# experiment say nothing about the cost for a carefully chosen large group?
