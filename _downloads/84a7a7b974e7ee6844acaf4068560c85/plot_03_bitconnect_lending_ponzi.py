r"""
BitConnect and lending-platform Ponzis (2018)
=============================================

BitConnect took bitcoin deposits into a "lending program" and credited
interest of around 1% a day, said to come from a trading bot. Nothing was
traded: interest and withdrawals were paid out of new deposits, and
recruiters earned commissions down several levels of the investors they
brought in. Credited balances compound, so the liabilities grow as

.. math::

   L_t = L_{t-1}(1 + i) + D_t - W_t, \qquad (1.01)^{365} \approx 38,

while the cash grows only with new deposits. Texas and North Carolina
regulators ordered it to stop in January 2018, deposits dried up, and the
platform closed within two weeks; the SEC later charged it with a
two-billion-dollar fraud.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.fraud.visualizers import plot_ponzi

# %%
# Deposits grow, then stop at a regulator's order
# -----------------------------------------------

deposits = [100 * 1.03**day for day in range(120)] + [10.0] * 60
run = bk.fraud.simulate_lending_ponzi(deposits, daily_rate=0.01, withdrawal_rate=0.02)
print(f"collapsed on day {run.collapse}; raised {run.raised:,.0f}, paid out {run.repaid:,.0f}")
print(f"balances credited to investors at the end: {run.owed[-1]:,.0f}")
assert run.collapse is not None and 120 < run.collapse < 180
assert run.cash[-1] == 0 and run.owed[-1] > 0.5 * run.raised  # Owed, with nothing left.

fig, ax = plt.subplots(figsize=(9, 4))
plot_ponzi(run, ax=ax)
ax.set_xlabel("day")
ax.set_yscale("symlog", linthresh=100)
fig.tight_layout()

# %%
# The referral pyramid
# --------------------
# Each investor recruits two more, three levels deep, and every recruiter
# earns 7%, 3%, 2% and 1% on the deposits one to four levels below it.

sponsors, deposits_by = {}, {"root": 1_000.0}
level = ["root"]
for _ in range(4):
    nxt = []
    for parent in level:
        for k in range(2):
            child = f"{parent}.{k}"
            sponsors[child] = parent
            deposits_by[child] = 1_000.0
            nxt.append(child)
    level = nxt
commissions = bk.fraud.referral_commissions(sponsors, deposits_by)
by_depth = {}
for name, earned in commissions.items():
    by_depth.setdefault(name.count("."), []).append(earned)
averages = [sum(v) / len(v) for _, v in sorted(by_depth.items())]
print("average commission by depth:", [round(a) for a in averages])
assert averages == sorted(averages, reverse=True)  # The top of the pyramid earns most.

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(range(len(averages)), averages, color="#9333ea")
ax.set(xlabel="depth in the referral tree", ylabel="commission earned")
ax.set_title("Commissions flow to the top")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# With 1% daily interest and no withdrawals, how fast must daily deposits
# grow for the cash to keep pace with the credited balances? Compare with
# the breakeven growth of Ponzi's own scheme.
