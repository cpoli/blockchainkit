"""
HMAC: keyed hashing that resists length extension (1996)
========================================================

Bellare, Canetti and Krawczyk defined HMAC to turn any Merkle-Damgard hash
into a message authentication code with a security proof:
HMAC(k, m) = H((k XOR opad) || H((k XOR ipad) || m)). The outer hash hides
the inner chaining state, so an attacker has nothing to extend.

What to look for
----------------

The length-extension forgery that defeats the naive H(key || message) fails
against HMAC. HMAC also appears inside RFC 6979's deterministic nonces and
in key derivation (HKDF).

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Same attack, two MACs
# ---------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

secret = b"server-side key!"
order = b"user=alice&amount=10"
suffix = b"&amount=1000000"
results = {}
for name, mac in (("naive H(k||m)", bk.crypto.naive_mac), ("HMAC", bk.crypto.hmac_sha256)):
    tag = mac(secret, order)
    glue, forged = bk.crypto.length_extension(tag, len(secret) + len(order), suffix)
    results[name] = forged == mac(secret, order + glue + suffix)
    print(f"{name}: forgery {'accepted' if results[name] else 'rejected'}")
assert results == {"naive H(k||m)": True, "HMAC": False}

# %%
# A known test vector
# -------------------
tag = bk.crypto.hmac_sha256(b"key", b"The quick brown fox jumps over the lazy dog")
assert tag.hex().startswith("f7bc83f430538424b13298e6aa6fb143")

# %%
# Changing one key bit changes about half the tag bits
# ----------------------------------------------------
base = bk.crypto.hmac_sha256(secret, order)
flips = []
for bit in range(len(secret) * 8):
    key = bytearray(secret)
    key[bit // 8] ^= 1 << (bit % 8)
    flips.append(bk.crypto.hamming_distance(base, bk.crypto.hmac_sha256(bytes(key), order)))
assert 110 < sum(flips) / len(flips) < 146
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.hist(flips, bins=15, color="#16a34a", edgecolor="white")
ax.axvline(128, color="black", linestyle="--", label="half of 256 bits")
ax.set(
    xlabel="tag bits changed by one key-bit flip",
    ylabel="key bits",
    title="An HMAC tag depends on every key bit",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Would H(m || k), with the key at the end, resist length extension? What
# property of the hash would it then rely on instead? (Hint: think of
# collisions in m.)
