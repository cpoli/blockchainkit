"""
The account model and nonces (Ethereum 2014)
============================================

Ethereum replaced Bitcoin's coins with accounts: a balance per address, and a
*nonce* counting the transactions each account has sent. A transaction must
carry the next expected nonce, so it can be applied once and only in order.
Without it, anyone could replay a signed payment again and again.

What to look for
----------------

The same signed transfer is accepted once and rejected on replay. A transfer
with a skipped nonce waits until the gap is filled. Account balances make
wallets simple, at the cost of this global ordering per sender.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Replay is rejected by the nonce
# -------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

alice_key = 7
alice_pub = bk.crypto.public_key(alice_key)
alice = bk.structures.address(alice_pub)
bob = bk.structures.address(bk.crypto.public_key(11))
ledger = bk.structures.Ledger({alice: 100})


def pay(amount, nonce):
    tx = bk.structures.Transaction(alice_pub, bob, amount, nonce)
    return tx.signed(
        alice_key, signing_nonce=bk.crypto.deterministic_nonce(alice_key, tx.payload())
    )


first = pay(10, 0)
ledger = ledger.apply([first])
try:
    ledger.apply([first])
except ValueError as error:
    print("Replay rejected:", error)
assert ledger.balances[bob] == 10 and ledger.nonces[alice] == 1

# %%
# Out-of-order transactions wait for the gap
# ------------------------------------------
later = pay(5, 2)
try:
    ledger.apply([later])
except ValueError:
    print("Nonce 2 cannot run before nonce 1")
ledger = ledger.apply([pay(3, 1), later])
assert ledger.nonces[alice] == 3 and ledger.balances[bob] == 18

# %%
# Nonce and balance after each transfer
# -------------------------------------
history = [(0, 100)]
state = bk.structures.Ledger({alice: 100})
for nonce, amount in enumerate([10, 3, 5, 20, 7]):
    state = state.apply([pay(amount, nonce)])
    history.append((state.nonces[alice], state.balances[alice]))
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.step(*zip(*history, strict=True), where="post", marker="o")
ax.set(
    xlabel="Alice's account nonce", ylabel="Alice's balance", title="One nonce per transaction sent"
)
fig.tight_layout()

# %%
# Exercise
# --------
# The account nonce and the signing nonce are different ideas sharing a name.
# Which one is public and sequential, which one secret and random, and what
# goes wrong when each is reused?
