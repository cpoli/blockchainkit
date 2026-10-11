r"""
Myerson's optimal auction and revenue equivalence (1981)
========================================================

Which auction earns the seller the most? Myerson replaced each bidder's
value :math:`v` by its *virtual value*, the marginal revenue of selling to
it,

.. math::

   \varphi(v) = v - \frac{1 - F(v)}{f(v)},

and showed that expected revenue equals the expected virtual value of the
winner. The optimal auction therefore sells to the highest nonnegative
virtual value: for identical bidders, a second-price auction with a
*reserve price* :math:`\varphi^{-1}(0)`, which is :math:`1/2` for values
uniform on :math:`[0, 1]`, however many bidders there are.

The same identity gives *revenue equivalence*: any two auctions that
allocate alike earn the same on average. A first-price auction, in which
bidders shade their bids, and a second-price one, in which they bid their
values, raise exactly the same expected revenue.
"""

# %%
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

# %%
# Revenue against the reserve
# ---------------------------

reserves = np.linspace(0, 0.95, 39)
fig, ax = plt.subplots(figsize=(7, 4.5))
for n, color in ((1, "#dc2626"), (2, "#2563eb"), (4, "#16a34a")):
    revenue = [bk.economics.expected_revenue(n, reserve=r) for r in reserves]
    ax.plot(reserves, revenue, color=color, label=f"{n} bidder{'s' * (n > 1)}")
    best = reserves[int(np.argmax(revenue))]
    assert abs(best - bk.economics.optimal_reserve()) < 0.03
    for auction, marker in (("first-price", "o"), ("second-price", "s")):
        measured = [
            bk.economics.simulate_revenue(auction, n, rounds=4_000, reserve=r, seed=3)
            for r in (0.0, 0.5, 0.8)
        ]
        ax.plot((0.0, 0.5, 0.8), measured, marker, color=color, fillstyle="none")
ax.axvline(bk.economics.optimal_reserve(), color="black", linestyle=":", label="phi(r) = 0")
ax.set(xlabel="reserve price", ylabel="expected revenue")
ax.set_title("Myerson's reserve; circles first-price, squares second-price")
ax.legend()
fig.tight_layout()

# %%
# Revenue equivalence
# -------------------

for n in (2, 5):
    theory = bk.economics.expected_revenue(n, reserve=0.5)
    first = bk.economics.simulate_revenue("first-price", n, rounds=30_000, reserve=0.5, seed=8)
    second = bk.economics.simulate_revenue("second-price", n, rounds=30_000, reserve=0.5, seed=8)
    print(f"{n} bidders: theory {theory:.4f}, first-price {first:.4f}, second-price {second:.4f}")
    assert abs(first - theory) < 0.01 and abs(second - theory) < 0.01

plt.show()

# %%
# Exercise
# --------
# The reserve helps most with one bidder. With a single bidder whose value
# is uniform on [0, 1], the seller just posts a price p. Show that its
# revenue is p (1 - p) and that the best price is Myerson's reserve.
# A worked solution is in :doc:`/exercises/economics`.
