r"""
EIP-1559: a base fee, burned (2021), and Roughgarden's analysis (2020)
======================================================================

Until August 2021, Ethereum sold block space as Bitcoin still does: a
*first-price auction* in which each user names a fee and pays it if
included. No bid is obviously right, so users overpay or wait, and the
price swings with every burst of demand. EIP-1559 sets a protocol price per
unit of gas, the *base fee*, adjusted after every block toward a target of
half the block's capacity,

.. math::

   b_{t+1} = b_t \left(1 + \frac{1}{8}\,\frac{g_t - g^*}{g^*}\right),

which every included transaction pays and which is *burned*; users add a
small tip for the producer. Roughgarden showed that outside sudden rises
in demand, offering the base fee plus a tip is optimal, that a myopic
producer has no reason to deviate, and that off-chain deals between
users and producers cannot beat the protocol, because the base fee goes to
nobody.

The simulation sends the same demand, with a surge in the middle, through
both mechanisms over a mempool whose users give up after 20 blocks.
"""

# %%
import statistics

import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.economics.visualizers import plot_fee_market

# %%
# One demand surge, two mechanisms
# --------------------------------

TARGET = 20 * 21_000  # Twenty transfers.
arrivals = [20] * 40 + [45] * 40 + [20] * 40
eip1559 = bk.economics.simulate_fee_market(arrivals, gas_target=TARGET, seed=7)
auction = bk.economics.simulate_fee_market(
    arrivals, mechanism="first-price", gas_target=TARGET, seed=7
)

fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
plot_fee_market(eip1559, gas_target=TARGET, ax=top)
plot_fee_market(auction, gas_target=TARGET, ax=bottom)
fig.tight_layout()

# %%
# The base fee finds the price at which demand meets the target
# -------------------------------------------------------------

before, during = eip1559.base_fees[39], eip1559.base_fees[79]
print(f"base fee before the surge {before}, at its end {during}")
assert during > 1.5 * before
settled = statistics.mean(eip1559.gas_used[60:80]) / TARGET
print(f"gas used during the surge, once the fee has adjusted: {settled:.2f} x target")
assert 0.8 < settled < 1.2
assert max(eip1559.gas_used) <= 2 * TARGET

burned, tips = sum(eip1559.burned), sum(eip1559.producer_revenue)
print(f"burned {burned:,}, paid to producers {tips:,}")
assert burned > 10 * tips  # The producer gains almost nothing from what users pay.

# %%
# Prices that are easier to predict
# ---------------------------------
#
# Block to block, the base fee moves by at most 12.5%; the first-price
# auction's clearing price jumps with the bids that happen to arrive.


def jumps(prices):
    return [abs(b - a) / a for a, b in zip(prices, prices[1:], strict=False) if a]


paid = [fee + 2 for fee in eip1559.base_fees]
print(
    f"largest jump: EIP-1559 {max(jumps(paid)):.1%}, "
    f"first-price {max(jumps(auction.mean_price)):.1%}"
)
assert max(jumps(eip1559.base_fees)) <= 0.125
assert max(jumps(auction.mean_price)) > max(jumps(paid))

plt.show()

# %%
# Exercise
# --------
# A producer considers filling its block with its own transactions to push
# the base fee up for the next producers. What does it pay for that, and
# who receives it? Use ``next_base_fee`` to compute how many full blocks
# it takes to double the base fee.
# A worked solution is in :doc:`/exercises/economics`.
