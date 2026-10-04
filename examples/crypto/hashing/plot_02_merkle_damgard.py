"""
The Merkle-Damgard construction and length extension (1989)
===========================================================

Merkle and Damgard independently showed how to build a hash for messages of
any length from a fixed-size compression function: pad the message, append
its length, and chain the blocks through the function. SHA-256 is built
this way. The digest *is* the final chaining state, which has a famous
consequence.

What to look for
----------------

blockchainkit's step-by-step SHA-256 matches the standard library. Then an
attacker who sees only H(key || message) computes a valid
H(key || message || padding || suffix) without the key: the
length-extension attack that breaks naive secret-prefix MACs.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Hashing as a chain of compressions
# ----------------------------------
import hashlib

import matplotlib.pyplot as plt

import blockchainkit as bk

message = b"x" * 150
padded = message + bk.crypto.sha256_padding(len(message))
states = [bk.crypto.SHA256_IV]
for start in range(0, len(padded), 64):
    states.append(bk.crypto.sha256_compress(states[-1], padded[start : start + 64]))
digest = b"".join(word.to_bytes(4, "big") for word in states[-1])
assert digest == hashlib.sha256(message).digest() == bk.crypto.merkle_damgard_sha256(message)
print(len(message), "bytes ->", len(padded) // 64, "blocks")

# %%
# Extend a hash without knowing the secret
# ----------------------------------------
secret = b"server-side key!"  # The attacker never sees this...
order = b"user=alice&amount=10"
tag = bk.crypto.naive_mac(secret, order)  # ...only the order and its tag.
glue, forged_tag = bk.crypto.length_extension(tag, len(secret) + len(order), b"&amount=1000000")
forged_order = order + glue + b"&amount=1000000"
assert bk.crypto.naive_mac(secret, forged_order) == forged_tag
print("Forged order accepted:", forged_order[-16:])

# %%
# The chaining state through the blocks
# -------------------------------------
fig, ax = plt.subplots(figsize=(8, 3.5))
for word in range(8):
    ax.plot(range(len(states)), [s[word] / 2**32 for s in states], "o-", alpha=0.7)
ax.set(
    xlabel="blocks compressed",
    ylabel="state word / 2**32",
    title="Eight 32-bit words carry everything forward",
)
ax.set_xticks(range(len(states)))
fig.tight_layout()

# %%
# Exercise
# --------
# The forged message contains the padding bytes "glue". Print them and
# explain where the 0x80 byte and the trailing length come from. Why does
# hashing twice, H(H(m)), as Bitcoin does, also stop length extension?
