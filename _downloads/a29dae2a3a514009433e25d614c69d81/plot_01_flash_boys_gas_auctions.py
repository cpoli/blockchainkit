r"""
Flash Boys 2.0: priority gas auctions and front-running (Daian et al. 2019)
===========================================================================

When an arbitrage opportunity appears on a decentralized exchange, only the
first transaction to execute can take it, and transactions in a block run
in fee order. Daian et al. watched bots compete by repeatedly replacing
their pending transaction with one paying a higher fee: a *priority gas
auction*. Each replacement must raise the fee by a minimum step (10% in
go-ethereum), so with bots that value the opportunity alike, bidding stops
only when the next step would exceed its value :math:`V`:

.. math::

   \text{price} > \frac{V}{1.1}, \qquad \text{profit} < V - \frac{V}{1.1} \approx 0.09\,V.

Competition hands more than nine tenths of the value to whoever orders the
block. Daian et al. called it *miner extractable value*, and showed that it
can even pay a miner to reorder or rewrite recent blocks.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.economics.visualizers import plot_gas_auction

# %%
# Two bots and one opportunity
# ----------------------------

OPPORTUNITY = 50_000
auction = bk.economics.priority_gas_auction(OPPORTUNITY, ["bot A", "bot B"], start=10, seed=2)
print(f"{len(auction.bids)} bids; {auction.winner} pays {auction.price:,} for {OPPORTUNITY:,}")
assert auction.price > OPPORTUNITY / 1.1 and auction.profit < 0.1 * OPPORTUNITY

fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))
plot_gas_auction(auction, opportunity=OPPORTUNITY, ax=left)

# %%
# The bump decides how much the bots keep
# ---------------------------------------

bumps = [1, 2, 5, 10, 12, 15, 20, 25, 30]
kept = []
for bump in bumps:
    shares = [
        bk.economics.priority_gas_auction(OPPORTUNITY, ["a", "b", "c"], bump=bump, seed=s).profit
        / OPPORTUNITY
        for s in range(20)
    ]
    kept.append(sum(shares) / len(shares))
    assert max(shares) < bump / (100 + bump) + 1 / OPPORTUNITY
right.plot(bumps, kept, "o-", color="#2563eb", label="winner's profit")
right.plot(bumps, [b / (100 + b) for b in bumps], ":", color="black", label="bound b / (100 + b)")
right.set(xlabel="minimum raise (%)", ylabel="fraction of the opportunity kept")
right.set_title("Everything else goes to the block producer")
right.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# If the block producer runs its own bot, it pays its fees to itself. How
# much of the opportunity does it keep, and what does that suggest about
# who ends up ordering transactions?
