r"""
Pay-to-script-hash and multisig (BIP16, 2012)
=============================================

One key is one point of failure. A coin locked to 2 of 3 keys survives the
loss or theft of one, but before 2012 the payer had to write the whole
locking script, and pay for its size. Gavin Andresen's BIP16 locks a coin
to the hash of a *redeem script* instead,

.. math::

   \texttt{OP\_HASH256}\ \langle H(\text{redeem}) \rangle\ \texttt{OP\_EQUAL},

and the spender reveals the script and satisfies it. Validation runs in two
stages: the revealed script must match the hash, and then it runs on the
remaining pushes. The payer sees only a short address starting with 3. The
teaching interpreter has no ``OP_CHECKMULTISIG``, so m-of-n is written as
one branch per set of m signers, and its size shows why scripts are capped
at 520 bytes.
"""

# %%
from itertools import combinations
from math import comb

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A 2-of-3 wallet
# ---------------

keys = [3, 5, 7]
redeem = bk.wallets.multisig_redeem_script(2, [bk.crypto.public_key(k) for k in keys])
locking = bk.wallets.p2sh_locking(redeem)
print("address:", bk.wallets.p2sh_address(redeem))
print(
    "redeem script:",
    len(bk.wallets.serialize_script(redeem)),
    "bytes; locking script:",
    len(bk.wallets.serialize_script(locking)),
    "bytes",
)
message = b"spend the coin to bob"
for signers in combinations(range(3), 2):
    signatures = {i: bk.crypto.sign(message, keys[i], nonce=40 + i) for i in signers}
    spend = bk.wallets.p2sh_unlocking(redeem, bk.wallets.multisig_unlocking(2, 3, signatures))
    result = bk.wallets.verify_p2sh(spend, locking, message=message)
    print("signers", signers, "valid:", result.valid)
    assert result.valid

# One key alone cannot spend: there is no branch with a single signature.
lone = {0: bk.crypto.sign(message, 3, nonce=1), 1: bk.crypto.sign(message, 99, nonce=2)}
spend = bk.wallets.p2sh_unlocking(redeem, bk.wallets.multisig_unlocking(2, 3, lone))
assert not bk.wallets.verify_p2sh(spend, locking, message=message).valid

# %%
# The cost of writing m-of-n without OP_CHECKMULTISIG
# ---------------------------------------------------

sizes = {}
for n in range(1, 6):
    publics = [bk.crypto.public_key(k) for k in range(2, 2 + n)]
    for m in range(1, n + 1):
        script = bk.wallets.multisig_redeem_script(m, publics)
        sizes[m, n] = len(bk.wallets.serialize_script(script))
assert sizes[2, 3] <= 520 < sizes[3, 5]

fig, ax = plt.subplots(figsize=(6, 4))
for n in range(1, 6):
    ax.plot(range(1, n + 1), [sizes[m, n] for m in range(1, n + 1)], "o-", label=f"n = {n}")
ax.axhline(
    bk.constants.MAX_SCRIPT_ELEMENT_SIZE, color="#dc2626", linestyle="--", label="520-byte limit"
)
ax.set(xlabel="threshold m", ylabel="redeem script (bytes)")
ax.set_title(f"One branch per signer set: C(5, 2) = {comb(5, 2)} branches")
ax.legend()
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# Which (m, n) wallets fit in 520 bytes? Bitcoin's ``OP_CHECKMULTISIG``
# needs about 34 bytes per compressed key: how large would 3-of-5 be?
# A worked solution is in :doc:`/exercises/wallets`.
