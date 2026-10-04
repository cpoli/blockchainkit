"""
Pohlig-Hellman: why the group order must have a large prime factor (1978)
=========================================================================

Pohlig and Hellman noticed that a discrete log in a group of order
n = p1**e1 * p2**e2 * ... splits into small problems, one per prime power,
recombined with the Chinese Remainder Theorem. The cost depends on the
*largest prime factor* of n, not on n. A huge group with a smooth order is
weak.

What to look for
----------------

Two groups of about the same size: one whose order splits into small primes,
one of prime order. Pohlig-Hellman breaks the first almost instantly and
gains nothing on the second. This is why Diffie-Hellman and Schnorr use a
subgroup of large *prime* order, like blockchainkit's ``TEACHING_GROUP``.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# A smooth order falls apart
# --------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.crypto.systems.discrete_log import factor_order

smooth_p = 8101  # 8100 = 2**2 * 3**4 * 5**2
print("order factors:", factor_order(smooth_p - 1))
secret = 4321
target = pow(6, secret, smooth_p)  # 6 generates the whole group modulo 8101.
ph = bk.crypto.pohlig_hellman(6, target, smooth_p, smooth_p - 1)
bsgs = bk.crypto.baby_step_giant_step(6, target, smooth_p, smooth_p - 1)
assert ph.exponent == bsgs.exponent == secret
print("Pohlig-Hellman:", ph.group_operations, "ops; baby-step giant-step:", bsgs.group_operations)

# %%
# A prime order does not
# ----------------------
prime_order = bk.crypto.DHGroup(8147, 4073, 4)  # 4073 is prime.
target = prime_order.public(1234)
ph_prime = bk.crypto.pohlig_hellman(4, target, prime_order.p, prime_order.q)
bsgs_prime = bk.crypto.baby_step_giant_step(4, target, prime_order.p, prime_order.q)
assert ph_prime.exponent == bsgs_prime.exponent == 1234
assert ph_prime.group_operations >= bsgs_prime.group_operations

# %%
fig, ax = plt.subplots(figsize=(7, 4))
labels = ["smooth order 8100", "prime order 4073"]
xs = range(2)
ax.bar(
    [x - 0.18 for x in xs],
    [bsgs.group_operations, bsgs_prime.group_operations],
    0.36,
    label="baby-step giant-step",
)
ax.bar(
    [x + 0.18 for x in xs],
    [ph.group_operations, ph_prime.group_operations],
    0.36,
    label="Pohlig-Hellman",
)
ax.set_xticks(list(xs), labels)
ax.set(ylabel="group operations", title="Only the largest prime factor matters")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# The teaching group uses p = 2q + 1 with q prime (a "safe prime"). What is
# the largest prime factor of p - 1, and what would Pohlig-Hellman cost in the
# order-q subgroup? Why would working in the full group modulo p leak one bit
# of every exponent?
