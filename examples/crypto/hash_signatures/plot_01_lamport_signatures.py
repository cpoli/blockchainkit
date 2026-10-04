"""
Lamport one-time signatures: signing with only a hash (1979)
============================================================

Lamport built a signature from nothing but a one-way function. The private
key is 256 pairs of random strings; the public key is their hashes. To sign,
reveal one string from each pair, chosen by the bits of the message digest.

What to look for
----------------

A signature verifies, and changing the message breaks it. But every
signature reveals half the private key: after a few signatures an attacker
can sign new messages. The key must sign exactly once. Because security
needs only a one-way hash, the idea survives quantum computers; it is the
ancestor of today's standardized SPHINCS+ (SLH-DSA).

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Sign once, verify
# -----------------
import matplotlib.pyplot as plt

import blockchainkit as bk

key = bk.crypto.lamport_keypair(b"teaching seed, never reuse")
signature = bk.crypto.lamport_sign(b"pay Bob 10", key)
assert bk.crypto.lamport_verify(b"pay Bob 10", signature, key.public)
assert not bk.crypto.lamport_verify(b"pay Bob 99", signature, key.public)
print(len(signature), "revealed preimages,", sum(map(len, signature)), "bytes")


# %%
# Reusing the key leaks it
# ------------------------
# Collect the preimages revealed by k signatures, then count how many random
# messages an attacker could now sign (every digest bit must be covered).
def forgeable_fraction(signed_count: int, trials: int = 300) -> float:
    known = set()
    for i in range(signed_count):
        message = f"message {i}".encode()
        for position, revealed in enumerate(bk.crypto.lamport_sign(message, key)):
            bit = key.private[position].index(revealed)
            known.add((position, bit))
    hits = 0
    for t in range(trials):
        digest = int.from_bytes(bk.crypto.sha256(f"forgery {t}".encode()), "big")
        bits = [(digest >> (255 - i)) & 1 for i in range(256)]
        hits += all((i, b) in known for i, b in enumerate(bits))
    return hits / trials


counts = list(range(1, 13))
observed = [forgeable_fraction(k) for k in counts]
expected = [(1 - 0.5**k) ** 256 for k in counts]
assert observed[0] == 0 and observed[-1] > 0.8

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(counts, observed, "o", label="measured")
ax.plot(
    counts, expected, "-", color="black", label="expected over random messages: (1 - 2**-k)**256"
)
ax.set(
    xlabel="signatures made with one key",
    ylabel="fraction of messages forgeable",
    title="A one-time key used many times",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# A Lamport public key is 16 KiB. Merkle (1979) signed many messages by
# putting many one-time public keys in a hash tree and publishing only its
# root. How big is a proof that one key belongs to a tree of 2**20 keys?
