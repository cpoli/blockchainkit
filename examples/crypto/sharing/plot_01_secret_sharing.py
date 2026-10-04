"""
Shamir's secret sharing: reconstruct a secret without storing it whole (1979)
=============================================================================

The secret is the constant coefficient of a random polynomial. Any threshold
number of evaluations determines it; fewer evaluations leave it undetermined.
Arithmetic takes place in a prime field, not over floating-point reals.

What to look for
----------------

Watch every three-person subset recover the same secret. Two shares fit several possible
secrets; the curves illustrate why the missing share matters.

Read cells in order. An ``assert`` that produces no output has passed.
The final exercise asks you to change an input and explain the result.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
See :doc:`/tutorials/solutions` for a worked answer to the exercise.
"""

# %%
from itertools import combinations
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

secret, prime = 42, 101
shares = bk.crypto.split_secret(secret, 3, 5, prime, randbelow=Random(7).randrange)
for subset in combinations(shares, 3):
    assert bk.crypto.recover_secret(subset, prime) == secret
print("Five shares:", shares)
print("Every one of the ten three-share subsets recovers", secret)

# %%
# Two points admit every possible secret in a quadratic sharing scheme
# --------------------------------------------------------------------
# For each candidate constant, solve for the remaining two coefficients.
(x1, y1), (x2, y2) = shares[:2]
candidate_polynomials = []
for candidate in (0, 20, 42, 80):
    # y_i - candidate = a*x_i + b*x_i**2
    determinant = (x1 * x2**2 - x2 * x1**2) % prime
    a = ((y1 - candidate) * x2**2 - (y2 - candidate) * x1**2) * pow(determinant, -1, prime) % prime
    b = (x1 * (y2 - candidate) - x2 * (y1 - candidate)) * pow(determinant, -1, prime) % prime
    candidate_polynomials.append((candidate, a, b))
    assert (candidate + a * x1 + b * x1**2) % prime == y1
    assert (candidate + a * x2 + b * x2**2) % prime == y2

# %%
fig, ax = plt.subplots(figsize=(8, 4))
xs = list(range(7))
for candidate, a, b in candidate_polynomials:
    ax.scatter(
        xs, [(candidate + a * x + b * x**2) % prime for x in xs], label=f"secret={candidate}"
    )
ax.scatter([x1, x2], [y1, y2], s=180, facecolors="none", edgecolors="black", label="known shares")
ax.set(
    xlabel="Evaluation coordinate x",
    ylabel="Polynomial value modulo 101",
    title="Two shares, many possible secrets",
)
ax.legend(ncol=2)
fig.tight_layout()

# %%
# Exercise
# --------
# Change a share before reconstruction. The result may be wrong without any
# error: plain Shamir sharing does not authenticate shares. What additional
# mechanism would participants need to detect dishonest contributions?
