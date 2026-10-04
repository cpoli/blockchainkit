"""
Double-entry bookkeeping: value is moved, never created (Pacioli 1494)
======================================================================

Luca Pacioli's *Summa de arithmetica* gave the first printed account of
Venetian double-entry bookkeeping: every transaction is recorded twice, as a
debit in one account and a credit in another, so the books always balance.
A blockchain ledger enforces the same invariant mechanically: transfers move
value between accounts, so the total supply never changes.

What to look for
----------------

Thousands of random transfers leave the total supply exactly where it
started. A transfer that would overdraw an account is rejected as a whole,
and the ledger is left untouched: no half-recorded entries.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Random transfers among five accounts
# ------------------------------------
from contextlib import suppress
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

keys = [3, 5, 7, 11, 13]
publics = [bk.crypto.public_key(k) for k in keys]
accounts = [bk.structures.address(p) for p in publics]
ledger = bk.structures.Ledger({a: 100 for a in accounts})
rng = Random(1494)
supply, balances = [ledger.total_supply], [[ledger.balances[a] for a in accounts]]
for _ in range(300):
    i, j = rng.sample(range(5), 2)
    amount = rng.randint(1, 20)
    tx = bk.structures.Transaction(
        publics[i], accounts[j], amount, ledger.nonces.get(accounts[i], 0)
    )
    tx = tx.signed(keys[i], signing_nonce=bk.crypto.deterministic_nonce(keys[i], tx.payload()))
    with suppress(ValueError):  # Insufficient funds: rejected whole.
        ledger = ledger.apply([tx])
    supply.append(ledger.total_supply)
    balances.append([ledger.balances.get(a, 0) for a in accounts])
assert set(supply) == {500}
print(ledger)

# %%
# A failed batch changes nothing
# ------------------------------
richest = max(range(5), key=lambda k: ledger.balances[accounts[k]])
nonce = ledger.nonces.get(accounts[richest], 0)
ok = bk.structures.Transaction(publics[richest], accounts[0], 1, nonce).signed(
    keys[richest], signing_nonce=1
)
overdraw = bk.structures.Transaction(publics[richest], accounts[0], 10_000, nonce + 1).signed(
    keys[richest], signing_nonce=2
)
before = dict(ledger.balances)
try:
    ledger.apply([ok, overdraw])
except ValueError as error:
    print("Rejected:", error)
assert dict(ledger.balances) == before  # Even the valid first transfer was not recorded.

# %%
fig, ax = plt.subplots(figsize=(8, 4))
ax.stackplot(
    range(len(balances)),
    list(zip(*balances, strict=True)),
    labels=[f"account {k}" for k in range(5)],
)
ax.plot(supply, color="black", linewidth=2, label="total supply")
ax.set(xlabel="transfer attempt", ylabel="balance", title="Balances move; their sum does not")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()

# %%
# Exercise
# --------
# Bitcoin creates new coins in each block's coinbase transaction. Where would
# that break this example's invariant, and what rule replaces it ("supply
# grows exactly by the block reward")?
