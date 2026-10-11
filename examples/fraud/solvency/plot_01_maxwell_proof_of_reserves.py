r"""
Maxwell's Merkle-sum-tree proof of reserves (2013)
==================================================

An exchange can show that it holds coins by moving them, but holding
coins proves nothing unless one also knows what it owes. Gregory Maxwell
proposed in 2013 that the exchange publish the root of a Merkle tree over
its customers' balances in which every node also carries the sum below it,

.. math::

   \text{node} = \big(H(s_L \,\|\, s_R \,\|\, h_L \,\|\, h_R),\; s_L + s_R\big),

so that the root commits to the total liabilities. Each customer checks a
short proof that its own balance is counted, and the public checks that the
reserves cover the root's total. Leaving out customers lowers the total,
but each one left out may notice: if every customer checks independently
with probability :math:`f`, cheating :math:`k` of them goes unnoticed with
probability :math:`(1 - f)^k`.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Publish, prove, verify
# ----------------------

owed = {f"customer{i:03}": 10 + 37 * i % 500 for i in range(200)}
tree = bk.fraud.liability_tree(owed, salt=b"2013-snapshot")
print(tree, "root", tree.root.hex()[:16])
index = tree.index("customer042")
proof = tree.proof(index)
print("customer042's proof has", len(proof.steps), "siblings, each with its sum")
assert bk.fraud.verify_sum_proof(
    "customer042", owed["customer042"], proof, tree.root, tree.total, salt=tree.salt
)
assert tree.total == sum(owed.values())

# %%
# Hiding liabilities
# ------------------
# The exchange leaves out its ten largest customers, hiding a tenth of what
# it owes. Only those ten can notice.

largest = sorted(owed, key=owed.get)[-10:]
cheat = bk.fraud.liability_tree(
    {c: v for c, v in owed.items() if c not in largest}, salt=b"2013-snapshot"
)
print(f"declared {cheat.total:,} instead of {tree.total:,}")
result = bk.fraud.audit(cheat, owed, checking=0.1, seed=1)
print("customers who checked:", len(result.checked), "complaints:", result.complaints)

fractions = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]
caught = [
    sum(bk.fraud.audit(cheat, owed, checking=f, seed=s).caught for s in range(200)) / 200
    for f in fractions
]
predicted = [bk.fraud.detection_probability(10, f) for f in fractions]
assert all(abs(c - p) < 0.12 for c, p in zip(caught, predicted, strict=True))

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(fractions, caught, "o", color="#dc2626", label="simulated audits")
ax.plot(fractions, predicted, color="black", label="1 - (1 - f)^10")
ax.set(xlabel="fraction f of customers who check", ylabel="chance the cheat is caught")
ax.set_title("Ten customers left out")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Instead of leaving customers out, the exchange adds a fake account with a
# balance of minus 5,000. Which customers can notice, and why does
# :func:`~blockchainkit.fraud.utils.merkle_sum.verify_sum_proof` reject
# negative sibling sums?
# A worked solution is in :doc:`/exercises/fraud`.
