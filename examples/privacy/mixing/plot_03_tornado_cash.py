r"""
Tornado Cash: a mixer contract with zero-knowledge withdrawals (2019)
=====================================================================

Tornado Cash put Zerocash's notes and nullifiers into an Ethereum
contract. Each deposit is a fixed amount with the commitment to a secret
note, appended to a Merkle tree. A withdrawal, from any address, reveals
the note's nullifier and a zk-SNARK that the note is a leaf under a recent
root. The contract pays once per nullifier and never learns which leaf.

The proof protects the link; behaviour can give it away. A withdrawal's
anonymity set is the deposits that could be its source,

.. math::

   |S_w| = \#\{\text{deposits before } w\} - \#\{\text{withdrawals before } w\},

and it collapses to one when someone withdraws to the address it
deposited from. The US Treasury sanctioned the contracts in August 2022.
"""

# %%
import dataclasses
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.privacy.visualizers import plot_anonymity_sets
from blockchainkit.proofs import Groth16Trapdoor, Note, note_commitment, owner_key, spend_setup

# %%
# Deposits and a withdrawal
# -------------------------

key = spend_setup(3, Groth16Trapdoor(5, 6, 7, 8, 9))
world = bk.contracts.World()
mixer = world.deploy("deployer", bk.privacy.Mixer, 100, 3, key.verifying_key, name="mixer")
notes = []
for i in range(5):
    world.fund(f"user{i}", 1_000)
    note = Note(owner_key(700 + i), 100, rho=i + 1, randomness=4_000 + i)
    notes.append(note)
    assert world.transact(f"user{i}", mixer, "deposit", note_commitment(note), value=100).success
deposits = world.view(mixer, "deposits")
withdrawal = bk.privacy.prove_withdrawal(key, deposits, 3, 702, notes[2], "fresh-address")

# A front-runner copies the proof but names itself: the proof is bound to the recipient.
stolen = dataclasses.replace(withdrawal, recipient="front-runner")
print("redirected:", world.transact("front-runner", mixer, "withdraw", stolen).error)
receipt = world.transact("relayer", mixer, "withdraw", withdrawal)
assert receipt.success and world.balance("fresh-address") == 100
print("paid:", world.balance("fresh-address"), "| mixer holds:", world.balance(mixer))
print("replayed:", world.transact("relayer", mixer, "withdraw", withdrawal).error)

# %%
# Anonymity sets over a day of use
# --------------------------------
# Forty users; a few careless ones withdraw to their own address.

rng = Random(3)
deposit_log, withdrawal_log = [], []
for i in range(40):
    block = rng.randrange(0, 200)
    deposit_log.append((f"user{i}", block))
    out = f"user{i}" if rng.random() < 0.15 else f"fresh{i}"
    withdrawal_log.append((out, block + rng.randrange(1, 60)))
withdrawal_log.sort(key=lambda entry: entry[1])
report = bk.privacy.mixer_report(deposit_log, withdrawal_log)
print(f"{len(report.address_links)} withdrawals linked by address reuse")
assert report.address_links and min(report.anonymity_sets) >= 1

fig, ax = plt.subplots(figsize=(7, 4))
plot_anonymity_sets(report.anonymity_sets, ax=ax)
for _, j in report.address_links:
    ax.scatter(j + 1, 1, color="#dc2626", marker="x")
ax.set_title("Anonymity sets, and withdrawals given away by address reuse (x)")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The first withdrawal after a mixer is deployed has an anonymity set of
# however many deposits came before it. Why did Tornado's guides tell
# users to wait before withdrawing, and what does waiting cost?
# A worked solution is in :doc:`/exercises/privacy`.
