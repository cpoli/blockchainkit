r"""
PBKDF2 key stretching (2000)
============================

A key derived from a password is only as hard to find as the password.
Burt Kaliski's PBKDF2, in RFC 2898, cannot add entropy, but it makes every
guess expensive: it iterates HMAC c times, and mixes in a salt so that one
precomputed table cannot serve every user,

.. math::

   U_1 = \mathrm{HMAC}(P, S \,\|\, 1), \quad U_j = \mathrm{HMAC}(P, U_{j-1}), \quad
   T = U_1 \oplus \cdots \oplus U_c .

The honest user pays c HMAC calls once; an attacker trying N passwords
pays N times c. BIP39 stretches seed phrases this way with 2048
iterations. Here a three-digit PIN is cracked at increasing iteration
counts.
"""

# %%
import time

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The same password, different salts
# ----------------------------------

alice = bk.wallets.pbkdf2(b"042", b"alice's salt", 10, 32)
bob = bk.wallets.pbkdf2(b"042", b"bob's salt", 10, 32)
print("alice", alice.hex()[:16], "bob", bob.hex()[:16])
assert alice != bob

# %%
# The cost of exhaustive search
# -----------------------------

iterations = [1, 2, 4, 8, 16, 32]
calls, seconds = [], []
for c in iterations:
    key = bk.wallets.pbkdf2(b"731", b"salt", c, 32)
    start = time.perf_counter()
    result = bk.wallets.crack_pin(key, b"salt", c, 3)
    seconds.append(time.perf_counter() - start)
    calls.append(result.hash_calls)
    print(
        f"c = {c:2}: found {result.secret} after {result.guesses} guesses,"
        f" {result.hash_calls:,} HMAC calls"
    )
    assert result.secret == "731" and result.hash_calls == 732 * c

fig, ax = plt.subplots(figsize=(6, 4))
ax.loglog(iterations, calls, "o-", color="#2563eb", label="HMAC calls")
ax.set(xlabel="iterations c", ylabel="attacker's HMAC calls")
twin = ax.twinx()
twin.loglog(iterations, seconds, "s--", color="#dc2626", label="seconds")
twin.set_ylabel("seconds")
ax.set_title("Each iteration multiplies every guess")
fig.legend(loc="upper left", bbox_to_anchor=(0.15, 0.85))
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# How many iterations make cracking a six-digit PIN cost as many HMAC calls
# as cracking an unstretched nine-digit one? What does that say about
# stretching against a long, random password?
# A worked solution is in :doc:`/exercises/wallets`.
