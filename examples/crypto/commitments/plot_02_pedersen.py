"""
Pedersen commitments: perfectly hiding and additive (1991)
==========================================================

Pedersen committed to a value v as C = g**v * h**r, with a random blinding
factor r and a second generator h whose logarithm nobody knows. For any
other value there is a blinding factor giving the same C, so the commitment
hides v perfectly; opening it to a different value would reveal log_g(h).
And commitments multiply to a commitment of the sum.

What to look for
----------------

Two commitments multiply into a commitment to the total, without anyone
seeing the amounts. This homomorphism is how confidential transactions
(Monero, Mimblewimble) let anyone check that inputs equal outputs.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Commit and add
# --------------
import matplotlib.pyplot as plt

import blockchainkit as bk

G = bk.crypto.TEACHING_GROUP
g, h = bk.crypto.pedersen_generators(G)
inputs = [(40, 1111), (2, 2222)]  # (amount, blinding factor)
outputs = [(30, 1500), (12, 1833)]
c_in = [bk.crypto.pedersen_commit(v, r) for v, r in inputs]
c_out = [bk.crypto.pedersen_commit(v, r) for v, r in outputs]
balance_in = c_in[0] * c_in[1] % G.p
balance_out = c_out[0] * c_out[1] % G.p
assert balance_in == balance_out  # 40 + 2 == 30 + 12, blindings also balance.
print("Inputs and outputs balance without revealing any amount")

# %%
# Perfect hiding in a group small enough to search
# ------------------------------------------------
small = bk.crypto.DHGroup(1019, 509, 4)
target = bk.crypto.pedersen_commit(7, 100, small)
for value in (7, 8, 500):
    blinding = next(
        r for r in range(small.q) if bk.crypto.pedersen_commit(value, r, small) == target
    )
    print(f"the same commitment opens as value {value} with blinding {blinding}")

# %%
# Commitments look uniform whatever the value
# -------------------------------------------
from random import Random

rng = Random(1991)
zeros = [bk.crypto.pedersen_commit(0, rng.randrange(small.q), small) for _ in range(2000)]
hundreds = [bk.crypto.pedersen_commit(100, rng.randrange(small.q), small) for _ in range(2000)]
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.hist([zeros, hundreds], bins=20, label=["commit(0, r)", "commit(100, r)"])
ax.set(xlabel="commitment value", ylabel="count", title="Random blinding hides the amount")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Suppose a dishonest committer knew x = log_g(h). Show how they could open
# C = g**v * h**r as any other value v' by choosing r'. Why must h be
# derived by hashing rather than chosen by a participant?
