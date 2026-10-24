r"""
k-anonymity and anonymity sets: hiding among k (2002)
=====================================================

Latanya Sweeney showed that a ZIP code, a birth date and a sex single out
most Americans. A table is *k-anonymous* if every combination of these
*quasi-identifiers* appears at least :math:`k` times, so each person hides
among :math:`k`. Generalising values, a ZIP to its first three digits or a
date to a year, merges rows until :math:`k` is reached.

The same year, anonymity on networks was measured the same way: by the
*anonymity set* of possible senders. An attacker who finds some senders
likelier than others has less uncertainty than the set's size suggests,
so Serjantov and Danezis, and Díaz et al., counted

.. math::

   |S|_{\text{eff}} = 2^{H}, \qquad H = -\sum_i p_i \log_2 p_i ,

the number of equally likely senders that leave the same uncertainty.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Generalising a table
# --------------------

rng = Random(1997)
rows = [
    {
        "zip": f"021{rng.randrange(30, 40)}",
        "born": f"19{rng.randrange(50, 90)}-{rng.randrange(1, 13):02d}",
        "sex": rng.choice("FM"),
    }
    for _ in range(400)
]
quasi = ["zip", "born", "sex"]
steps = {
    "as released": rows,
    "ZIP to 4 digits": [{**r, "zip": r["zip"][:4]} for r in rows],
    "birth to year": [{**r, "zip": r["zip"][:4], "born": r["born"][:4]} for r in rows],
    "birth to decade": [{**r, "zip": r["zip"][:3], "born": r["born"][:3]} for r in rows],
}
ks = {name: bk.privacy.k_anonymity(table, quasi) for name, table in steps.items()}
unique = sum(1 for n in bk.privacy.equivalence_classes(rows, quasi).values() if n == 1)
print(f"{unique} of {len(rows)} rows are unique as released; k by step: {ks}")
assert ks["as released"] == 1 and ks["birth to decade"] > 1

# %%
# Size is not the whole story
# ---------------------------
# Ten possible senders, as the attacker's suspicion of one grows.

suspicion = [i / 20 for i in range(1, 20)]
effective = [bk.privacy.effective_anonymity_set([p] + [(1 - p) / 9] * 9) for p in suspicion]
assert abs(effective[1] - 10) < 1e-9

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
ax1.bar(list(ks), list(ks.values()), color="#2563eb")
ax1.set(ylabel="k", title="Generalising raises k")
ax1.tick_params(axis="x", labelrotation=20)
ax2.plot(suspicion, effective, color="#dc2626")
ax2.axhline(10, color="#64748b", linestyle="--", label="set size")
ax2.set(xlabel="probability of the likeliest sender", ylabel="effective anonymity set")
ax2.set_title("Ten senders, but not equally likely")
ax2.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A table is 5-anonymous, but in one class of five rows every patient has
# the same diagnosis. What does an attacker who knows a neighbour is in
# that class learn, and what property did Machanavajjhala et al. add?
# A worked solution is in :doc:`/exercises/privacy`.
