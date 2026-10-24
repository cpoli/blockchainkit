r"""
The brain-wallet drain (Vasek et al., 2016)
===========================================

A brain wallet's private key is the SHA-256 of a passphrase,

.. math::

   k = \mathrm{SHA256}(\text{passphrase}),

so nothing needs to be stored. But anyone can hash the same passphrase.
Marie Vasek, Joseph Bonneau, Ryan Castellucci, Cameron Keith and Tyler
Moore searched the Bitcoin chain for brain wallets and found that thieves
had precomputed the keys of dictionaries, quotations and leaked
passwords, and emptied most funded brain wallets, many within minutes,
often racing one another. There is no salt and no stretching, and a phrase
a person chooses has far less entropy than a random key. Here thieves with
precomputed tables sweep a population of brain wallets.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The most famous brain wallet
# ----------------------------

key = bk.wallets.brain_wallet_key("password")
address = bk.wallets.brain_wallet_address("password")
print("SHA256('password') =", hex(key))
print("address:", address)
assert bk.wallets.crack_brain_wallet(address, bk.wallets.PHRASEBOOK) == "password"

# A random 12-word phrase is out of reach of any dictionary.
strong = bk.wallets.entropy_to_mnemonic(bytes(range(16)))
assert (
    bk.wallets.crack_brain_wallet(bk.wallets.brain_wallet_address(strong), bk.wallets.PHRASEBOOK)
    is None
)

# %%
# Thieves racing to sweep deposits
# --------------------------------
# Three thieves: a fast one with most of the phrasebook, and two slower ones.

thieves = [(0.7, 2.0), (0.5, 10.0), (0.3, 50.0)]
drain = bk.wallets.simulate_brain_drain(300, weak_share=0.4, thieves=thieves, seed=2016)
print(f"{drain.wallets} wallets, {drain.weak} with a common phrase, {drain.drained} drained")
print("wallets taken by each thief:", drain.hauls)
assert drain.drained <= drain.weak and drain.hauls[0] == max(drain.hauls)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
ax1.hist(drain.delays, bins=range(1, max(drain.delays) + 2), color="#dc2626")
ax1.set(xlabel="blocks from deposit to theft", ylabel="wallets")
ax1.set_title("Most weak wallets are swept at once")
ax2.bar(["fast", "medium", "slow"], drain.hauls, color="#64748b")
ax2.set(ylabel="wallets drained")
ax2.set_title("The fastest table wins the race")
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# Brain wallets that stretched their passphrase, such as WarpWallet with
# scrypt and PBKDF2, slowed each guess. Why does that still not save a
# passphrase from the phrasebook?
# A worked solution is in :doc:`/exercises/wallets`.
