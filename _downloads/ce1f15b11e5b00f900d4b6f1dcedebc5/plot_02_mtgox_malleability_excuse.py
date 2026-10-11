r"""
The Mt. Gox collapse and the malleability excuse (2014)
=======================================================

In February 2014 Mt. Gox, then handling most bitcoin trading, halted
withdrawals and blamed transaction malleability: an attacker could alter a
withdrawal's signature encoding in flight, changing its txid; the exchange,
which tracked withdrawals by txid, would not find it on chain, and paid
again. Weeks later it filed for bankruptcy, about 850,000 bitcoins short.

Decker and Wattenhofer scanned the network for malleated transactions and
found that malleability attacks could account for at most 386 bitcoins
before the announcement, a tiny fraction of the loss. The coins had been
disappearing for years. An exchange losing to malleability loses exactly
the withdrawals it re-sends,

.. math::

   \text{loss} = \sum_{w \,:\, \mathrm{txid}(w) \notin \mathrm{chain}} a_w ,

and tracking withdrawals by an id that excludes the signature, as segregated
witness's txid later did, makes it zero.
"""

# %%
import random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The exchange signs 200 withdrawals; an attacker malleates some in flight
# ------------------------------------------------------------------------
# A different signature over the same payment stands in for Bitcoin's
# re-encoded signature: same payment, valid, different txid.

EXCHANGE_KEY = 7  # A fixed teaching key: never use such a key for real money.
hot_wallet = bk.crypto.public_key(EXCHANGE_KEY)
rng = random.Random(2014)
withdrawals = [
    bk.structures.Transaction(
        hot_wallet, bk.structures.address(bk.crypto.public_key(100 + i)), rng.randint(1, 50), i
    ).signed(EXCHANGE_KEY, signing_nonce=10_000 + i)
    for i in range(200)
]
malleated = set(rng.sample(range(200), 12))
confirmed = [
    tx.signed(EXCHANGE_KEY, signing_nonce=90_000 + i) if i in malleated else tx
    for i, tx in enumerate(withdrawals)
]
assert all(tx.is_valid() for tx in confirmed)

by_txid = bk.fraud.reissue_missing(withdrawals, confirmed, by="txid")
by_payment = bk.fraud.reissue_missing(withdrawals, confirmed, by="unsigned_id")
lost = sum(tx.amount for tx in by_txid)
print(f"tracking by txid: {len(by_txid)} withdrawals paid twice, {lost} coins lost")
print("tracking by unsigned id:", len(by_payment), "paid twice")
assert len(by_txid) == len(malleated) and by_payment == ()

# %%
# What malleability could explain
# -------------------------------

fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(
    ["missing at Mt. Gox", "malleability attacks\n(Decker and Wattenhofer)"],
    [850_000, 386],
    color=["#dc2626", "#2563eb"],
)
ax.set_yscale("log")
ax.set_ylabel("bitcoins")
ax.set_title("The excuse covers about 0.05% of the loss")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Suppose the exchange waits for a customer to complain before re-sending,
# and a fraction :math:`c` of customers whose withdrawal was malleated
# complain falsely. Write the expected loss for :math:`n` withdrawals of
# mean size :math:`a`, a fraction :math:`m` of them malleated.
