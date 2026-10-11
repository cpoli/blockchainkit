r"""
Zerocash: notes, nullifiers and private payments (2014)
=======================================================

Bitcoin's ledger shows who paid whom and how much. Ben-Sasson, Chiesa,
Garman, Green, Miers, Tromer and Virza hid all three. A coin is a *note*,
and the ledger stores only its commitment, in a Merkle tree. Spending a
note publishes its *nullifier* :math:`\mathrm{nf} = H(\mathit{sk}, \rho)`, a
commitment to the payee's new note, and a zk-SNARK of the statement

.. math::

   \exists\, \text{note}, \mathit{sk}, \text{path}:\;
   \mathrm{Commit}(\text{note}) \in \text{tree}(\mathit{root}),\;
   \text{owner} = H(\mathit{sk}, 0),\;
   \mathrm{nf} = H(\mathit{sk}, \rho),\;
   v_\text{in} = v_\text{out} + v_\text{public}.

The ledger records the nullifier to stop double spending, but cannot tell
which commitment it belongs to. Zcash launched on this design in 2016.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Alice pays Bob, privately
# -------------------------

key = bk.proofs.spend_setup(3, bk.proofs.Groth16Trapdoor(5, 6, 7, 8, 9))
pool = bk.proofs.ShieldedPool(3, key.verifying_key)
alice, bob = 1111, 2222
coin = bk.proofs.Note(bk.proofs.owner_key(alice), 100, rho=1, randomness=77)
pool.mint(coin)  # Depositing reveals the amount, not the owner.
pool.mint(bk.proofs.Note(bk.proofs.owner_key(3333), 50, rho=9, randomness=5))  # Someone else's.

payment = bk.proofs.Note(bk.proofs.owner_key(bob), 70, rho=2, randomness=88)
spend = bk.proofs.prove_spend(key, pool, alice, coin, 0, payment, public_value=30, seed=1)
pool.spend(spend)
print("the ledger sees commitments", [c % 10**6 for c in pool.commitments], "...")
print("and one nullifier", spend.nullifier, "linked to none of them")
assert pool.supply == 120 and spend.nullifier not in pool.commitments

# %%
# Double spends, theft and inflation fail
# ---------------------------------------

try:
    pool.spend(spend)
except ValueError as error:
    print("replaying the spend:", error)
for label, secret, new_note, public in (
    ("Mallory spends Bob's note", 4444, bk.proofs.Note(bk.proofs.owner_key(4444), 70, 3, 1), 0),
    (
        "Bob mints a 'negative' note",
        bob,
        bk.proofs.Note(bk.proofs.owner_key(bob), bk.proofs.FIELD_PRIME - 1000, 3, 1),
        1070,
    ),
):
    try:
        bk.proofs.prove_spend(key, pool, secret, payment, 2, new_note, public)
        raise AssertionError("a false statement was proved")
    except ValueError:
        print(label + ": no proof exists")

# %%
# What the circuit costs
# ----------------------
# Each MiMC hash is 48 constraints; the Merkle path adds one hash per level.

depths = range(1, 9)
dummy = bk.proofs.Note(0, 0, 0, 0)
sizes = [
    bk.proofs.spend_circuit(d, 0, dummy, [0] * d, 0, dummy, 0).r1cs().num_constraints
    for d in depths
]
print("constraints by tree depth:", sizes)
assert sizes[1] - sizes[0] == 48 + 2

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.bar(depths, sizes, color="#2563eb")
ax.set(xlabel="Merkle tree depth (log2 of the number of notes)", ylabel="R1CS constraints")
ax.set_title("The spend statement grows by one hash per level")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Bob's "negative" note balances modulo p. Build its spend circuit with
# ``spend_circuit`` and find which constraint the witness violates. Without
# that constraint, how many coins would the spend create?
# A worked solution is in :doc:`/exercises/proofs`.
