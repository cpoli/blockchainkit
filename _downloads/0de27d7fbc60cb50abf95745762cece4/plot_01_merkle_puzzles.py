"""
Merkle's puzzles: the first public-key exchange (1974-1978)
===========================================================

As a student, Ralph Merkle asked whether two strangers could agree on a key
over a public channel. His answer used only a symmetric cipher. Alice
publishes many puzzles, each a session key locked by a deliberately weak
key. Bob solves one at random and announces only its label. An eavesdropper
does not know which puzzle Bob picked, and must open about half of them.

What to look for
----------------

Bob's work stays flat while the eavesdropper's grows with the number of
puzzles. With N puzzles of N-trial difficulty, honest parties do O(N) work
and the attacker O(N**2): a real but only *quadratic* advantage. Diffie and
Hellman's exponential gap came next.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# One exchange
# ------------
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

bits = 8
puzzles, alice_table = bk.crypto.merkle_puzzles(64, bits, randbits=Random(78).getrandbits)
bob = bk.crypto.solve_puzzle(puzzles[Random(1).randrange(64)], bits)
print("Bob announces", bob.puzzle_id.hex(), "after", bob.trials, "trials")
assert alice_table[bob.puzzle_id] == bob.key  # Alice looks the key up: shared secret.

# %%
# What the eavesdropper must do
# -----------------------------
eve_trials = 0
for puzzle in puzzles:
    opened = bk.crypto.solve_puzzle(puzzle, bits)
    eve_trials += opened.trials
    if opened.puzzle_id == bob.puzzle_id:
        assert opened.key == bob.key
        break
print("Eve needed", eve_trials, "trials")

# %%
# Honest work versus attack work
# ------------------------------
counts = [2**k for k in range(2, 9)]
bob_work, eve_work = [], []
for count in counts:
    puzzles, _ = bk.crypto.merkle_puzzles(count, bits, randbits=Random(count).getrandbits)
    trials = [bk.crypto.solve_puzzle(p, bits).trials for p in puzzles]
    bob_work.append(sum(trials) / count)  # One puzzle, on average.
    eve_work.append(sum(trials) / 2)  # Half the puzzles, on average.
fig, ax = plt.subplots(figsize=(7, 4))
ax.loglog(counts, bob_work, "o-", label="Bob: one puzzle")
ax.loglog(counts, eve_work, "s-", label="Eve: half of the puzzles")
ax.set(xlabel="number of puzzles", ylabel="trials", title="A quadratic gap from symmetric crypto")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Set the number of puzzles to 2**bits. Express Alice's, Bob's and Eve's work
# in terms of N = 2**bits. If honest parties can afford 2**30 operations, how
# much work does the attacker face? Compare with Diffie-Hellman.
