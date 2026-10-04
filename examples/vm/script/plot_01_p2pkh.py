"""
Bitcoin Script: pay to public-key hash (Nakamoto 2009)
======================================================

Bitcoin does not record owners. Each coin carries a *locking script*, and
spending it means supplying an *unlocking script* that makes the pair
succeed. The standard lock, pay-to-public-key-hash, says: "show a public key
with this hash, and a signature by it over the spending transaction". Script
is a Forth-like stack language with no loops, so a script of n operations
runs at most n steps: Bitcoin needs no gas.

What to look for
----------------

The owner's spend passes; a different key fails at ``OP_EQUALVERIFY``, and the
right key with a signature over a different transaction fails at
``OP_CHECKSIG``. The operation count never exceeds the script length.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Lock a coin to Alice's key hash
# -------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.crypto import public_key, sign

alice = public_key(7)
lock = bk.vm.p2pkh_locking(alice)
print([item if isinstance(item, str) else item.hex()[:16] + "..." for item in lock])
spend = b"spend coin 0: 5 to carol"
attempts = {
    "Alice signs": (bk.vm.p2pkh_unlocking(sign(spend, 7, nonce=11), alice), spend),
    "Mallory's key": (bk.vm.p2pkh_unlocking(sign(spend, 9, nonce=11), public_key(9)), spend),
    "replayed signature": (
        bk.vm.p2pkh_unlocking(sign(spend, 7, nonce=11), alice),
        b"spend coin 0: 5 to mallory",
    ),
}
results = {
    name: bk.vm.verify_script(unlock, lock, message=message)
    for name, (unlock, message) in attempts.items()
}
for name, result in results.items():
    print(f"{name:18s} valid={result.valid}  {result.error or ''}")
assert [r.valid for r in results.values()] == [True, False, False]
assert all(r.operations <= len(lock) + 2 for r in results.values())

fig, ax = plt.subplots(figsize=(7, 3))
ax.barh(
    list(results), [r.operations for r in results.values()], color=["#16a34a", "#dc2626", "#dc2626"]
)
ax.axvline(len(lock) + 2, color="black", linestyle="--", label="script length")
ax.set(xlabel="operations executed", title="Scripts cannot loop")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Write a 2-of-2 lock that requires signatures from both Alice and Bob
# using only the opcodes available (hint: ``OP_CHECKSIG`` then
# ``OP_VERIFY``). Why did Bitcoin later add ``OP_CHECKMULTISIG``?
