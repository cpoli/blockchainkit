r"""
Address poisoning with look-alike addresses (2022-2023)
=======================================================

An Ethereum address is 40 hexadecimal digits, and wallets show only the
first and last few. From late 2022, poisoners watched for payments, ground
out an address matching the payee's ends, and sent the payer a worthless
transfer from it, so that the look-alike appeared in the payer's history
right next to the real one. The next payment copied from the history went
to the poisoner; in May 2024 one victim sent 68 million dollars this way.
Tsuchiya, Dong, Soska and Christin measured millions of such attempts.
Matching :math:`k` digits takes about

.. math::

   \mathbb{E}[\text{trials}] = 16^{k}

tries, a few seconds of computing for the eight digits a hurried user
checks, and a detector needs only to compare new senders against the
addresses the victim has paid.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# The cost of a look-alike
# ------------------------

payee = bk.fraud.candidate_address(2023, 0)
digits, costs = [], []
for k in range(1, 5):
    prefix, suffix = (k + 1) // 2, k // 2
    found = [
        bk.fraud.grind_lookalike(payee, prefix=prefix, suffix=suffix, seed=s).trials
        for s in range(12 if k < 4 else 3)
    ]
    digits.append(k)
    costs.append(sum(found) / len(found))
    print(f"{k} digits: about {costs[-1]:,.0f} trials (16^{k} = {16**k:,})")
assert costs == sorted(costs)

fig, ax = plt.subplots(figsize=(6, 4))
ax.semilogy(digits, costs, "o", color="#dc2626", label="measured")
ax.semilogy(digits, [16**k for k in digits], color="black", label="16^k")
ax.set(xlabel="hex digits matched", ylabel="trials", xticks=digits)
ax.set_title("Each digit checked multiplies the work by 16")
ax.legend()
fig.tight_layout()

# %%
# Poisoning a history, and spotting it
# ------------------------------------

fake = bk.fraud.grind_lookalike(payee, prefix=2, suffix=2, seed=7).address
history = [
    bk.fraud.Flow("victim", payee, 25_000, 0),
    bk.fraud.Flow(fake, "victim", 0, 1),  # The poisoner's zero-value transfer.
]
print("payee:", payee)
print("fake: ", fake)
latest = history[-1].sender  # The address a hurried user copies.
assert bk.fraud.looks_alike(latest, payee, prefix=2, suffix=2)
suspects = bk.fraud.poisoning_suspects(history, "victim", prefix=2, suffix=2)
print("suspects:", suspects)
assert suspects == (fake,)

plt.show()

# %%
# Exercise
# --------
# A wallet shows six characters at each end. How long does a poisoner
# computing ten million addresses a second need to match all twelve?
# A worked solution is in :doc:`/exercises/fraud`.
