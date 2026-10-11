r"""
Vickrey's second-price auction: truthful bidding (1961)
=======================================================

In a sealed-bid *first-price* auction, the winner pays its own bid, so
every bidder shades its bid below its value, by an amount that depends on
guesses about the others. Vickrey proposed charging the winner the
*second-highest* bid instead. A bid then decides only whether one wins,
never what one pays, and bidding one's true value is a dominant strategy:

.. math::

   u_i(b_i) = \begin{cases} v_i - \max_{j \ne i} b_j & b_i > \max_{j \ne i} b_j,\\
   0 & \text{otherwise}, \end{cases}

is maximized by :math:`b_i = v_i` whatever the others bid. Blockchains use
the idea where honest bidding matters: fee mechanisms, block-builder
auctions, and on-chain auctions of names and collateral.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# One bidder's utility against its own bid
# ----------------------------------------

VALUE = 60
others = {"rival0": 35, "rival1": 48, "rival2": 22}
bids = range(0, 101)
second = [bk.economics.second_price_auction(others | {"me": b}).utility("me", VALUE) for b in bids]
first = [bk.economics.first_price_auction(others | {"me": b}).utility("me", VALUE) for b in bids]
assert max(second) == second[VALUE]  # The true value is a best bid.
assert max(first) > first[VALUE] == 0  # Bidding the value earns nothing in a first-price auction.
print("best first-price bid:", first.index(max(first)), "earning", max(first))

# %%
# Truthfulness against every rival profile
# ----------------------------------------

rng = Random(11)
worst_gain = 0
for _ in range(300):
    rivals = {f"r{i}": rng.randint(0, 100) for i in range(rng.randint(1, 5))}
    value = rng.randint(0, 100)
    truthful = bk.economics.second_price_auction(rivals | {"me": value}).utility("me", value)
    for deviation in range(0, 101, 5):
        result = bk.economics.second_price_auction(rivals | {"me": deviation})
        worst_gain = max(worst_gain, result.utility("me", value) - truthful)
print("largest gain from lying over 300 random auctions:", worst_gain)
assert worst_gain == 0

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(bids, second, color="#2563eb", label="second-price")
ax.plot(bids, first, color="#dc2626", label="first-price")
ax.axvline(VALUE, color="black", linestyle=":", label=f"true value {VALUE}")
ax.set(xlabel="my bid", ylabel="my utility", title="Only the second-price auction rewards honesty")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Two bidders could collude in a second-price auction: the lower one stays
# out. How much does that save the winner, and who pays for it? Repeat with
# three bidders where the two highest collude.
