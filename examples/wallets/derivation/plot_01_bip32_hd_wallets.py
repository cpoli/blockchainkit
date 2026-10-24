r"""
Hierarchical deterministic wallets (BIP32, 2012)
================================================

Early Bitcoin wallets drew each key at random, so a backup went stale with
the next payment. Pieter Wuille's BIP32 derives a tree of keys from one
seed. An extended key is a key k and a chain code c, and child i is

.. math::

   I = \mathrm{HMAC\text{-}SHA512}(c,\ K \,\|\, i), \qquad k_i = I_L + k \bmod n .

Since :math:`k_i G = I_L G + K`, an extended *public* key derives every
normal child's public key: a shop's server can make a new address for each
order and hold no private key. The other side of that coin is that the
extended public key and any one normal child's private key give away the
parent's, which is why accounts are derived with hardened indices
(i >= 2**31), whose data is the private key instead.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# BIP32's first test vector
# -------------------------

master = bk.wallets.master_key(bytes(range(16)))
print("m      ", bk.wallets.serialize_extended_key(master))
account = bk.wallets.derive_path(master, "m/0'")
print("m/0'   ", bk.wallets.serialize_extended_key(bk.wallets.neuter(account)))
assert bk.wallets.serialize_extended_key(master).startswith("xprv9s21ZrQH143K3QTDL4LXw2F7HEK")

# %%
# A shop with only the extended public key
# ----------------------------------------

xpub = bk.wallets.neuter(account)
addresses = []
for order in range(5):
    from_public = bk.wallets.derive_public(xpub, order)
    from_private = bk.wallets.derive_private(account, order)
    assert from_public.public == from_private.public
    addresses.append(bk.wallets.p2pkh_address(from_public.public))
    print(f"order {order}: {addresses[-1]}")

# %%
# One leaked child key, and the whole account falls
# -------------------------------------------------

leaked = bk.wallets.derive_private(account, 3).private
recovered = bk.wallets.recover_parent_private(xpub, leaked, 3)
assert recovered == account.private
print("account key recovered from the xpub and child 3's key")
stolen = bk.wallets.derive_private(
    bk.wallets.ExtendedKey(
        account.chain_code, account.public, recovered, 1, account.index, account.parent_fingerprint
    ),
    4,
)
assert stolen.private == bk.wallets.derive_private(account, 4).private

# The master stays safe: m/0' is hardened, so its key does not reveal m's.
try:
    bk.wallets.recover_parent_private(bk.wallets.neuter(master), recovered, account.index)
except ValueError as exc:
    print("master:", exc)

fig, ax = plt.subplots(figsize=(7, 4))
ax.axis("off")
ax.text(0.5, 0.9, "m", ha="center", fontsize=12)
ax.text(0.5, 0.55, "m/0'  (hardened)", ha="center", fontsize=11)
ax.annotate("", (0.5, 0.6), (0.5, 0.86), arrowprops={"arrowstyle": "->"})
for i in range(5):
    x = 0.1 + 0.2 * i
    color = "#dc2626" if i == 3 else "#2563eb"
    ax.annotate("", (x, 0.2), (0.5, 0.5), arrowprops={"arrowstyle": "->", "color": color})
    ax.text(x, 0.1, f"m/0'/{i}", ha="center", color=color)
ax.text(
    0.5,
    -0.05,
    "xpub + the private key of m/0'/3 reveal m/0' and every child",
    ha="center",
    color="#dc2626",
)
ax.set_title("BIP32: one leaked child of a public parent leaks the parent")
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# Repeat the attack with a hardened child, ``m/0'/3'``. What stops it?
# A worked solution is in :doc:`/exercises/wallets`.
