r"""
ICO exit scams and the DAICO (2017-2018)
========================================

In 2017 initial coin offerings raised billions of dollars for projects that
existed only as white papers. Nothing tied the team to the money: once the
sale closed, it could withdraw everything and disappear, an *exit scam*.
In December 2017 the SEC's new Cyber Unit froze the PlexCoin sale, which had
promised a 1,354% return within a month. Buterin's DAICO proposal of
January 2018 keeps the ether in the contract and releases it at a *tap*
rate :math:`\tau`, while contributors may vote to refund what remains:

.. code-block:: solidity

   function withdraw(uint amount) onlyTeam {
       require(withdrawn + amount <= tap * (now - start));
       withdrawn += amount;
       team.transfer(amount);
   }

A team that vanishes after time :math:`t` then takes at most
:math:`\min(\tau t, \text{raised})`, and the contributors recover the rest.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Two sales of 10 million, one with a tap
# ---------------------------------------


RAISE = 10_000_000


def run_sale(tap, days=30):
    world = bk.contracts.World()
    buyers = [f"buyer{k}" for k in range(10)]
    for name in buyers:
        world.fund(name, RAISE // 10)
    sale = world.deploy("team", bk.fraud.TokenSale, tap, name="sale")
    for name in buyers:
        world.transact(name, sale, "buy", value=RAISE // 10)
    taken = []
    for _ in range(days):
        world.advance(seconds=86_400)
        available = world.view(sale, "available")
        if available:
            world.transact("team", sale, "withdraw", available)
        taken.append(world.balance("team"))
    return world, sale, buyers, taken


world, sale, buyers, open_sale = run_sale(tap=0)
print("no tap: team takes", open_sale[0], "on the first day")
assert open_sale[0] == RAISE

TAP = RAISE // (100 * 86_400)  # About 1% of the raise per day.
world, sale, buyers, tapped = run_sale(tap=TAP)
print("tap: team has taken", tapped[-1], "after 30 days")
for name in buyers[:6]:
    world.transact(name, sale, "vote_refund")
for name in buyers:
    world.transact(name, sale, "refund")
recovered = sum(world.balance(name) for name in buyers)
print("contributors recover", recovered)
assert tapped[-1] + recovered == RAISE and recovered > 0.6 * RAISE

fig, ax = plt.subplots(figsize=(7, 4))
days = range(1, 31)
ax.plot(days, open_sale, color="#dc2626", label="no tap: exit scam on day 1")
ax.plot(days, tapped, color="#2563eb", label=f"DAICO tap of {TAP} per second")
ax.set(xlabel="day", ylabel="ether taken by the team")
ax.set_title("A tap bounds what a vanishing team can take")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A team with a tap could instead propose raising the tap and vote for it
# with tokens it bought back cheaply. What share of the tokens must it hold
# to take everything, and how could a DAICO defend against this?
