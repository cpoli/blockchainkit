r"""
Spilman and Hearn's one-way micropayment channels (2013)
========================================================

Paying for a stream by the second on chain costs a transaction, and a fee,
per payment. Jeremy Spilman's channel needs two. The payer locks the
channel's capacity in a 2-of-2 output, after the payee has signed a refund
that returns everything to the payer at a lock time. Each payment is a new
transaction from that output, paying the payee a little more; the payer
signs it and hands it over, and the payee countersigns and publishes only
the last one. Mike Hearn built the scheme into bitcoinj the same year.

For ``m`` payments the chain sees two transactions instead of ``m``:

.. math::

   \text{on-chain transactions} = 2 \quad\text{vs.}\quad m.

The payee must close before the refund's lock time, or the payer takes
everything back.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Streaming one coin a second for a minute
# ----------------------------------------

channel = bk.channels.SpilmanChannel(
    "viewer", "streamer", payer_key=7, payee_key=5, capacity=100, expiry=144
)
paid = [channel.pay(1) for _ in range(60)]
settlement = channel.close(height=30)
print(dict(settlement.payouts))
assert dict(settlement.payouts) == {"viewer": 40, "streamer": 60}

# %%
# A payee who waits too long
# --------------------------
# The refund becomes valid at height 144; the payer can then take back all
# 100 coins, although it signed payments worth 60.

late = bk.channels.SpilmanChannel(
    "viewer", "streamer", payer_key=7, payee_key=5, capacity=100, expiry=144
)
for _ in range(60):
    late.pay(1)
try:
    late.refund(height=143)
except ValueError as error:
    print("at height 143:", error)
refund = late.refund(height=144)
assert refund.kind == "refund" and refund.payouts["streamer"] == 0

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
seconds = range(1, 61)
left.step(seconds, paid, where="post", color="#2563eb", label="signed off chain")
left.axhline(60, color="#16a34a", linestyle="--", label="settled on chain")
left.set(xlabel="second", ylabel="coins paid to the streamer")
left.set_title("Each payment is a signature, not a transaction")
left.legend()
right.plot(seconds, seconds, color="#dc2626", label="one transaction per payment")
right.plot(seconds, [2] * 60, color="#16a34a", label="channel: fund and close")
right.set(xlabel="payments", ylabel="transactions on chain")
right.set_title("Two transactions for any number of payments")
right.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The payer can never take back what it has paid before the lock time,
# because the payee holds a signed transaction for it. What stops the payee
# from publishing an *earlier* payment, and why would it never want to?
