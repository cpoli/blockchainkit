"""
One payment from signature to reorganization and reinclusion
============================================================

Prerequisites: the quick start, gossip, and the fork experiment.
By the end you should distinguish a signed, pending, included, and displaced
payment. A pending queue (often called a mempool) is local to each peer.

What to look for
----------------

Bob's balance goes from 0 to 25, back to 0 after a competing history wins,
and finally to 25 after reinclusion. Queueing a payment never changes balances.
A signature remains valid throughout. Read the event table from top to bottom.

This deliberately small scenario has one pending payment per peer. It has no
fees or queue replacement policy. Hash announcements resolve through a shared
in-memory object registry; synchronization explicitly sends parents first.

This capstone ties the subpackages together; :doc:`/tutorials/life_of_a_payment` tells
the same story step by step. See :doc:`/exercises/structures` for a worked solution to the exercise.
"""

# %%
# Sign and validate before queueing
# ---------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

alice_key = 7
alice_public = bk.crypto.public_key(alice_key)
alice = bk.structures.address(alice_public)
bob = bk.structures.address(bk.crypto.public_key(11))
initial = bk.structures.Ledger({alice: 100})
genesis = bk.consensus.mine(bk.structures.Block(difficulty=4)).block
peers = {name: bk.structures.Blockchain(genesis, initial) for name in ("west", "east")}
queues = {name: {} for name in peers}
payment = bk.structures.Transaction(alice_public, bob, 25, 0).signed(alice_key, signing_nonce=17)
assert payment.is_valid()
# apply returns a new snapshot. Discarding it checks validity without spending.
assert initial.apply([payment]).balances[bob] == 25
assert initial.balances.get(bob, 0) == 0
registry = {payment.txid: payment}
events = []


def record(stage):
    events.append(
        [
            stage,
            *[peers[n].state.balances.get(bob, 0) for n in peers],
            *[len(queues[n]) for n in peers],
        ]
    )


def receive(delivery):
    item = registry[delivery.payload]
    peer = peers[delivery.recipient]
    if isinstance(item, bk.structures.Transaction):
        peer.state.apply([item])
        queues[delivery.recipient][item.txid] = item
    else:
        peer.add(item)
        # Reconcile our one-payment queue against the new canonical state.
        # After a reorganization an old payment may become eligible again.
        try:
            peer.state.apply([payment])
        except ValueError:
            queues[delivery.recipient].pop(payment.txid, None)
        else:
            queues[delivery.recipient][payment.txid] = payment


network = bk.network.SimulatedNetwork(peers, on_receive=receive)
network.connect("west", "east", latency=(2, 2))
network.broadcast("west", payment.txid)
record("Queued at west")
assert len(queues["west"]) == 1 and not queues["east"]
network.run()
record("Payment propagated")
assert all(len(queue) == 1 for queue in queues.values())
assert all(peer.state.balances.get(bob, 0) == 0 for peer in peers.values())

# %%
# Partition and mine competing histories
# --------------------------------------
network.disconnect("west", "east")
paid = bk.consensus.mine(
    bk.structures.Block(genesis.hash, tuple(queues["west"].values()), 1, 3, 4)
).block
alternate = bk.consensus.mine(bk.structures.Block(genesis.hash, (), 1, 4, 4)).block
extension = bk.consensus.mine(bk.structures.Block(alternate.hash, (), 2, 5, 4)).block
for block, sender in [(paid, "west"), (alternate, "east"), (extension, "east")]:
    registry[block.hash] = block
    network.broadcast(sender, block.hash)
record("Partition: west includes payment")
assert peers["west"].state.balances[bob] == 25
assert not queues["west"] and len(queues["east"]) == 1

# %%
# Reconnect, synchronize, and restore a displaced payment
# -------------------------------------------------------
network.connect("west", "east")
network.broadcast("east", alternate.hash)
network.run()
network.broadcast("east", extension.hash)
network.run()
record("Longer fork wins; payment pending")
assert peers["west"].tip == peers["east"].tip == extension
assert all(peer.state.balances.get(bob, 0) == 0 for peer in peers.values())
assert all(payment.txid in queue for queue in queues.values())
proof = bk.structures.MerkleTree([payment.to_bytes()]).proof(0)
assert bk.structures.verify_proof(payment.to_bytes(), proof, paid.merkle_root)
assert payment.is_valid()

# %%
# Reinclude once; reject replay
# -----------------------------
reincluded = bk.consensus.mine(
    bk.structures.Block(extension.hash, tuple(queues["west"].values()), 3, 6, 4)
).block
registry[reincluded.hash] = reincluded
network.broadcast("west", reincluded.hash)
network.run()
record("Reincluded on winning history")
assert all(peer.state.balances[bob] == 25 for peer in peers.values())
assert all(not queue for queue in queues.values())
for peer in peers.values():
    try:
        peer.state.apply([payment])
    except ValueError as error:
        assert "nonce" in str(error)
    else:
        raise AssertionError("replay must be rejected")

# %%
# Read the lifecycle as a balance and queue trace
# -----------------------------------------------
fig, (ax, table_ax) = plt.subplots(2, 1, figsize=(11, 7), height_ratios=[1, 1.2])
for column, peer in [(1, "west"), (2, "east")]:
    ax.step(range(len(events)), [row[column] for row in events], where="post", label=peer)
ax.set(xticks=range(len(events)), xlabel="Stage number (table order)", ylabel="Bob's balance")
ax.legend()
table_ax.axis("off")
table = table_ax.table(
    cellText=events,
    colLabels=["Stage", "West balance", "East balance", "West queue", "East queue"],
    colWidths=[0.48, 0.13, 0.13, 0.13, 0.13],
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2)
fig.suptitle("Signed does not mean pending; included does not mean final")
fig.tight_layout()
for event in events:
    print(event)

# %%
# Exercise
# --------
# Replace an empty competing block with a conflicting payment that spends all
# of Alice's funds. Predict whether the original payment returns to the queue.
# Explain why the single-payment queue is insufficient for dependent payments
# with consecutive account nonces.
