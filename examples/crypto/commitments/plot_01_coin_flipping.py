"""
Coin flipping by telephone: hash commitments (Blum 1981)
========================================================

Alice and Bob, on the phone, want a fair coin toss. If Alice calls first,
Bob can lie. Blum's fix: Alice *commits* to her call, Bob announces the coin,
then Alice opens the commitment. A commitment must be binding (Alice cannot
change her call) and hiding (Bob cannot read it early).

What to look for
----------------

A salted hash commitment opens only to the committed value. Without a
secret salt, Bob can hash both possible calls and read Alice's choice: a
commitment to a guessable value needs randomness to hide it.

The history behind this experiment: :doc:`/history/crypto_breakthroughs`.
"""

# %%
# Commit, reveal, verify
# ----------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

salt = bytes(range(32))  # A real salt comes from secrets.token_bytes(32).
commitment = bk.crypto.commit(b"heads", salt)
bob_coin = b"tails"  # Bob announces after seeing only the commitment.
assert bk.crypto.verify_commitment(commitment, b"heads", salt)
assert not bk.crypto.verify_commitment(commitment, b"tails", salt)  # Binding.
print(
    "Alice called heads; the coin was", bob_coin.decode(), "-> Bob wins, and Alice cannot deny it"
)

# %%
# Why the salt matters
# --------------------
unsalted = bk.crypto.sha256(b"heads")
guesses = {call: bk.crypto.sha256(call) for call in (b"heads", b"tails")}
recovered = next(call for call, h in guesses.items() if h == unsalted)
assert recovered == b"heads"  # Bob reads the call: no hiding without a salt.

# %%
# A thousand fair flips
# ---------------------
# The coin is the XOR of Alice's committed bit and Bob's bit: fair if either
# party is honest.
from random import Random

rng = Random(1981)
outcomes = []
for _ in range(1000):
    alice_bit, alice_salt = bytes([rng.getrandbits(1)]), rng.randbytes(32)
    sealed = bk.crypto.commit(alice_bit, alice_salt)  # Sent first.
    bob_bit = rng.getrandbits(1)  # Bob replies without being able to read it.
    assert bk.crypto.verify_commitment(sealed, alice_bit, alice_salt)  # Then Alice opens.
    outcomes.append(alice_bit[0] ^ bob_bit)
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.bar(["0", "1"], [outcomes.count(0), outcomes.count(1)], color="#2563eb")
ax.set(ylabel="flips", title="XOR of a committed bit and a reply")
fig.tight_layout()
assert 430 < outcomes.count(1) < 570

# %%
# Exercise
# --------
# Commitments are everywhere in this package: name where a Schnorr signature
# commits before seeing a challenge, and where a block commits to its
# transactions. Why does a commitment scheme need *both* properties for the
# coin toss to be fair?
