r"""
Proposer-builder separation and MEV-Boost (2022)
================================================

Extracting the value of transaction ordering takes searchers, private order
flow and fast infrastructure. A validator that has them earns more per
unit of stake than one that does not, and so attracts more stake: MEV
pushes proof of stake toward a few large operators. Proposer-builder
separation splits the roles. Specialized *builders* assemble blocks and
bid for the slot; the proposer, any validator, signs the best bid.

If builders bid their values :math:`v_b = f + \sigma_b M` for fees
:math:`f`, MEV :math:`M` and skill :math:`\sigma_b`, the proposer receives
at least the second-highest value,

.. math::

   \text{revenue} \ge v_{(2)} = f + \sigma_{(2)} M,

so with competitive builders a solo validator earns nearly as much per
slot as a sophisticated one. Flashbots' MEV-Boost, launched with Ethereum's
move to proof of stake in September 2022, runs this auction outside the
protocol, through relays the proposer must trust.
"""

# %%
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

# %%
# A sophisticated operator and two solo stakers
# ---------------------------------------------

stakes = {"operator": 64, "solo A": 32, "solo B": 32}
options = {"sophisticated": {"operator"}, "slots": 20_000, "fees": 0.05, "mev": 0.05}
runs = {}
for label, separated, builders in (
    ("no PBS", False, {}),
    ("PBS, two strong builders", True, {"b1": 1.0, "b2": 0.95}),
    ("PBS, one strong builder", True, {"b1": 1.0, "b2": 0.3}),
):
    runs[label] = bk.economics.simulate_pbs(
        stakes, separated=separated, builders=builders, seed=9, **options
    )
    per_stake = {v: runs[label].revenue_per_stake(v) * 32 for v in stakes}
    print(label, {v: round(r, 1) for v, r in per_stake.items()})

alone = runs["no PBS"]
assert alone.revenue_per_stake("operator") > 1.7 * alone.revenue_per_stake("solo A")
boosted = runs["PBS, two strong builders"]
assert boosted.revenue_per_stake("operator") < 1.1 * boosted.revenue_per_stake("solo A")

fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))
xs = np.arange(len(stakes))
for i, (label, run) in enumerate(runs.items()):
    left.bar(
        xs + (i - 1) * 0.27,
        [run.revenue_per_stake(v) * 32 for v in stakes],
        0.27,
        label=label,
    )
left.set_xticks(xs, list(stakes))
left.set(ylabel="revenue per 32 staked")
left.set_title("Builder competition equalizes validators")
left.legend(fontsize=8)

# %%
# How much competition is enough?
# -------------------------------

skills = np.linspace(0, 1, 11)
ratio = []
for skill in skills:
    run = bk.economics.simulate_pbs(
        stakes, builders={"b1": 1.0, "b2": float(skill)}, seed=9, **options
    )
    ratio.append(run.revenue_per_stake("solo A") / run.revenue_per_stake("operator"))
right.plot(skills, ratio, "o-", color="#2563eb")
right.axhline(1, color="black", linestyle=":")
right.set(xlabel="second builder's skill", ylabel="solo revenue / operator revenue")
right.set_title("Solo stakers get what the runner-up builder would pay")
fig.tight_layout()
assert ratio[0] < ratio[-1] and ratio[-1] > 0.95

plt.show()

# %%
# Exercise
# --------
# The proposer receives the second-highest value, but the winning builder
# keeps the gap between its value and that price. With one builder of skill
# 1 and one of skill 0.5, what fraction of the MEV does the winning builder
# keep, and why might it pay to integrate a builder with a large validator?
