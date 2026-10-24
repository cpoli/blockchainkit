r"""
CryptoNote stealth addresses: a fresh key for every payment (2013)
==================================================================

A reused address links every payment it receives. CryptoNote let a payee
publish one address :math:`(A, B) = (g^a, g^b)` from which each payer
derives a fresh one-time key. The payer picks :math:`r`, publishes
:math:`R = g^r`, and pays to

.. math::

   P = g^{H(A^r)} B .

The payee recognises it by computing :math:`R^a = A^r`, and spends it with
:math:`x = H(R^a) + b`. The view key :math:`a` alone finds payments
without being able to spend them.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

G = bk.crypto.TEACHING_GROUP

# %%
# Payments to one address
# -----------------------

bob = bk.privacy.stealth_keys(view_secret=31_337, spend_secret=27_182)
others = [bk.privacy.stealth_keys(1_000 + i, 2_000 + i) for i in range(4)]
ledger = []
for k in range(12):
    payee = bob if k % 3 == 0 else others[k % 4]
    output = bk.privacy.stealth_payment(payee.view_public, payee.spend_public, 5_000 + k)
    ledger.append((payee is bob, output))

found = [o for _, o in ledger if bk.privacy.owns_output(o, bob.view_secret, bob.spend_public)]
assert found == [o for mine, o in ledger if mine]
print(f"bob's view key finds {len(found)} of {len(ledger)} outputs")
for output in found:
    x = bk.privacy.one_time_secret(output, bob.view_secret, bob.spend_secret)
    assert G.public(x) == output.one_time_key
assert len({o.one_time_key for o in found}) == len(found)

# %%
# What the ledger shows
# ---------------------
# Bob's outputs are scattered among the rest.

fig, ax = plt.subplots(figsize=(7, 3))
for k, (mine, output) in enumerate(ledger):
    ax.scatter(k, output.one_time_key / G.p, color="#16a34a" if mine else "#64748b")
ax.scatter([], [], color="#16a34a", label="paid to bob")
ax.scatter([], [], color="#64748b", label="paid to others")
ax.set(xlabel="output", ylabel="one-time key / p", ylim=(0, 1))
ax.set_title("One published address, unlinkable outputs")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Bob gives his view key to an auditor. What can the auditor learn about
# Bob's incoming and outgoing payments, and what can it not do?
# A worked solution is in :doc:`/exercises/privacy`.
