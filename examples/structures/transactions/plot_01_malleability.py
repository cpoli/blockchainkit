"""
Transaction malleability and segregated witness (2014-2017)
===========================================================

Bitcoin's transaction id hashed the whole transaction, signatures included.
Anyone relaying a transaction could alter its signature encoding without
invalidating it, changing the id. In 2014 the Mt. Gox exchange blamed
malleability for lost withdrawals; Decker and Wattenhofer found it explained
only a small fraction. Segregated witness (2017) moved signatures out of
the id, which also made payment channels such as Lightning safe to build.

What to look for
----------------

The same payment, signed twice, has two txids: a child transaction that
named the first id would point at nothing. The unsigned id, like SegWit's
txid, is the same for every valid signature.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# One payment, two signatures, two txids
# --------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

alice_key = 7
payment = bk.structures.Transaction(
    bk.crypto.public_key(alice_key), bk.structures.address(bk.crypto.public_key(11)), 25, 0
)
first = payment.signed(alice_key, signing_nonce=1001)
second = payment.signed(alice_key, signing_nonce=2002)  # Same payment, re-signed.
assert first.is_valid() and second.is_valid()
assert first.txid != second.txid
assert first.unsigned_id == second.unsigned_id
print("txid:       ", first.txid.hex()[:16], "vs", second.txid.hex()[:16])
print("unsigned id:", first.unsigned_id.hex()[:16], "for both")

# %%
# A child that names its parent by txid breaks
# --------------------------------------------
child_refers_to = first.txid
confirmed = second  # A miner confirmed the re-signed version.
assert child_refers_to != confirmed.txid
assert first.unsigned_id == confirmed.unsigned_id  # A SegWit-style reference still works.

# %%
ids = {f"signature {n}": payment.signed(alice_key, signing_nonce=n) for n in (11, 22, 33, 44)}
fig, ax = plt.subplots(figsize=(8, 3))
for row, (label, tx) in enumerate(ids.items()):
    ax.text(0.02, row, label, va="center")
    ax.text(0.30, row, tx.txid.hex()[:20], va="center", family="monospace", color="#dc2626")
    ax.text(0.68, row, tx.unsigned_id.hex()[:20], va="center", family="monospace", color="#16a34a")
ax.text(0.30, len(ids), "txid (covers signature)", weight="bold")
ax.text(0.68, len(ids), "unsigned id (SegWit)", weight="bold")
ax.set(xlim=(0, 1), ylim=(-0.7, len(ids) + 0.5), title="Re-signing changes one id, not the other")
ax.axis("off")
ax.invert_yaxis()
fig.tight_layout()

# %%
# Exercise
# --------
# In Lightning, two parties pre-sign a refund transaction that spends a
# funding transaction before it is broadcast. Explain why the refund needs
# an id for its parent that cannot change.
