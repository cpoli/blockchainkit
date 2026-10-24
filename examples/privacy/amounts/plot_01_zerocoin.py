r"""
Zerocoin: spending a coin without saying which (2013)
=====================================================

Miers, Garman, Green and Rubin proposed an extension to Bitcoin in which
a user *mints* a coin by publishing a commitment :math:`C = g^S h^r` to a
random serial number :math:`S`, and later *spends* it by revealing
:math:`S` with a zero-knowledge proof that some minted coin opens to it.
Spent serials are recorded, so no coin is spent twice, but the spend
points to no particular mint: every coin ever minted is in the anonymity
set.

To keep the proof short, the coins are gathered in an RSA accumulator
:math:`A = u^{c_1 c_2 \cdots c_n} \bmod N`; each coin's witness is the
accumulator of all the others, and

.. math::

   w_i^{\,c_i} \equiv A \pmod N .

Here the spend instead proves membership with a ring signature over all
coins, since :math:`C_i g^{-S} = h^{r}` exactly for the coin being spent.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The accumulator
# ---------------

pool = bk.privacy.ZerocoinPool()
coins = [(1_000 + 37 * i, 50 + i) for i in range(12)]
for serial, blinding in coins:
    pool.mint(bk.privacy.mint_coin(serial, blinding))
primes = [bk.privacy.hash_to_prime(c) for c in pool.coins]
accumulator = pool.accumulator
for i, prime in enumerate(primes):
    assert bk.privacy.verify_membership(
        accumulator, prime, bk.privacy.membership_witness(primes, i)
    )
print(f"12 coins, one {accumulator.bit_length()}-bit accumulator")

# %%
# Spending, once
# --------------

serial, blinding = coins[7]
spend = bk.privacy.prove_zerocoin_spend(pool.coins, serial, blinding, b"pay alice", seed=1)
pool.spend(spend, b"pay alice")
try:
    pool.spend(spend, b"pay alice")
except ValueError as error:
    print("second spend:", error)
assert pool.spent == {serial}

# %%
# The proof looks the same for every coin
# ---------------------------------------
# Every ring member gets a response, so the spent coin does not stand out.

q = bk.crypto.TEACHING_GROUP.q
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.bar(range(12), [r / q for r in spend.proof.responses], color="#2563eb")
ax.set(xlabel="minted coin", ylabel="response / q", ylim=(0, 1))
ax.set_title("Which of the 12 coins was spent? The proof does not say")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The proof here grows with the number of coins, while Zerocoin's stays
# constant. Roughly how many group elements does a spend from a pool of a
# million coins carry here, and why did Zerocoin need a trusted RSA
# modulus to do better?
# A worked solution is in :doc:`/exercises/privacy`.
