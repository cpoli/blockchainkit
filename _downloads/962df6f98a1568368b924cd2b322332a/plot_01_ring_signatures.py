r"""
Ring signatures: leaking a secret for a group (2001)
====================================================

Rivest, Shamir and Tauman titled their paper *How to Leak a Secret*: a
cabinet member wants to prove a leak comes from the cabinet without saying
who leaked it. A ring signature does that. The signer lists any public
keys, its own among them, and signs so that the signature checks against
the whole list but not against any one key.

The signature is a ring of challenges. Starting after the signer, each
member's challenge hashes the previous member's commitment,

.. math::

   c_{i+1} = H\big(m,\; g^{r_i} y_i^{c_i}\big),

with random responses :math:`r_i` for everyone else. The ring closes only
if the signer answers :math:`r_s = u - x_s c_s`, which needs its secret
key. A verifier recomputes the ring from :math:`c_0` and checks it closes.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

G = bk.crypto.TEACHING_GROUP

# %%
# A cabinet of five
# -----------------

secrets = [101, 202, 303, 404, 505]
cabinet = [G.public(x) for x in secrets]
leak = b"the budget will be cut by 10%"
signature = bk.privacy.ring_sign(leak, cabinet, 3, secrets[3], seed=1)
assert bk.privacy.ring_verify(leak, cabinet, signature)
assert not bk.privacy.ring_verify(b"the budget will grow", cabinet, signature)
print("first challenge:", signature.challenge)

# %%
# Every member's signature looks alike
# ------------------------------------
# The responses are uniform whoever signs, so no response stands out.

signatures = {
    signer: bk.privacy.ring_sign(leak, cabinet, signer, secrets[signer], seed=signer)
    for signer in range(5)
}
assert all(bk.privacy.ring_verify(leak, cabinet, s) for s in signatures.values())
responses = {signer: s.responses for signer, s in signatures.items()}

fig, ax = plt.subplots(figsize=(7, 3.5))
for signer, r in responses.items():
    ax.scatter(range(5), [x / G.q for x in r], label=f"signed by member {signer}")
ax.set(xlabel="ring member", ylabel="response / q", ylim=(0, 1))
ax.set_title("Responses carry no trace of the signer")
ax.legend(fontsize="small", ncol=2)
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The leaker signs twice, with two different rings that share only the
# leaker's own key. Why does that reveal the leaker, and what would a
# careful leaker do instead?
# A worked solution is in :doc:`/exercises/privacy`.
