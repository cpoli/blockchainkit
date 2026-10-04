"""
Coins, not accounts: the unspent-output model (Nakamoto 2008)
=============================================================

Bitcoin keeps no balances. Value lives in coins, the outputs of earlier
transactions, each locked to an owner. A payment consumes whole coins as
inputs and creates new outputs: one to the payee, usually one back to the
payer as change. Whatever is not assigned to an output goes to the miner as
a fee. A coin can be spent once; a double spend is two transactions
consuming the same coin.

What to look for
----------------

Alice pays Bob 30 from a 50 coin: she gets 18 back as change and 2 goes to
fees. Spending the same coin again is rejected, because it is no longer in
the unspent set.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Spend a coin, receive change
# ----------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

alice_key, bob_key = 7, 11
alice = bk.structures.address(bk.crypto.public_key(alice_key))
bob = bk.structures.address(bk.crypto.public_key(bob_key))
utxos = bk.structures.UTXOSet.genesis({alice: 50})
(coin,) = utxos.coins_of(alice)
payment = bk.structures.UTXOTransaction((coin,), ((bob, 30), (alice, 18))).signed([alice_key])
after = utxos.apply(payment)
print(f"Bob {after.balance(bob)}, Alice {after.balance(alice)}, fee {payment.fee(utxos)}")
assert (after.balance(bob), after.balance(alice), payment.fee(utxos)) == (30, 18, 2)

# %%
# A coin cannot be spent twice
# ----------------------------
double_spend = bk.structures.UTXOTransaction((coin,), ((alice, 50),)).signed([alice_key])
try:
    after.apply(double_spend)
except ValueError as error:
    print("Rejected:", error)

# %%
# Bob combines coins
# ------------------
second = bk.structures.UTXOTransaction((after.coins_of(alice)[0],), ((bob, 18),)).signed(
    [alice_key]
)
after2 = after.apply(second)
merge = bk.structures.UTXOTransaction(after2.coins_of(bob), ((alice, 48),)).signed(
    [bob_key, bob_key]
)
final = after2.apply(merge)
assert final.balance(alice) == 48 and len(final) == 1

stages = {"genesis": utxos, "pay Bob": after, "change to Bob": after2, "Bob merges": final}
fig, ax = plt.subplots(figsize=(8, 3.5))
for row, state in enumerate(stages.values()):
    left = 0
    for outpoint in sorted(state.coins_of(alice) + state.coins_of(bob)):
        coin_ = state[outpoint]
        color = "#2563eb" if coin_.owner == alice else "#ea580c"
        ax.barh(row, coin_.amount, left=left, color=color, edgecolor="white")
        left += coin_.amount
ax.set(
    yticks=range(len(stages)),
    yticklabels=list(stages),
    xlabel="value (blue: Alice, orange: Bob)",
    title="Unspent coins after each transaction",
)
ax.invert_yaxis()
fig.tight_layout()

# %%
# Exercise
# --------
# In the UTXO model, how does a wallet compute "its balance"? Why can two
# transactions that spend different coins of the same owner be validated in
# parallel, while two account-model transfers from one sender cannot?
