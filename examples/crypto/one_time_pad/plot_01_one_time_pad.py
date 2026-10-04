"""
The one-time pad and perfect secrecy (Vernam 1917, Shannon 1949)
=================================================================

Vernam's teleprinter cipher added a key tape to the message, character by
character. Shannon later proved that if the key is truly random, as long as
the message, and used once, the ciphertext reveals *nothing*: every
plaintext of that length is equally consistent with it.

What to look for
----------------

For one ciphertext, find a key that "decrypts" it to any message you like:
that is perfect secrecy. Then reuse a key for two messages and watch the
pad cancel out, leaving the XOR of the plaintexts.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Encrypt and decrypt with the same operation
# -------------------------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

message = b"ATTACK AT DAWN"
key = bytes([23, 199, 5, 88, 241, 7, 130, 61, 17, 250, 92, 3, 144, 66])  # Fixed for the lesson.
ciphertext = bk.crypto.one_time_pad(message, key)
assert bk.crypto.one_time_pad(ciphertext, key) == message
print("ciphertext:", ciphertext.hex())

# %%
# Every plaintext is possible
# ---------------------------
# For each candidate there is exactly one key: candidate XOR ciphertext.
# Without the key, an eavesdropper cannot rule any of them out.
for candidate in (b"ATTACK AT DAWN", b"RETREAT AT TEN", b"HOLD POSITION!"):
    fitting_key = bk.crypto.xor_bytes(ciphertext, candidate)
    assert bk.crypto.one_time_pad(ciphertext, fitting_key) == candidate
    print(candidate.decode(), "<- key", fitting_key.hex()[:12], "...")

# %%
# Reusing the pad breaks it
# -------------------------
# The "two-time pad": XORing two ciphertexts removes the key. Soviet reuse
# of one-time pads is what the Venona project exploited.
second = b"RETREAT AT TEN"
leak = bk.crypto.xor_bytes(ciphertext, bk.crypto.one_time_pad(second, key))
assert leak == bk.crypto.xor_bytes(message, second)
guess = bk.crypto.xor_bytes(leak, b"ATTACK AT DAWN")  # A guessed first message...
assert guess == second  # ...reveals the second one exactly.

# %%
# Ciphertext bytes are uniform; plaintext bytes are not
# -----------------------------------------------------
rng = np.random.default_rng(1949)
text = b"the quick brown fox jumps over the lazy dog " * 200
pad = rng.integers(0, 256, len(text), dtype=np.uint8).tobytes()
fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), sharey=True)
axes[0].hist(list(text), bins=64, range=(0, 256), color="#64748b")
axes[0].set(title="Plaintext byte values", xlabel="byte")
axes[1].hist(list(bk.crypto.one_time_pad(text, pad)), bins=64, range=(0, 256), color="#2563eb")
axes[1].set(title="One-time-pad ciphertext", xlabel="byte")
fig.tight_layout()

# %%
# Exercise
# --------
# The pad needs as much key as message. Count the key bytes needed to encrypt
# one gigabyte, and explain why Diffie-Hellman (1976) was needed to agree on
# short keys instead. Why does a repeated *short* key (a Vigenere cipher) fail?
