"""
Hash chains and one-time passwords (Lamport 1981)
=================================================

Lamport proposed logging in without ever sending a reusable password. Hash a
secret seed n times and give the server only the last value. Each login
reveals the value before it: the server hashes it once and compares. A
captured password is useless, because the next one is its *preimage*.
This became S/KEY (1995), and hash chains reappear in blockchains as
commit-reveal randomness and in Lamport-style signatures.

What to look for
----------------

Each password verifies against the previous anchor, and the anchor moves
back along the chain. Replaying a captured password fails, and the attacker
cannot step backwards without inverting SHA-256.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Log in five times
# -----------------
import matplotlib.pyplot as plt

import blockchainkit as bk

chain = bk.structures.hash_chain(b"Alice's secret seed", 100)
anchor = chain[-1]  # Registered with the server once.
used = []
for login in range(5):
    password = chain[-2 - login]
    assert bk.structures.verify_one_time_password(password, anchor)
    used.append(password)
    anchor = password  # The server keeps the newest accepted value.
print("5 logins accepted; the server now stores", anchor.hex()[:16], "...")

# %%
# A captured password cannot be replayed
# --------------------------------------
eavesdropped = used[-1]
assert not bk.structures.verify_one_time_password(eavesdropped, anchor)
next_password = chain[-7]
assert bk.crypto.sha256(next_password) == anchor  # Only the seed holder can produce this.

# %%
# Remaining logins
# ----------------
fig, ax = plt.subplots(figsize=(7, 3))
ax.barh(
    ["used", "remaining"], [len(used), len(chain) - 1 - len(used)], color=["#94a3b8", "#2563eb"]
)
ax.set(xlabel="passwords", title="A chain of 100 hashes gives 99 logins")
fig.tight_layout()

# %%
# Exercise
# --------
# Why must passwords be revealed in reverse order of computation? What does
# a server learn if it is breached, compared with storing a password hash?
