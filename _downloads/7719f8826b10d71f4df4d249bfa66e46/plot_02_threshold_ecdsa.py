r"""
Threshold ECDSA (Gennaro and Goldfeder, 2018)
=============================================

A multisig script shows its policy on chain and needs a signature per
signer. A threshold signature is one ordinary signature under one key,
made by any t of n parties holding Shamir shares of a private key that no
one ever assembles. Schnorr responses add, but ECDSA's

.. math::

   s = k^{-1}(z + r x)

multiplies secrets. Rosario Gennaro and Steven Goldfeder's protocol
converts products of secrets held by two parties into sums with a
multiplicative-to-additive (MtA) conversion, one for every ordered pair of
signers and each of two products, :math:`k\gamma` and :math:`kx`. Here a
2-of-3 key is generated jointly and used to sign. The MtA step is an ideal
function; the real protocol runs it under Paillier encryption.
"""

# %%
from itertools import combinations

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A jointly generated 2-of-3 key
# ------------------------------

keys = bk.wallets.threshold_keygen(2, 3, seed=2018)
print("joint key address:", bk.wallets.p2pkh_address(keys.public))
for index, _ in keys.shares:
    assert bk.wallets.verify_key_share(keys, index)
print("every share matches the dealers' Feldman commitments")

message = b"pay bob 5 BTC"
for signers in combinations((1, 2, 3), 2):
    signing = bk.wallets.threshold_sign(message, keys, signers, seed=sum(signers))
    valid = bk.wallets.ecdsa_verify(message, signing.signature, keys.public)
    print(f"signers {signers}: r = {hex(signing.signature.r)[:12]}..., valid {valid}")
    assert valid

try:
    bk.wallets.threshold_sign(message, keys, [2])
except ValueError as exc:
    print("one signer:", exc)

# %%
# The work ECDSA's nonlinearity costs
# -----------------------------------
# A Schnorr threshold signature needs no conversions; ECDSA needs
# 2 t (t - 1).

thresholds = list(range(1, 8))
conversions = []
for t in thresholds:
    big = bk.wallets.threshold_keygen(t, t, seed=t)
    signing = bk.wallets.threshold_sign(b"m", big, range(1, t + 1), seed=t)
    assert bk.wallets.ecdsa_verify(b"m", signing.signature, big.public)
    conversions.append(signing.conversions)
assert conversions == [2 * t * (t - 1) for t in thresholds]

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(thresholds, conversions, "o-", color="#dc2626", label="threshold ECDSA (MtA runs)")
ax.plot(thresholds, [0] * len(thresholds), "o-", color="#2563eb", label="threshold Schnorr")
ax.set(xlabel="signers t", ylabel="two-party conversions")
ax.set_title("Quadratic interaction for one ECDSA signature")
ax.legend()
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# Recover the joint private key from two shares with Lagrange coefficients,
# and check it against ``keys.public``. Why does the protocol never do this?
# A worked solution is in :doc:`/exercises/wallets`.
