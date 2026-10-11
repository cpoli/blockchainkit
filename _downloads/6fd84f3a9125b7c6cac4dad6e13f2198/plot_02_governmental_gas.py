r"""
GovernMental: an unbounded loop meets the block gas limit (2016)
================================================================

GovernMental was a Ponzi game: the last person to invest before 12 hours
of silence won the jackpot. Paying out also reset the game, by clearing the
array of creditors, one storage write per entry. In April 2016 the array
had grown so long that clearing it needed more gas than a block allowed
(about 4.7 million then), so the payout could not execute and roughly
1,100 ether sat stuck in the contract.

The cost of the reset grows linearly with the number of creditors :math:`n`,
and the payout fails once

.. math::

   G_{\text{base}} + n \cdot G_{\text{write}} > G_{\text{block}}.

Any loop over a collection that users can grow is a denial of service
waiting to happen. A constant-cost reset, here a new round number instead
of deleting old entries, pays out whatever the size.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts.systems.payments import GOVERNMENTAL_TIMEOUT
from blockchainkit.contracts.systems.world import GAS_COSTS

# %%
# Payout gas against the number of creditors
# ------------------------------------------

BLOCK_GAS_LIMIT = 4_712_388  # Ethereum's block gas limit in early 2016.
sizes = [100, 300, 600, 900, 920, 940, 1_200]


def payout(creditors, lazy):
    world = bk.contracts.World(block_gas_limit=BLOCK_GAS_LIMIT)
    game = world.deploy("operator", bk.contracts.GovernMental, lazy)
    for index in range(creditors):
        world.fund(f"p{index}", 1)
        world.transact(f"p{index}", game, "invest", value=1)
    world.advance(seconds=GOVERNMENTAL_TIMEOUT)
    return world.transact("anyone", game, "payout")


eager = {n: payout(n, lazy=False) for n in sizes}
lazy = {n: payout(n, lazy=True) for n in sizes}
for n in sizes:
    print(
        f"{n:5d} creditors: clear-all {eager[n].gas_used:>9,} gas "
        f"{'ok' if eager[n].success else eager[n].error:10s} new round {lazy[n].gas_used:,} gas"
    )
first_failure = min(n for n in sizes if not eager[n].success)
assert all(r.success for r in lazy.values()) and first_failure == 940
assert (BLOCK_GAS_LIMIT - GAS_COSTS["transaction"]) // GAS_COSTS["write"] < first_failure

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(
    sizes, [eager[n].gas_used for n in sizes], "o-", color="#dc2626", label="clear every creditor"
)
ax.plot(sizes, [lazy[n].gas_used for n in sizes], "o-", color="#16a34a", label="start a new round")
ax.axhline(BLOCK_GAS_LIMIT, color="#64748b", linestyle="--", label="block gas limit")
ax.set(xlabel="creditors", ylabel="gas used by the payout", title="The payout outgrows the block")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Ethereum's block gas limit has since grown to 30 million. With this
# model's 5,000 gas per write, how many creditors would it take to freeze
# the same contract today? Check your answer with ``World()``, whose default
# limit is 30 million. A worked solution is in :doc:`/exercises/contracts`.
