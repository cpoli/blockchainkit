r"""
Bech32 addresses (BIP173, 2017)
===============================

Pieter Wuille and Gregory Maxwell designed Bech32 for segregated-witness
addresses. It uses one case and 32 characters chosen to avoid look-alikes,
and a 6-character checksum that is a BCH code over GF(32): the string,
read as a polynomial, must satisfy

.. math::

   \mathrm{polymod}(\mathrm{expand}(hrp) \,\|\, data \,\|\, checksum) = 1 .

Out of 159,605 candidate codes, the one chosen detects every error in up to
4 characters for strings of up to 89 characters. Base58Check's hash
detects most errors, but promises nothing about any of them. Here every
pattern of one and two substitutions in an address is tried, and a sample
of three and four.
"""

# %%
import random
from itertools import combinations

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The address of a key
# --------------------

key = bk.crypto.public_key(1)
address = bk.wallets.p2wpkh_address(key)
print("private key 1 ->", address)
program = bk.wallets.segwit_decode("bc", address)
print("witness version", program.version, "program", program.program.hex())
assert address == "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
assert program.program == bk.wallets.base58check_decode(bk.wallets.p2pkh_address(key))[1]

# %%
# Errors in up to four characters
# -------------------------------


def detected(positions, rng):
    chars = list(address)
    for i in positions:
        chars[i] = rng.choice([c for c in bk.wallets.CHARSET if c != chars[i]])
    try:
        bk.wallets.bech32_decode("".join(chars))
    except ValueError:
        return True
    return False


rng = random.Random(173)
data_positions = range(3, len(address))
rates = []
for k in (1, 2, 3, 4):
    patterns = list(combinations(data_positions, k))
    if len(patterns) > 3_000:
        patterns = rng.sample(patterns, 3_000)
    hits = sum(detected(p, rng) for p in patterns)
    rates.append(hits / len(patterns))
    print(f"{k} characters wrong: {hits} of {len(patterns)} detected")
assert rates == [1.0, 1.0, 1.0, 1.0]

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar([1, 2, 3, 4], rates, color="#2563eb")
ax.set(xlabel="characters substituted", ylabel="share detected", ylim=(0, 1.05))
ax.set_title("Bech32 detects every error in up to 4 characters")
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# Upper-case the address. Is it still valid? Mix the case. Is it still valid?
# A worked solution is in :doc:`/exercises/wallets`.
