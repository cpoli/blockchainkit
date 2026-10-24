r"""
BCH error-correcting codes (1959-1960)
======================================

Alexis Hocquenghem in 1959, and Raj Chandra Bose and Dijen Ray-Chaudhuri in
1960, found how to build binary codes that correct any chosen number t of
flipped bits. A word of n = 2**m - 1 bits is read as a polynomial, and the
codewords are the multiples of a generator g(x) that vanishes at
:math:`\alpha, \alpha^2, \dots, \alpha^{2t}` in GF(2**m). Any two codewords
then differ in at least

.. math::

   d \ge 2t + 1

bits, so a received word with at most t errors is nearer to its codeword
than to any other. The same construction over GF(32) gives Bech32's
checksum. Here a (15, 7) code corrects two errors, and three errors defeat
it.
"""

# %%
import random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Correcting two errors
# ---------------------

code = bk.wallets.BCHCode(4, 2)
print(f"n = {code.n}, k = {code.k}, designed distance {code.designed_distance}")
print("generator g(x) =", bin(code.generator))
message = [1, 0, 1, 1, 0, 0, 1]
word = list(code.encode(message))
received = list(word)
for i in (2, 11):
    received[i] ^= 1
print("sent    ", "".join(map(str, word)))
print("received", "".join(map(str, received)))
print("syndromes", code.syndromes(received))
decoded = code.decode(received)
print("corrected positions", decoded.errors)
assert decoded.corrected and list(decoded.message) == message

# %%
# What each number of errors does
# -------------------------------
# For every count of flipped bits, the share of words decoded to the right
# message, wrongly corrected, or refused.

rng = random.Random(1960)
outcomes = {"right": [], "wrong": [], "refused": []}
counts = range(6)
for errors in counts:
    tally = dict.fromkeys(outcomes, 0)
    for _ in range(300):
        sent = [rng.randrange(2) for _ in range(code.k)]
        noisy = list(code.encode(sent))
        for i in rng.sample(range(code.n), errors):
            noisy[i] ^= 1
        result = code.decode(noisy)
        if not result.corrected:
            tally["refused"] += 1
        elif list(result.message) == sent:
            tally["right"] += 1
        else:
            tally["wrong"] += 1
    for key, value in tally.items():
        outcomes[key].append(value / 300)
assert outcomes["right"][:3] == [1.0, 1.0, 1.0]
assert outcomes["right"][3] < 0.1

fig, ax = plt.subplots(figsize=(6, 4))
bottom = [0.0] * len(counts)
for key, color in (("right", "#16a34a"), ("refused", "#64748b"), ("wrong", "#dc2626")):
    ax.bar(counts, outcomes[key], bottom=bottom, color=color, label=key)
    bottom = [b + v for b, v in zip(bottom, outcomes[key], strict=True)]
ax.axvline(code.t + 0.5, color="black", linestyle="--")
ax.set(xlabel="bits flipped", ylabel="share of words", xticks=list(counts))
ax.set_title("BCH(15, 7): up to t = 2 errors are always corrected")
ax.legend()
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# How many message bits does a code of length 31 keep if it must correct
# three errors?
# A worked solution is in :doc:`/exercises/wallets`.
