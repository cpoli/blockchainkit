r"""
Sandwich attacks on decentralized exchanges (Zhou et al. 2021)
==============================================================

A swap on a constant-product pool waits in the public mempool before it is
mined. An attacker who sees it can *sandwich* it: buy just before it, which
raises the price the victim pays, and sell just after, at the price the
victim's own purchase pushed up. The victim's *slippage limit*, the least
output it accepts, is all that stops the attacker: the victim's swap
reverts below it, so the attacker picks the most profitable front-run
:math:`a` among those that keep

.. math::

   \text{out}_{\text{victim}}(a) \ge (1 - s)\, \text{out}_{\text{victim}}(0).

For a large trade, that is the largest one allowed. Zhou et al. derived
this optimal attack, showed how a looser tolerance hands more of the trade
to the attacker, and measured sandwiches on Uniswap.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# One sandwich
# ------------

RESERVES = (10_000_000, 10_000_000)
VICTIM = 100_000
attack = bk.economics.sandwich_attack(*RESERVES, VICTIM, slippage_bps=200)
print(
    f"front-run {attack.front_run:,}; victim gets {attack.victim_out:,} "
    f"instead of {attack.victim_out_alone:,}; attacker profit {attack.profit:,}"
)
assert attack.profit > 0 and attack.victim_loss > attack.profit  # Fees take the difference.

# The pool contract agrees with the formula.
world = bk.contracts.World()
tok = world.deploy("lp", bk.contracts.ERC20, 10**9, name="TOK")
usd = world.deploy("lp", bk.contracts.ERC20, 10**9, name="USD")
pool = world.deploy("lp", bk.economics.ConstantProductPool, usd, tok, name="pool")
for who in ("lp", "victim", "attacker"):
    if who != "lp":
        world.transact("lp", usd, "transfer", who, 10**7)
    for token in (tok, usd):
        world.transact(who, token, "approve", pool, 10**9)
world.transact("lp", pool, "add_liquidity", *RESERVES)
minimum = attack.victim_out_alone * 9_800 // 10_000
bought = world.transact("attacker", pool, "swap", usd, attack.front_run, 0).result
victim = world.transact("victim", pool, "swap", usd, VICTIM, minimum)
sold = world.transact("attacker", pool, "swap", tok, bought, 0).result
assert victim.result == attack.victim_out and sold - attack.front_run == attack.profit
greedy = bk.economics.sandwich_profit(*RESERVES, VICTIM, attack.front_run + 10_000)
assert greedy.victim_out < minimum  # Any larger, and the victim's swap would revert.

# %%
# Profit against the front-run, and against the tolerance
# -------------------------------------------------------

fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))
sizes = range(0, 1_500_001, 25_000)
for slippage, color in ((50, "#16a34a"), (200, "#2563eb"), (500, "#dc2626")):
    best = bk.economics.sandwich_attack(*RESERVES, VICTIM, slippage_bps=slippage)
    floor = best.victim_out_alone * (10_000 - slippage) // 10_000
    feasible = [
        a for a in sizes if bk.economics.sandwich_profit(*RESERVES, VICTIM, a).victim_out >= floor
    ]
    left.plot(
        feasible,
        [bk.economics.sandwich_profit(*RESERVES, VICTIM, a).profit for a in feasible],
        color=color,
        label=f"slippage {slippage / 100}%",
    )
    left.plot(best.front_run, best.profit, "o", color=color)
left.axhline(0, color="black", linewidth=0.8)
left.set(xlabel="front-run size", ylabel="attacker profit")
left.set_title("The best front-run is the largest the victim tolerates")
left.legend()

tolerances = [10, 25, 50, 100, 200, 300, 500, 800]
results = [bk.economics.sandwich_attack(*RESERVES, VICTIM, slippage_bps=s) for s in tolerances]
right.plot(
    [s / 100 for s in tolerances], [r.profit for r in results], "o-", label="attacker profit"
)
right.plot(
    [s / 100 for s in tolerances], [r.victim_loss for r in results], "s-", label="victim loss"
)
right.set(xlabel="victim's slippage tolerance (%)", ylabel="tokens")
right.set_title("A loose tolerance invites the sandwich")
right.legend()
fig.tight_layout()
# The victim moves the price by about 2%, more than the attacker's two fees of 0.3%,
# so even a tight tolerance leaves a profit; a loose one multiplies it.
assert results[0].profit > 0 and all(
    a.profit < b.profit for a, b in zip(results, results[1:], strict=False)
)

plt.show()

# %%
# Exercise
# --------
# The victim could split its trade into ten swaps of 10,000. Assuming each
# is sandwiched with the same tolerance, does the attacker earn more or
# less in total? What about the 0.3% fee the attacker pays twice?
# A worked solution is in :doc:`/exercises/economics`.
