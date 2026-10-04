"""
A signed payment, a network fork, and a ledger reorganization
=============================================================

This is the full teaching chain: keys authorize a transfer, a Merkle root
commits to it, proof of work secures a header, and peers compare valid forks.
The example uses an account ledger, not Bitcoin's UTXO model.

What to look for
----------------

Follow Alice and Bob’s balances after a payment, then after a competing branch wins. The
old payment’s signature can still verify even though its effect disappears from the
selected ledger.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

See :doc:`/tutorials/course` for prerequisites and :doc:`/tutorials/solutions` for worked answers.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

alice_private, bob_private = 7, 11
alice = bk.structures.address(bk.crypto.public_key(alice_private))
bob = bk.structures.address(bk.crypto.public_key(bob_private))
initial = bk.structures.Ledger({alice: 100})
genesis = bk.consensus.mine(bk.structures.Block(difficulty=5)).block
peers = {name: bk.structures.Blockchain(genesis, initial) for name in ("west", "east")}
transaction = bk.structures.Transaction(bk.crypto.public_key(alice_private), bob, 25, 0).signed(
    alice_private, signing_nonce=17
)
payment_block = bk.consensus.mine(bk.structures.Block(genesis.hash, (transaction,), 1, 1, 5)).block

# %%
# Two partitions extend the same genesis independently
# ----------------------------------------------------
# Transport sends hash announcements; this in-memory registry supplies the
# corresponding immutable block objects. It is not a wire serialization layer.
alternate = bk.consensus.mine(bk.structures.Block(genesis.hash, (), 1, 2, 5)).block
extension = bk.consensus.mine(bk.structures.Block(alternate.hash, (), 2, 3, 5)).block
registry = {block.hash: block for block in (payment_block, alternate, extension)}


def receive(delivery):
    peers[delivery.recipient].add(registry[delivery.payload])


network = bk.network.SimulatedNetwork(peers, on_receive=receive)
network.broadcast("west", payment_block.hash)
network.broadcast("east", alternate.hash)
network.broadcast("east", extension.hash)
before = [peers[name].state.balances.get(bob, 0) for name in peers]
assert before == [25, 0]

# %%
# Reconnect and synchronize parent before child
# ---------------------------------------------
network.connect("west", "east")
network.broadcast("west", payment_block.hash)
network.broadcast("east", alternate.hash)
network.run()
network.broadcast("east", extension.hash)
network.run()
assert peers["west"].tip == peers["east"].tip == extension
after = [peers[name].state.balances.get(bob, 0) for name in peers]
assert after == [0, 0]
assert peers["west"].state.nonces.get(alice, 0) == 0
print("Both peers chose the higher-work fork. Alice's payment is no longer confirmed.")

# %%
# Inclusion remains true for the discarded block
# ----------------------------------------------
tree = bk.structures.MerkleTree(tx.to_bytes() for tx in payment_block.transactions)
assert bk.structures.verify_proof(transaction.to_bytes(), tree.proof(0), payment_block.merkle_root)
print("The payment still has an inclusion proof in its original side-fork block.")

# %%
fig, ax = plt.subplots(figsize=(7, 4))
xs = [0, 1]
ax.bar([x - 0.18 for x in xs], before, 0.36, label="During partition")
ax.bar([x + 0.18 for x in xs], after, 0.36, label="After synchronization")
ax.set(
    xticks=xs,
    xticklabels=list(peers),
    ylabel="Bob's canonical balance",
    title="A valid signature does not guarantee finality",
    ylim=(0, 30),
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Reinclude the payment on the winning fork, then attempt to replay it. Check
# that its first inclusion succeeds and its second fails on the account nonce.
# Change the chain ID and explain why the existing signature no longer works.
