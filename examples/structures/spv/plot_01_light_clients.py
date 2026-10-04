"""
Simplified payment verification: light clients (Nakamoto 2008)
==============================================================

Section 8 of the Bitcoin whitepaper describes a client that never downloads
blocks. It keeps only the chain of block headers, checks that they link and
carry proof of work, and asks a full node for a Merkle proof that a payment
is in one of them. Phones run wallets this way.

What to look for
----------------

The client verifies 20 headers and one inclusion proof: a few kilobytes
instead of every transaction. What it gives up is visible too: it trusts
that the heaviest header chain is valid, without checking the transactions
inside.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# A full node mines 20 blocks of payments
# ---------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

alice_key = 7
alice = bk.crypto.public_key(alice_key)
bob = bk.structures.address(bk.crypto.public_key(11))
genesis = bk.consensus.mine(bk.structures.Block(difficulty=6)).block
blocks, nonce = [genesis], 0
for height in range(1, 20):
    payments = []
    for _ in range(8):
        tx = bk.structures.Transaction(alice, bob, 1, nonce)
        payments.append(
            tx.signed(
                alice_key, signing_nonce=bk.crypto.deterministic_nonce(alice_key, tx.payload())
            )
        )
        nonce += 1
    block = bk.structures.Block(blocks[-1].hash, tuple(payments), height, height, 6)
    blocks.append(bk.consensus.mine(block).block)

# %%
# The light client checks headers and one proof
# ---------------------------------------------
headers = [block.to_header() for block in blocks]
work = bk.structures.verify_header_chain(headers)
target_block = blocks[13]
payment = target_block.transactions[5]
tree = bk.structures.MerkleTree(tx.to_bytes() for tx in target_block.transactions)
proof = tree.proof(5)
assert bk.structures.verify_proof(payment.to_bytes(), proof, headers[13].merkle_root)
print(f"verified payment in block 13 under {work} units of work")

# %%
# Bytes a light client downloads, against a full node
# ---------------------------------------------------
header_bytes = sum(len(h.encode()) for h in headers)
proof_bytes = 32 * sum(s is not None for s in proof.siblings)
full_bytes = sum(len(b.header()) + sum(len(tx.to_bytes()) for tx in b.transactions) for b in blocks)
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.barh(
    ["full node", "light client"],
    [full_bytes, header_bytes + proof_bytes],
    color=["#64748b", "#2563eb"],
)
ax.set(xlabel="bytes downloaded", title="Headers and a Merkle proof instead of every block")
fig.tight_layout()

# %%
# Exercise
# --------
# A light client accepts the heaviest header chain. Describe a block whose
# header is valid but whose transactions are not. Why can't the client
# notice, and why does honest-majority mining make that unlikely to last?
