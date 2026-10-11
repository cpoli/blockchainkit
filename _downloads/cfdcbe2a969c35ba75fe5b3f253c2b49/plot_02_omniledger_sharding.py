r"""
OmniLedger and sharding (Kokoris-Kogias et al., 2018)
=====================================================

Splitting validators into shards multiplies throughput, but each shard is
only as safe as its own committee. OmniLedger reshuffles validators into
shards every epoch from unbiasable randomness, so an adversary cannot
concentrate its validators in one committee. A committee of ``m`` drawn
from ``N`` validators, ``M`` of them malicious, fails if a third or more of
it is malicious, which is a hypergeometric tail:

.. math::

   P(X \ge m/3) = \sum_{x \ge m/3}
   \frac{\binom{M}{x}\binom{N-M}{m-x}}{\binom{N}{m}}.

Payments that span shards use Atomix: lock every input, then commit on the
output shard if all inputs were accepted, or unlock them all.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# How large must a shard be?
# --------------------------

validators, adversary = 1_800, 450  # A quarter of all validators.
sizes = [10, 25, 50, 100, 200, 300, 450, 600]
exact = [bk.channels.shard_failure_probability(validators, adversary, m) for m in sizes]
for m, p in zip(sizes, exact, strict=True):
    print(f"shard of {m:3d}: fails with probability {p:.2e}")
assert exact[-1] < 1e-6 < exact[3]

# %%
# Simulated epochs match the formula
# ----------------------------------

shards = [18, 9, 6]  # Committees of 100, 200 and 300.
simulated = [
    bk.channels.compromised_epochs(validators, adversary, s, epochs=400, seed=s) for s in shards
]
predicted = [
    1 - (1 - bk.channels.shard_failure_probability(validators, adversary, validators // s)) ** s
    for s in shards
]
print("some shard compromised per epoch:", simulated, "predicted about", predicted)
assert abs(simulated[0] - predicted[0]) < 0.05

# %%
# Atomix: all inputs or none
# --------------------------

balances = [{"alice": 30}, {"alice": 20}, {}]
ok = bk.channels.atomix_transfer(balances, [(0, "alice", 30), (1, "alice", 20)], (2, "bob"))
short = bk.channels.atomix_transfer(balances, [(0, "alice", 30), (1, "alice", 25)], (2, "bob"))
assert ok.committed and dict(ok.balances[2]) == {"bob": 50}
assert not short.committed and [dict(b) for b in short.balances] == balances

fig, ax = plt.subplots(figsize=(8, 4))
ax.semilogy(sizes, exact, "o-", color="#2563eb", label="25% adversary")
ax.semilogy(
    sizes,
    [bk.channels.shard_failure_probability(validators, 540, m) for m in sizes],
    "s-",
    color="#dc2626",
    label="30% adversary",
)
ax.set(xlabel="validators per shard", ylabel="chance a shard is a third malicious")
ax.set_title("Larger committees are exponentially safer")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# With 1,800 validators and a 25% adversary, how many shards can the
# network run while keeping the chance that *any* shard fails in an epoch
# below one in a million? What happens as the adversary nears a third?
# A worked solution is in :doc:`/exercises/channels`.
