"""
Feldman's verifiable secret sharing (1987)
==========================================

In Shamir's scheme every share holder must trust the dealer: nothing stops
a dealer from handing out shares that do not lie on one polynomial. Feldman
had the dealer publish g**a_j for each coefficient a_j. Each holder checks
g**y == product of C_j**(x**j), which holds only for points on the
committed polynomial.

What to look for
----------------

Honest shares pass the check and any three of them recover the secret. A
corrupted share is caught by its holder before reconstruction. Verifiable
sharing is the starting point of distributed key generation, used for
threshold signatures in modern wallets.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Deal and verify
# ---------------
from itertools import combinations
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

G = bk.crypto.TEACHING_GROUP
secret = 2026
dealt = bk.crypto.feldman_split(secret, 3, 5, randbelow=Random(87).randrange)
assert all(bk.crypto.feldman_verify(share, dealt.commitments) for share in dealt.shares)
assert dealt.commitments[0] == pow(G.g, secret, G.p)  # g**secret is public; secret is not.
for subset in combinations(dealt.shares, 3):
    assert bk.crypto.recover_secret(subset, prime=G.q) == secret
print("5 shares, all verified; any 3 recover the secret")

# %%
# A cheating dealer is caught
# ---------------------------
x, y = dealt.shares[2]
bad_share = (x, (y + 1) % G.q)
assert not bk.crypto.feldman_verify(bad_share, dealt.commitments)
corrupted = [dealt.shares[0], dealt.shares[1], bad_share]
assert bk.crypto.recover_secret(corrupted, prime=G.q) != secret  # Unverified, it would mislead.

# %%
# Which shares pass?
# ------------------
offsets = range(-3, 4)
passes = [bk.crypto.feldman_verify((x, (y + d) % G.q), dealt.commitments) for d in offsets]
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.bar([str(d) for d in offsets], passes, color=["#16a34a" if p else "#dc2626" for p in passes])
ax.set(
    xlabel="error added to share 3",
    ylabel="passes the check",
    yticks=[0, 1],
    title="Only the committed share verifies",
)
fig.tight_layout()

# %%
# Exercise
# --------
# Feldman's commitments reveal g**secret. Explain why that hides the secret
# only computationally, and how Pedersen (1991) used his commitments to make
# verifiable sharing hide the secret perfectly.
