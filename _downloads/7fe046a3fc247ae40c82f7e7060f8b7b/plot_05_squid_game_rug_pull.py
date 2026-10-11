r"""
Rug pulls and hidden-mint tokens: the Squid Game token (2021)
=============================================================

Anyone can issue a token and open a market for it on a decentralized
exchange. In November 2021 a token named after the Squid Game series rose
from a cent to 2,861 dollars in a week; its buyers could not sell, because
the contract refused transfers into the market unless the seller held
"marbles", which nobody could earn. Its creators then sold and vanished,
and the price fell to nothing in minutes. The rule hid behind an
innocent-looking override, of the kind many scam tokens use:

.. code-block:: solidity

   function _transfer(address from, address to, uint amount) internal override {
       if (to == pair) require(antiDumpExempt[from], "anti-dump");   // no selling
       super._transfer(from, to, amount);
   }

On a constant-product market :math:`xy = k`, whoever can sell when no one
else can drains the quote reserve: selling :math:`\Delta x` returns
:math:`y \Delta x / (x + \Delta x)`, close to all of :math:`y` for a large
mint. The defence costs one fork of the chain: buy a little and sell it
back before buying for real, as honeypot scanners do.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A market for a token only its owner can sell
# --------------------------------------------

world = bk.contracts.World()
usd = world.deploy("bank", bk.contracts.ERC20, 10**8, name="USD")
squid = world.deploy("dev", bk.fraud.SellBlockToken, 10**6, name="SQUID")
world.transact("bank", usd, "transfer", "dev", 10_000)
pool = world.deploy("dev", bk.economics.ConstantProductPool, squid, usd, name="pool")
world.transact("dev", squid, "set_pool", pool)
for asset in (squid, usd):
    world.transact("dev", asset, "approve", pool, 10**6)
world.transact("dev", pool, "add_liquidity", 500_000, 10_000)

print("sell test before buying:", bk.fraud.sell_test(world, pool, squid, usd, "bank", 100))
assert not bk.fraud.sell_test(world, pool, squid, usd, "bank", 100)

# %%
# Buyers pile in; nobody can leave
# --------------------------------

prices = [float(world.view(pool, "price"))]
buyers = [f"buyer{k}" for k in range(15)]
for k, name in enumerate(buyers):
    world.transact("bank", usd, "transfer", name, 2_000 + 500 * k)
    world.transact(name, usd, "approve", pool, 10**6)
    world.transact(name, pool, "swap", usd, 2_000 + 500 * k)
    prices.append(float(world.view(pool, "price")))
stuck = world.view(squid, "balance_of", buyers[0])
world.transact(buyers[0], squid, "approve", pool, stuck)
print("a buyer tries to sell:", world.transact(buyers[0], pool, "swap", squid, stuck).error)

# %%
# The owner sells everything it kept
# ----------------------------------

before = world.view(usd, "balance_of", "dev")
world.transact("dev", pool, "swap", squid, world.view(squid, "balance_of", "dev"))
prices.append(float(world.view(pool, "price")))
gain = world.view(usd, "balance_of", "dev") - before
paid_in = sum(2_000 + 500 * k for k in range(15))
print(f"buyers paid {paid_in:,} USD; the owner walked away with {gain:,}")
assert gain > 0.9 * paid_in and prices[-1] < prices[0]

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(prices, "o-", color="#dc2626")
ax.set(xlabel="trade", ylabel="price of SQUID in USD", yscale="log")
ax.set_title("Buys push the price up; one sale ends it")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Replace the sell block with :class:`~blockchainkit.fraud.systems.rug_pulls.HiddenMintToken`.
# Does the sell test still warn the buyers? Which check on the token's
# source or its total supply would?
