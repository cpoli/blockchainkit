r"""
zk-rollups: validity proofs for batched transactions (2018)
===========================================================

A rollup runs transactions off chain but posts them, compressed, to the
chain, so anyone can rebuild its state. Barry Whitehat's *roll_up* and
Buterin's 2018 proposal added a succinct proof that the posted state root
follows from the batch. The contract checks the proof at a fixed cost and
never re-executes anything, so the gas per transaction falls toward the
cost of its calldata:

.. math::

   g(n) = \frac{G_{\text{verify}}}{n} + 16\,b
   \quad\text{vs.}\quad 21\,000 \text{ for a transfer on chain}.

An invalid state root cannot be posted at all, because no proof of it
exists, so withdrawals are final as soon as the batch is accepted.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A batch of transfers, proven and posted
# ---------------------------------------

rng = Random(11)
accounts = [f"user{i}" for i in range(20)]
rollup = bk.channels.ZKRollup({a: 1_000 for a in accounts})
batch = [
    bk.channels.Transfer(rng.choice(accounts), rng.choice(accounts), rng.randint(1, 300))
    for _ in range(200)
]
gas = rollup.submit(batch, rollup.prove(batch))
print(f"200 transfers for {gas:,} gas: {gas / 200:,.0f} per transfer")
assert sum(rollup.balances.values()) == 20 * 1_000

# %%
# An operator cannot prove a false state
# --------------------------------------

theft = {**rollup.balances, "operator": 5_000}
try:
    rollup.prove(batch, claimed_root=bk.channels.state_root(theft))
except ValueError as error:
    print("operator's claim:", error)

# %%
# Gas per transaction against batch size
# --------------------------------------

sizes = [1, 10, 30, 100, 300, 1_000, 3_000, 10_000]
per_transfer = [
    bk.channels.batch_gas(n, bytes_per_transaction=12, fixed_gas=300_000) / n for n in sizes
]
break_even = next(n for n, g in zip(sizes, per_transfer, strict=True) if g < 21_000)
print("cheaper than on chain from", break_even, "transfers per batch")
per_block = 30_000_000 // round(per_transfer[-1])
print(f"transfers per 30M-gas block: {30_000_000 // 21_000:,} on chain, {per_block:,} rolled up")

fig, ax = plt.subplots(figsize=(8, 4))
ax.loglog(sizes, per_transfer, "o-", color="#2563eb", label="zk-rollup")
ax.axhline(21_000, color="#dc2626", linestyle="--", label="transfer on chain")
ax.axhline(12 * 16, color="#16a34a", linestyle=":", label="calldata alone (12 bytes)")
ax.set(xlabel="transfers per batch", ylabel="gas per transfer")
ax.set_title("The proof's cost is shared by the whole batch")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A rollup that posts its data elsewhere (a "validium") pays only for the
# proof. Recompute the gas per transfer with ``bytes_per_transaction=0``,
# and explain what users lose if the operator then withholds the data.
# A worked solution is in :doc:`/exercises/channels`.
