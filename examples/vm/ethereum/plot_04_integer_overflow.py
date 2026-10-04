"""
Integer overflow: minting tokens from nothing (BeautyChain, 2018)
=================================================================

EVM words wrap modulo 2**256. In April 2018 an attacker called the
BeautyChain (BEC) token's ``batchTransfer`` with two recipients and a value of
2**255. The contract computed the total as ``2 * 2**255``, which wraps to 0,
checked that the sender had at least 0 tokens, and credited each recipient
2**255 tokens. Exchanges suspended the token (CVE-2018-10299). The SafeMath
library's checked arithmetic, and later Solidity 0.8's default overflow
checks, close the hole.

What to look for
----------------

The unchecked contract accepts the call from a sender with no tokens, and
the total supply jumps by 2**256: tokens appear from nowhere.
The checked version reverts, and both versions agree on every ordinary
transfer.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# The attack
# ----------
import matplotlib.pyplot as plt

import blockchainkit as bk

ATTACKER, RECIPIENT_A, RECIPIENT_B = 1, 2, 3
balances = {ATTACKER: 0, 4: 1_000_000}
unchecked = bk.vm.batch_transfer(ATTACKER, [RECIPIENT_A, RECIPIENT_B])
checked = bk.vm.batch_transfer(ATTACKER, [RECIPIENT_A, RECIPIENT_B], checked=True)
value = 2**255
assert 2 * value % 2**256 == 0
after = bk.vm.execute(unchecked, arguments=(value,), storage=balances).storage
print("recipient A now holds", after[RECIPIENT_A])
assert after[RECIPIENT_A] == after[RECIPIENT_B] == value and after[ATTACKER] == 0
try:
    bk.vm.execute(checked, arguments=(value,), storage=balances)
except bk.vm.VMError as error:
    print("checked version:", error)

# %%
# Ordinary transfers are unaffected
# ---------------------------------
funded = {ATTACKER: 500}
for v in (1, 10, 100, 250):
    a = bk.vm.execute(unchecked, arguments=(v,), storage=funded).storage
    b = bk.vm.execute(checked, arguments=(v,), storage=funded).storage
    assert a == b and sum(a.values()) == 500

supply = {"before": sum(balances.values()), "after attack": sum(after.values())}
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.bar(supply.keys(), [s / 2**255 for s in supply.values()], color=["#64748b", "#dc2626"])
ax.set(ylabel="total supply / 2**255", title="Tokens from a wrapped multiplication")
fig.tight_layout()

# %%
# Exercise
# --------
# The checked version tests ``amount / count == value``. Why does that detect
# every overflow of ``count * value`` for ``count >= 1``? Could the check
# ``amount >= value`` replace it?
