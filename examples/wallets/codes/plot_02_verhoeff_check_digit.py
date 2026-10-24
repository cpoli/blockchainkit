r"""
Verhoeff's check digit and detecting transpositions (1969)
==========================================================

Jacobus Verhoeff studied the errors Dutch clerks made when copying
numbers: most were one wrong digit, and most of the rest were two
neighbouring digits swapped. A check digit chosen so that the digit sum is
a multiple of 10 catches every wrong digit but no swap, since addition
commutes. Luhn's scheme, used on payment cards, catches every swap but
09 and 90. Verhoeff catches all of them by computing in the dihedral group
D5, where :math:`a * b \ne b * a`, and permuting each digit by its
position:

.. math::

   \sigma^{0}(a_0) * \sigma^{1}(a_1) * \cdots * \sigma^{k}(a_k) = 0 .

Base58Check and Bech32 addresses do the same job, at the scale of a whole
string.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.wallets.visualizers import plot_detection_rates

# %%
# Check digits on one number
# --------------------------

number = "236"
for scheme in ("sum", "luhn", "verhoeff"):
    digit, valid = bk.wallets.CHECK_SCHEMES[scheme]
    word = number + digit(number)
    swapped = word[1] + word[0] + word[2:]
    print(f"{scheme:9} {word}  swap {swapped} caught: {not valid(swapped)}")
assert bk.wallets.verhoeff_valid("2363") and not bk.wallets.verhoeff_valid("3263")

# %%
# Luhn's blind spot
# -----------------

print("Luhn digit of 09 and 90:", bk.wallets.luhn_digit("09"), bk.wallets.luhn_digit("90"))
print(
    "Verhoeff digit of 09 and 90:", bk.wallets.verhoeff_digit("09"), bk.wallets.verhoeff_digit("90")
)
assert bk.wallets.luhn_digit("09") == bk.wallets.luhn_digit("90")

# %%
# Every error on every three-digit number
# ---------------------------------------

rates = [bk.wallets.detection_rates(s, 3) for s in ("sum", "luhn", "verhoeff")]
for r in rates:
    print(f"{r.scheme:9} single errors {r.single_errors:.1%}, swaps {r.transpositions:.1%}")
assert rates[2].single_errors == rates[2].transpositions == 1.0

ax = plot_detection_rates(rates)
ax.set_title("Only a non-commuting group catches every swap")
plt.show()

# %%
# Exercise
# --------
# Which pairs of different digits ab can Luhn's scheme not tell from ba?
# A worked solution is in :doc:`/exercises/wallets`.
