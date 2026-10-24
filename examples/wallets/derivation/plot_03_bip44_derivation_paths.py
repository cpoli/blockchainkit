r"""
Multi-account derivation paths (BIP44, 2014)
============================================

BIP32 allows any tree of keys, so one wallet program could not restore
another's from the same seed. Marek Palatinus and Pavol Rusnak fixed five
levels,

.. math::

   m / 44' / \text{coin}' / \text{account}' / \text{change} / \text{index},

and a rule for finding used keys: scan each account's receiving chain until
20 addresses in a row are unused (the gap limit), and stop at the first
account with none. A wallet that hands out more than 20 unpaid addresses
in a row hides later payments from any other wallet restoring the seed.
Here a seed is restored with several gap limits.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The paths of a wallet
# ---------------------

master = bk.wallets.master_key(bytes(range(16)))
print(bk.wallets.bip44_path(0, 0, 0, 0), "first Bitcoin receiving address")
print(bk.wallets.bip44_path(60, 0, 0, 0), "first Ether address")
print(bk.wallets.parse_path("m/44'/0'/0'/0/5"))


def address(account, index):
    path = bk.wallets.bip44_path(0, account, 0, index)
    return bk.wallets.p2pkh_address(bk.wallets.derive_path(master, path).public)


# A user paid to addresses 0-3 and 9 of account 0, and to address 0 of account 1.
used = {address(0, i) for i in (0, 1, 2, 3, 9)} | {address(1, 0)}

# %%
# Restoring with different gap limits
# -----------------------------------

limits = [2, 4, 5, 6, 8]
found = []
for gap in limits:
    scan = bk.wallets.discover_accounts(master, used, gap_limit=gap)
    found.append(len(scan.found))
    print(
        f"gap limit {gap}: {scan.accounts} accounts, {len(scan.found)} of 6 addresses,"
        f" {scan.derived} derived"
    )
assert found[0] < 6 and found[-1] == 6

fig, ax = plt.subplots(figsize=(6, 4))
ax.step(limits, found, where="post", color="#2563eb")
ax.plot(limits, found, "o", color="#2563eb")
ax.axhline(6, color="#64748b", linestyle="--", label="addresses used")
ax.set(xlabel="gap limit", ylabel="used addresses found", ylim=(0, 6.5))
ax.set_title("A gap longer than the limit hides the coins")
ax.legend(loc="lower right")
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# The user also pays to address 30 of account 0. What is the smallest gap
# limit that finds it?
# A worked solution is in :doc:`/exercises/wallets`.
