r"""
Base58Check addresses (2009)
============================

Bitcoin's first release wrote an address as a version byte, the 20-byte
``HASH160`` of a public key and a 4-byte checksum, in base 58: the digits
and letters without 0, O, I and l, which are easily confused. A wallet
refuses to pay an address whose checksum fails, so a typo is caught unless
it happens to match the checksum, with probability

.. math::

   2^{-32} \approx 2.3 \times 10^{-10}.

The account names of :mod:`blockchainkit.structures` are bare SHA-256
digests, where every typo is just another valid account. Here every
single-character typo of an address is tried.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The address of a key
# --------------------

key = bk.crypto.public_key(1)
address = bk.wallets.p2pkh_address(key)
print("private key 1 ->", address)
print("uncompressed   ->", bk.wallets.p2pkh_address(key, compressed=False))
version, payload = bk.wallets.base58check_decode(address)
print("version", version, "HASH160", payload.hex())
assert address == "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"

# %%
# Every single-character typo
# ---------------------------

alphabet = bk.wallets.ALPHABET
typos = [
    address[:i] + c + address[i + 1 :]
    for i in range(len(address))
    for c in alphabet
    if c != address[i]
]
accepted = [t for t in typos if bk.wallets.is_valid_address(t)]
print(f"{len(typos):,} typos, {len(accepted)} accepted")
assert not accepted

# An unchecked hex name accepts every typo: each is some other account.
plain = bk.crypto.sha256(bk.crypto.encode_point(key)).hex()
plain_typos = len(plain) * 15

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(["hex digest", "Base58Check"], [plain_typos, len(accepted)], color=["#dc2626", "#2563eb"])
ax.set(ylabel="single-character typos accepted")
ax.set_title(f"Of {len(typos):,} typos, the checksum refuses all")
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# How many of the typos that swap two neighbouring characters does the
# checksum accept?
# A worked solution is in :doc:`/exercises/wallets`.
