"""
Replay protection with a chain identifier (EIP-155, 2016)
=========================================================

In 2016 Ethereum split into two chains, Ethereum and Ethereum Classic, with
the same accounts and keys. A transaction signed for one was valid on the
other: anyone could replay it, moving the sender's coins on both. EIP-155
added the chain id to what is signed, so a signature belongs to exactly one
network.

What to look for
----------------

A payment signed for one chain is rejected by a ledger with a different
chain id, while an account nonce still prevents replay within one chain.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Two networks, same keys, same balances
# --------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

alice_key = 7
alice_pub = bk.crypto.public_key(alice_key)
alice = bk.structures.address(alice_pub)
bob = bk.structures.address(bk.crypto.public_key(11))
mainnet = bk.structures.Ledger({alice: 100}, chain_id="mainnet")
fork = bk.structures.Ledger({alice: 100}, chain_id="classic")

tx = bk.structures.Transaction(alice_pub, bob, 40, 0, chain_id="mainnet").signed(
    alice_key, signing_nonce=5
)
mainnet = mainnet.apply([tx])
try:
    fork.apply([tx])
except ValueError as error:
    print("Replay on the other chain rejected:", error)
assert fork.balances[alice] == 100

# %%
# The chain id is part of the signed bytes
# ----------------------------------------
assert b'"chain_id":"mainnet"' in tx.payload()
results = {}
for label, ledger in (
    ("same chain, new", bk.structures.Ledger({alice: 100}, chain_id="mainnet")),
    ("same chain, replay", mainnet),
    ("other chain", fork),
):
    try:
        ledger.apply([tx])
        results[label] = True
    except ValueError:
        results[label] = False
assert results == {"same chain, new": True, "same chain, replay": False, "other chain": False}

fig, ax = plt.subplots(figsize=(7, 3))
ax.bar(results.keys(), [int(v) for v in results.values()], color=["#16a34a", "#dc2626", "#dc2626"])
ax.set(
    ylabel="accepted", yticks=[0, 1], title="Nonce stops replay in time; chain id across networks"
)
fig.tight_layout()

# %%
# Exercise
# --------
# Before EIP-155, how could a cautious user split their coins safely after
# the fork? (Hint: make a transaction that is valid on only one chain.)
