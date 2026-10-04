"""
MuSig: Schnorr multi-signatures and the rogue-key attack (2018)
===============================================================

Because Schnorr signatures are linear, n signers can produce one ordinary
signature for the sum of their keys. Summing keys naively is unsafe: an
attacker who announces Q_rogue = xG - Q_honest controls the sum alone.
Maxwell, Poelstra, Seurin and Wuille's MuSig weights each key by a hash of
the whole key list, a_i = H(L, Q_i), so no key can cancel the others.

What to look for
----------------

The rogue key takes over a naive aggregate. With MuSig coefficients the
attack fails, and three signers produce one 64-byte-style signature that
verifies like any other. This is how Taproot multisig spends look like
single-signer spends on Bitcoin.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# The rogue-key attack on naive aggregation
# -----------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

curve = bk.crypto.SECP256K1
honest = bk.crypto.public_key(3)
attacker_secret = 1234
negated_honest = (honest[0], -honest[1] % curve.p)
rogue = bk.crypto.add(bk.crypto.public_key(attacker_secret), negated_honest, curve)
naive_aggregate = bk.crypto.add(honest, rogue, curve)
assert naive_aggregate == bk.crypto.public_key(attacker_secret)
forgery = bk.crypto.sign(b"send everything to Mallory", attacker_secret, nonce=99)
assert bk.crypto.verify(b"send everything to Mallory", forgery, naive_aggregate)
print("Naive aggregation: the attacker signed alone for the 'joint' key")

# %%
# MuSig coefficients stop it
# --------------------------
musig_aggregate = bk.crypto.aggregate_public_keys([honest, rogue])
assert musig_aggregate != bk.crypto.public_key(attacker_secret)
assert not bk.crypto.verify(b"send everything to Mallory", forgery, musig_aggregate)

# %%
# Three honest signers, one signature
# -----------------------------------
privates, nonces = [11, 22, 33], [101, 202, 303]
publics = [bk.crypto.public_key(x) for x in privates]
aggregate = bk.crypto.aggregate_public_keys(publics)
signature = bk.crypto.musig_sign(b"spend from the vault", privates, nonces)
assert bk.crypto.verify(b"spend from the vault", signature, aggregate)
coefficients = bk.crypto.musig_coefficients(publics)
print("coefficients a_i:", [hex(a)[:10] + "..." for a in coefficients])

# %%
fig, ax = plt.subplots(figsize=(7, 3.2))
results = {
    "naive key,\nforged sig": bk.crypto.verify(
        b"send everything to Mallory", forgery, naive_aggregate
    ),
    "MuSig key,\nforged sig": bk.crypto.verify(
        b"send everything to Mallory", forgery, musig_aggregate
    ),
    "MuSig key,\njoint sig": bk.crypto.verify(b"spend from the vault", signature, aggregate),
}
ax.bar(results.keys(), [int(v) for v in results.values()], color=["#dc2626", "#16a34a", "#2563eb"])
ax.set(ylabel="verifies", yticks=[0, 1], title="Key aggregation with and without MuSig")
fig.tight_layout()

# %%
# Exercise
# --------
# musig_sign plays all signers in one process. In a real protocol, why must
# signers exchange commitments to their nonces R_i before revealing them?
# (MuSig2 later reduced this to two rounds.)
