r"""
Trusted-setup ceremonies: Zcash's parameters and the powers of tau (2016)
=========================================================================

Pairing-based SNARKs need :math:`[\tau^i]G` for a :math:`\tau` that nobody
knows: whoever knows it can prove false statements. In October 2016 six
Zcash participants generated its parameters by multi-party computation, so
that the secret stayed unknown unless *all* of them colluded. Later
"powers of tau" ceremonies scaled this to thousands of participants. Each
one multiplies the current string by a secret :math:`s` and destroys it:

.. math::

   [\tau^i]G \;\mapsto\; [(\tau s)^i]G,

and publishes :math:`[s]G`, so that anyone can check with pairings that the
update is honest and builds on the previous string. One honest
participant is enough.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Five participants, each checked by everyone
# -------------------------------------------

secrets = [1789, 31337, 271828, 141421, 577215]
string = bk.proofs.start_ceremony(16)
checks = []
for s in secrets:
    step = bk.proofs.contribute(string, s)
    checks.append(bk.proofs.verify_contribution(string, step))
    string = step.srs
tau = 1
for s in secrets:
    tau = tau * s % bk.proofs.FIELD_PRIME
assert all(checks) and string == bk.proofs.trusted_setup(16, tau)
print("every contribution verified; tau is the product of five secrets")

# %%
# A participant who ignores the previous string is caught
# -------------------------------------------------------
# Mallory publishes a fresh string from a tau she knows, discarding the
# others' contributions.

fresh = bk.proofs.contribute(bk.proofs.start_ceremony(16), 42)
caught = not bk.proofs.verify_contribution(string, fresh)
assert caught

# %%
# Why tau must be destroyed
# -------------------------

f = [5, 0, 1]
commitment = bk.proofs.kzg_commit(f, string)
forged = bk.proofs.forge_opening(commitment, point=3, value=1_000_000, secret=tau, srs=string)
assert bk.proofs.kzg_verify(commitment, forged, string)  # f(3) is 14, yet "1,000,000" verifies.
print("with tau, the commitment to 5 + x**2 opens to", forged.value, "at x = 3")

fig, ax = plt.subplots(figsize=(7, 4))
names = [f"participant {i + 1}" for i in range(len(secrets))] + ["Mallory"]
results = checks + [not caught]
ax.barh(names, [1] * len(names), color=["#16a34a" if ok else "#dc2626" for ok in results])
for i, ok in enumerate(results):
    ax.text(0.5, i, "verified" if ok else "rejected", ha="center", va="center", color="white")
ax.set_xticks([])
ax.invert_yaxis()
ax.set_title("Pairing checks on each contribution")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The toy group has order about 2**31, so tau can be recovered from
# [tau]G by baby-step giant-step in about 2**16 steps. Write that search on
# the pairing curve and recover the ceremony's tau from ``string.powers[1]``.
