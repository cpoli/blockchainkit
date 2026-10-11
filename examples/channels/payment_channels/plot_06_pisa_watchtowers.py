r"""
Watchtowers and PISA: guarding offline channel parties (McCorry et al., 2019)
=============================================================================

A Lightning party is safe only while it watches the chain: if it is offline
for longer than the channel's delay, a revoked commitment can be swept. A
*watchtower* watches for it. After each update the party gives the tower a
hint, half the revoked commitment's txid, and a presigned penalty encrypted
under the whole txid; the tower learns nothing until that commitment
appears, and can then publish only a penalty that pays the party.

PISA made towers accountable: the tower signs a receipt for every
appointment and locks a deposit, which the party claims if a revoked state
it was hired to watch gets swept. For a party that checks the chain every
``T`` blocks, against a breach at a random moment and a delay ``d``,

.. math::

   P(\text{loss}) = \max\left(0,\ 1 - \frac{d}{T}\right) \times P(\text{tower fails}).
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A tower penalizes while Bob is offline
# --------------------------------------


def breach(tower_online):
    channel = bk.channels.LightningChannel(("alice", "bob"), (7, 5), (100, 0), delay=144)
    channel.pay("alice", 60)
    tower = bk.channels.Watchtower(99, collateral=500, online=tower_online)
    hint, blob = bk.channels.make_appointment(channel, "bob", state=0)
    receipt = tower.appoint(hint, blob, expires=10_000)
    channel.publish("alice", state=0, height=1_000)  # Alice tries her best old state.
    return channel, tower, receipt


channel, tower, receipt = breach(tower_online=True)
settlement = tower.watch(channel, height=1_001)
print("with a tower:", dict(settlement.payouts))
assert settlement.kind == "penalty" and settlement.payouts["bob"] == 100

# %%
# A tower that fails pays under PISA
# ----------------------------------

channel, lazy, receipt = breach(tower_online=False)
assert lazy.watch(channel, height=1_001) is None
channel.sweep(height=1_144)
assert bk.channels.verify_receipt(receipt) and bk.channels.tower_liable(receipt, channel)
print(f"the tower forfeits its {lazy.collateral} collateral to Bob")

# %%
# How often a breach succeeds
# ---------------------------
# Bob checks every T blocks; the breach happens at a uniformly random
# moment; the tower fails 5% of the time.

delay, tower_failure = 144, 0.05
intervals = [72, 144, 288, 576, 1_008, 2_016]
rng = Random(8)
simulated = []
for interval in intervals:
    trials = 20_000
    missed = sum(rng.uniform(0, interval) > delay for _ in range(trials))
    simulated.append(missed / trials)
alone = [max(0.0, 1 - delay / t) for t in intervals]
assert all(abs(s - a) < 0.02 for s, a in zip(simulated, alone, strict=True))

fig, ax = plt.subplots(figsize=(8, 4))
days = [t / 144 for t in intervals]
ax.plot(days, alone, "o-", color="#dc2626", label="Bob alone")
ax.plot(days, simulated, "x", color="black", label="simulated")
ax.plot(days, [a * tower_failure for a in alone], "s-", color="#16a34a", label="with a tower")
ax.set(xlabel="days between Bob's checks (delay = 1 day)", ylabel="chance a breach succeeds")
ax.set_title("A watchtower covers the time Bob is away")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A tower that is paid per appointment and never acts earns money for
# nothing. With PISA's collateral of ``C`` and a breach probability ``b``
# per appointment, what collateral makes acting worthwhile for a tower
# whose cost of watching is ``w`` per appointment?
