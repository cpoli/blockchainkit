"""
Baby-step giant-step: square-root discrete logs (Shanks 1971)
==============================================================

Diffie-Hellman and Schnorr are safe only if recovering x from g**x is hard.
Trying every exponent costs n steps in a group of order n. Shanks showed a
time-memory trade-off that costs about 2*sqrt(n): store m = sqrt(n) "baby
steps" g**j, then take "giant steps" target * g**(-m*i) until one matches.

What to look for
----------------

The measured work follows 2*sqrt(n), far below n. The square root sets the
security level: a group of order 2**256 gives about 2**128 work, which is
why 256-bit curves are said to offer 128-bit security.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Recover a secret exponent
# -------------------------
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

group = bk.crypto.DHGroup(1019, 509, 4)  # Order-509 subgroup of the integers mod 1019.
secret = 377
public = group.public(secret)
result = bk.crypto.baby_step_giant_step(group.g, public, group.p, group.q)
assert result.exponent == secret
print(f"log_4({public}) = {result.exponent} after {result.group_operations} multiplications")

# %%
# Work grows like the square root of the group order
# --------------------------------------------------
# Safe primes p = 2q + 1, with 4 generating the order-q subgroup.
safe_primes = [
    p for p in range(1000, 200_000) if bk.crypto.is_prime(p) and bk.crypto.is_prime((p - 1) // 2)
]
chosen = safe_primes[:: max(1, len(safe_primes) // 12)]
orders, work = [], []
for p in chosen:
    q = (p - 1) // 2
    target = pow(4, q - 1, p)  # The largest exponent: the worst case.
    orders.append(q)
    work.append(bk.crypto.baby_step_giant_step(4, target, p, q).group_operations)

fig, ax = plt.subplots(figsize=(7, 4))
ax.loglog(orders, work, "o", label="baby-step giant-step")
grid = np.array(orders, dtype=float)
ax.loglog(grid, 2 * np.sqrt(grid), "--", color="black", label="2 sqrt(n)")
ax.loglog(grid, grid, ":", color="#b45309", label="brute force: n")
ax.set(xlabel="group order n", ylabel="group operations", title="Square-root discrete logs")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# The baby-step table needs sqrt(n) memory. Estimate its size in bytes for
# n = 2**64 and for n = 2**256. Pollard's rho method (1978) needs almost no
# memory for the same running time: why does that make memory no defense?
