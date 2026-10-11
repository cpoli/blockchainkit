r"""
MakerDAO's Dai: a collateralized stablecoin and liquidation (2017)
==================================================================

A stablecoin aims at a constant price, usually one dollar. Dai is backed
not by dollars in a bank but by ether locked in a contract. A user locks
ether in a *vault* and draws newly minted Dai against it, as long as

.. math::

   \text{collateral} \times \text{price} \ge 1.5 \times \text{debt}

at the price an oracle reports. If ether falls far enough, anyone may
*liquidate* the vault: repay its Dai, which is burned, and take ether worth
the debt plus a 13% penalty. The surplus collateral stays with the owner.
The overcollateralization keeps every Dai backed by more than a dollar of
ether even after a fall.

The vaults run on the contract world model. Single-Collateral Dai sold the
collateral in an auction; here the liquidator buys it at the oracle price.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Three vaults and a falling price
# --------------------------------

world = bk.contracts.World()
feed = world.deploy("maker", bk.economics.PriceFeed, 400, name="price feed")
engine = world.deploy("maker", bk.economics.VaultEngine, feed, name="vault engine")
dai = world.view(engine, "dai")

vaults = {"cautious": 1_000, "moderate": 2_000, "aggressive": 2_600}
for owner, debt in vaults.items():
    world.fund(owner, 10)
    assert world.transact(owner, engine, "lock", value=10).success
    assert world.transact(owner, engine, "draw", debt).success
    world.transact(owner, dai, "transfer", "keeper", debt)  # Spent; the keeper holds the Dai.
print("a fourth vault drawing too much:", end=" ")
world.fund("greedy", 10)
world.transact("greedy", engine, "lock", value=10)
print(world.transact("greedy", engine, "draw", 2_700).error)

# %%
# The keeper liquidates whatever becomes unsafe
# ---------------------------------------------

prices = list(range(400, 99, -20))
supply, backing, liquidated = [], [], {}
for price in prices:
    world.transact("maker", feed, "set_price", price)
    for owner in vaults:
        if owner not in liquidated and not world.view(engine, "is_safe", owner):
            receipt = world.transact("keeper", engine, "liquidate", owner)
            assert receipt.success
            liquidated[owner] = (price, receipt.result)
    supply.append(world.view(dai, "total_supply"))
    locked = sum(world.view(engine, "collateral_of", owner) for owner in vaults)
    backing.append(locked * price)

for owner, (price, seized) in liquidated.items():
    left = world.view(engine, "collateral_of", owner)
    print(f"{owner}: liquidated at {price}, keeper took {seized} ETH, owner kept {left} ETH")
assert set(liquidated) == set(vaults)
assert liquidated["aggressive"][0] > liquidated["moderate"][0] > liquidated["cautious"][0]
assert all(dai_supply <= value for dai_supply, value in zip(supply, backing, strict=True))

fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.plot(prices, supply, "o-", color="#2563eb", label="Dai in circulation")
ax.plot(prices, backing, "s-", color="#16a34a", label="value of the ether still locked")
for owner, (price, _) in liquidated.items():
    ax.axvline(price, color="#dc2626", linestyle=":")
    ax.annotate(owner, (price, max(backing) * 0.9), rotation=90, ha="right")
ax.invert_xaxis()
ax.set(xlabel="ether price (Dai)", ylabel="Dai")
ax.set_title("Liquidations keep every Dai backed")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# If the price drops from 400 to 150 in one step, the aggressive vault is
# liquidated only at 150. Is its debt still covered? Find the price drop
# within one step at which the keeper would lose money, and explain why
# Maker later moved to auctions and a larger ratio for volatile collateral.
# A worked solution is in :doc:`/exercises/economics`.
