"""
Pricing via processing: making junk mail expensive (Dwork and Naor 1992)
========================================================================

Dwork and Naor proposed that a sender attach to each message the answer to
a puzzle that is moderately hard to solve but easy to check. One of their
pricing functions is a square root modulo a prime: computing it takes a
full modular exponentiation, checking it a single multiplication. The idea
of a cost asymmetry became proof of work.

What to look for
----------------

The work to compute a root grows with the size of the prime; checking stays
at one multiplication. The asymmetry here is only logarithmic, which is why
Hashcash (the next example) switched to hash puzzles with tunable,
exponential cost.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Price one message
# -----------------
import matplotlib.pyplot as plt

import blockchainkit as bk

p = 2**61 - 1  # A Mersenne prime, = 3 mod 4.
message_id = int.from_bytes(bk.crypto.sha256(b"Hello, buy my product!")[:8], "big") % p
square = message_id * message_id % p  # Choose a puzzle with a guaranteed root.
answer = bk.consensus.modular_square_root(square, p)
assert answer.root * answer.root % p == square  # The recipient checks with one multiplication.
print(f"sender: {answer.multiplications} multiplications; recipient: 1")

# %%
# Cost against prime size
# -----------------------
primes = [n for n in range(1000, 2**20, 997) if bk.crypto.is_prime(n) and n % 4 == 3][:40]
primes += [2**31 - 1, 2**61 - 1]
work = [bk.consensus.modular_square_root(4, q).multiplications for q in primes]
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.semilogx(primes, work, "o", base=2, label="compute the root")
ax.semilogx(primes, [1] * len(primes), "-", base=2, color="black", label="verify it")
ax.set(
    xlabel="prime p",
    ylabel="modular multiplications",
    title="Computing costs about 1.5 log2 p; checking costs 1",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Dwork and Naor also wanted a *shortcut*: a trapdoor letting a trusted
# authority price messages cheaply. Why is a logarithmic asymmetry too small
# to stop a spammer with a fast computer, and how does Hashcash fix that?
