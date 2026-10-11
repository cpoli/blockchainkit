r"""
Provisions: privacy-preserving proofs of solvency (2015)
========================================================

Maxwell's proof reveals the exchange's total liabilities and, to show its
reserves, which addresses it owns. Dagher, Bünz, Bonneau, Clark and Boneh
hid both with Pedersen commitments :math:`C(v, r) = g^v h^r`, which
multiply into a commitment to the sum. The exchange commits, for every
address in a large public set, to that address's balance if it owns it and
to 0 if not; it commits to every customer's balance; and

.. math::

   \frac{\prod_i C(s_i b_i, r_i)}{\prod_j C(\ell_j, t_j)}
   = C\Big(\sum_i s_i b_i - \sum_j \ell_j,\; \sum_i r_i - \sum_j t_j\Big)

commits to its surplus. Zero-knowledge proofs show that each asset
commitment holds 0 or the public balance, that each liability and the
surplus are not negative, and nothing else: not the total, not which
addresses, not any balance. Each customer, given its blinding factor,
checks that its own balance is among the commitments.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A solvent exchange proves it
# ----------------------------

# Balances of twelve public addresses, four of them the exchange's.
anonymity_set = [820, 40, 1_500, 310, 975, 60, 1_210, 400, 15, 1_830, 700, 95]
owned = {2, 6, 9, 10}
customers = [480, 1_200, 75, 960, 330, 610, 1_025, 290]
prover = bk.fraud.SolvencyProver(anonymity_set, owned, customers, seed=1)
print(f"assets {prover.assets}, liabilities {sum(customers)}, surplus {prover.surplus}")
proof = prover.prove()
assert bk.fraud.verify_solvency(anonymity_set, proof)
assert bk.fraud.verify_liability(proof.liability_commitments[3], customers[3], prover.blinding(3))
print("each liability proof commits to", proof.liability_proofs[0].bits, "bits")

# %%
# What the proof does not let the exchange do
# -------------------------------------------
# Selling a large address leaves it insolvent: no surplus proof exists.
# Dropping a customer from the list breaks the arithmetic, and that customer
# finds its commitment missing.

poorer = bk.fraud.SolvencyProver(anonymity_set, {2, 6, 9}, customers, seed=1)
try:
    poorer.prove()
except ValueError as error:
    print("insolvent exchange:", error)
hidden = bk.fraud.SolvencyProof(
    proof.asset_commitments,
    proof.asset_proofs,
    proof.liability_commitments[1:],
    proof.liability_proofs[1:],
    proof.surplus_proof,
)
assert not bk.fraud.verify_solvency(anonymity_set, hidden)

# %%
# Commitments reveal nothing
# --------------------------
# Commitments to an owned address's balance and to 0 look alike.

owned_c = [c for i, c in enumerate(proof.asset_commitments) if i in owned]
other_c = [c for i, c in enumerate(proof.asset_commitments) if i not in owned]
p = bk.crypto.TEACHING_GROUP.p
fig, ax = plt.subplots(figsize=(7, 3))
ax.scatter([c / p for c in owned_c], [1] * len(owned_c), color="#16a34a", label="owned")
ax.scatter([c / p for c in other_c], [0] * len(other_c), color="#64748b", label="not owned")
ax.set(xlabel="commitment / p", yticks=[0, 1], yticklabels=["not owned", "owned"], xlim=(0, 1))
ax.set_title("Which addresses the exchange owns is hidden")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Two exchanges could each claim the same address in their own proofs.
# Why can't customers of either exchange detect it, and what did Provisions
# add to rule it out?
# A worked solution is in :doc:`/exercises/fraud`.
