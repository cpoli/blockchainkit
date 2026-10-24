r"""
scrypt and memory-hard key derivation (2009)
============================================

PBKDF2 makes each guess slow but needs almost no memory, so custom chips
run millions of guesses in parallel. Colin Percival's scrypt makes each
guess need a large table as well. Its core, ROMix, fills a table of N
blocks and then reads it at N data-dependent addresses,

.. math::

   V_i = \mathrm{BlockMix}^{\,i}(B), \qquad
   X \leftarrow \mathrm{BlockMix}(X \oplus V_{\mathrm{Integerify}(X) \bmod N}).

An attacker may keep only every k-th entry and recompute the rest, but then
spends about (k + 1)/2 times as long in the second loop: memory times time
stays near constant, so the chip area and time of an attack grow together.
Here the trade-off is measured.
"""

# %%
import hashlib

import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.wallets.visualizers import plot_memory_tradeoff

# %%
# scrypt as specified
# -------------------

ours = bk.wallets.scrypt(b"password", b"NaCl", 64, 2, 1, 32)
assert ours == hashlib.scrypt(b"password", salt=b"NaCl", n=64, r=2, p=1, dklen=32)
print("scrypt(N=64, r=2):", ours.hex())

# %%
# Forgetting part of the table
# ----------------------------

block = bk.wallets.pbkdf2(b"password", b"NaCl", 1, 128)
n = 256
reference, _ = bk.wallets.romix(block, n)
costs = []
for k in (1, 2, 4, 8, 16, 32, 64, 128, 256):
    out, cost = bk.wallets.romix(block, n, keep_every=k)
    assert out == reference
    costs.append(cost)
    print(
        f"keep every {k:3}: {cost.memory:6,} bytes, {cost.block_mixes:6,} BlockMix calls,"
        f" product {cost.memory * cost.block_mixes:,}"
    )

# Filling the table costs N calls at any k, so the product falls from 2N
# to about N/2 per byte-block: a factor of 4 at most, never a free lunch.
products = [c.memory * c.block_mixes for c in costs]
assert max(products) / min(products) < 4.5

ax = plot_memory_tradeoff(costs)
plt.show()

# %%
# Exercise
# --------
# Keeping every k-th entry should cost about :math:`N + N(k + 1)/2`
# BlockMix calls. Check this against the measured counts.
# A worked solution is in :doc:`/exercises/wallets`.
