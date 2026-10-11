r"""
Fixed supply and the halving schedule (2009)
============================================

The first Bitcoin release fixed the monetary policy in code. The block at
height :math:`h` creates

.. math::

   S(h) = \left\lfloor 50 \cdot 10^8 \,/\, 2^{\lfloor h / 210\,000 \rfloor} \right\rfloor
   \text{ satoshis},

so the subsidy halves every 210,000 blocks, about every four years, and the
supply approaches a geometric limit of 21 million coins. Because the
division is a right shift that drops fractions of a satoshi, issuance stops
at the 33rd halving, around the year 2140, and the total falls short of 21
million by about 0.023 BTC. After that, miners are paid by fees alone.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.economics.systems.rewards import COIN, HALVING_INTERVAL

# %%
# Supply and subsidy over time
# ----------------------------

cap = bk.economics.issued_supply(64 * HALVING_INTERVAL)
print(f"final supply: {cap / COIN:,.8f} BTC, short of 21 million by {21e6 - cap / COIN:.4f}")
assert cap == 2_099_999_997_690_000
last_era = max(e for e in range(64) if bk.economics.block_subsidy(e * HALVING_INTERVAL) > 0)
assert last_era == 32  # Halving 33 brings the subsidy to zero.
print("last block with a subsidy:", (last_era + 1) * HALVING_INTERVAL - 1)

years = [2009 + 4 * h / HALVING_INTERVAL for h in range(0, 35 * HALVING_INTERVAL, 10_000)]
heights = range(0, 35 * HALVING_INTERVAL, 10_000)
fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
left.plot(years, [bk.economics.issued_supply(h) / COIN / 1e6 for h in heights], color="#2563eb")
left.axhline(21, color="black", linestyle=":")
left.set(xlabel="year (four years per halving)", ylabel="coins issued (millions)")
left.set_title("A geometric series that stops just short of 21 million")
paying = [(y, bk.economics.block_subsidy(h)) for y, h in zip(years, heights, strict=True)]
paying = [(y, subsidy) for y, subsidy in paying if subsidy > 0]
right.semilogy(*zip(*paying, strict=True), color="#dc2626")
right.set(xlabel="year", ylabel="subsidy per block (satoshis)")
right.set_title("Halving every 210,000 blocks")
fig.tight_layout()

# %%
# Half of what is left
# --------------------
#
# Each era issues as much as all later eras together, plus a little rounding.

for era in range(4):
    issued = bk.economics.issued_supply((era + 1) * HALVING_INTERVAL)
    issued -= bk.economics.issued_supply(era * HALVING_INTERVAL)
    later = cap - bk.economics.issued_supply((era + 1) * HALVING_INTERVAL)
    print(
        f"era {era}: {issued / COIN:>12,.0f} BTC issued, {later / COIN:>12,.2f} BTC still to come"
    )
    assert issued - later < COIN

plt.show()

# %%
# Exercise
# --------
# If the subsidy were divided exactly instead of shifted, how many coins
# would eventually exist? Which halving produces the first rounding loss?
# A worked solution is in :doc:`/exercises/economics`.
