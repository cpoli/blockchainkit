r"""
Uniswap's constant-product market maker and impermanent loss (2018)
===================================================================

An order book needs market makers constantly posting and cancelling
orders, which costs too much gas on chain. Uniswap replaced the book with a
pool of two tokens whose reserves keep their product constant: a trader who
adds :math:`\Delta x` (after a 0.3% fee) receives the :math:`\Delta y` that
satisfies

.. math::

   (x + \Delta x)(y - \Delta y) = x y.

The price :math:`y / x` moves against every trade, so arbitrageurs keep it
in line with other markets. Liquidity providers earn the fees but bear
*impermanent loss*: if the price moves by a factor :math:`r`, their deposit
is worth :math:`2\sqrt{r}/(1 + r)` of simply holding the tokens.
"""

# %%
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk
from blockchainkit.economics.visualizers import plot_constant_product

# %%
# A pool and its curve
# --------------------

world = bk.contracts.World()
eth = world.deploy("lp", bk.contracts.ERC20, 10**9, name="ETH")
usd = world.deploy("lp", bk.contracts.ERC20, 10**12, name="USD")
pool = world.deploy("lp", bk.economics.ConstantProductPool, eth, usd, name="pool")
for token in (eth, usd):
    world.transact("lp", token, "approve", pool, 10**12)
shares = world.transact("lp", pool, "add_liquidity", 1_000, 2_000_000).result
print("ETH price:", float(world.view(pool, "price")), "USD; LP shares:", shares)

world.transact("lp", usd, "transfer", "trader", 10**9)
world.transact("lp", eth, "transfer", "trader", 10**6)
for token in (eth, usd):
    world.transact("trader", token, "approve", pool, 10**12)
states = []
for size in (200_000, 400_000, 800_000):
    out = world.transact("trader", pool, "swap", usd, size, 0).result
    states.append(world.view(pool, "reserves"))
    print(f"{size:>9,} USD buys {out} ETH; price now {float(world.view(pool, 'price')):,.0f}")
x, y = world.view(pool, "reserves")
assert x * y >= 1_000 * 2_000_000  # Fees only ever grow the product.

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.5))
plot_constant_product(1_000, 2_000_000, states=states, ax=left)
left.set(xlabel="ETH reserve", ylabel="USD reserve")

# %%
# A liquidity provider against a holder
# -------------------------------------
#
# Arbitrage moves the pool to each new price; the provider then withdraws.

ratios = np.geomspace(0.2, 5, 25)
measured = []
for ratio in ratios:
    w = bk.contracts.World()
    a = w.deploy("lp", bk.contracts.ERC20, 10**12)
    b = w.deploy("lp", bk.contracts.ERC20, 10**15)
    p = w.deploy("lp", bk.economics.ConstantProductPool, a, b, 0)  # No fee: pure divergence.
    for token in (a, b):
        w.transact("lp", token, "approve", p, 10**15)
    w.transact("lp", p, "add_liquidity", 10**6, 10**9)  # Price 1,000.
    # Swap to the reserves at the new price, keeping x * y fixed.
    target_x = round(10**6 / np.sqrt(ratio))
    if target_x < 10**6:
        w.transact("lp", p, "swap", b, round(10**15 / target_x) - 10**9, 0)
    elif target_x > 10**6:
        w.transact("lp", p, "swap", a, target_x - 10**6, 0)
    price = float(w.view(p, "price"))
    out_a, out_b = w.transact("lp", p, "remove_liquidity", w.view(p, "shares_of", "lp")).result
    held = 10**6 * price + 10**9
    measured.append((out_a * price + out_b) / held - 1)

theory = [bk.economics.impermanent_loss(r) for r in ratios]
assert np.allclose(measured, theory, atol=2e-3)
right.semilogx(ratios, np.array(theory) * 100, color="#dc2626", label="2 sqrt(r)/(1 + r) - 1")
right.semilogx(ratios, np.array(measured) * 100, "o", color="#2563eb", label="pool withdrawal")
right.set(xlabel="price ratio r", ylabel="loss against holding (%)")
right.set_title("Impermanent loss")
right.legend()
fig.tight_layout()
print(
    f"price doubles: {bk.economics.impermanent_loss(2):.2%}; "
    f"fivefold: {bk.economics.impermanent_loss(5):.2%}"
)

plt.show()

# %%
# Exercise
# --------
# With the 0.3% fee, how much trading volume must pass through the pool,
# as a multiple of its value, to make up for the loss when the price
# doubles? Use ``amount_out`` to check your estimate with a round trip.
