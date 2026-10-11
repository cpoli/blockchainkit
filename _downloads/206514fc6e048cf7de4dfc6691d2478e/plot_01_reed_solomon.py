r"""
Reed-Solomon codes: recovering lost and corrupted symbols (1960)
================================================================

Reed and Solomon treated ``k`` symbols of data as a polynomial of degree
below ``k`` over a finite field, and sent its values at ``n`` points.
Two such polynomials agree on at most ``k - 1`` points, so any ``k`` of the
``n`` values determine all the others. The code survives the loss of up to
``n - k`` symbols, and up to ``(n - k) / 2`` symbols that arrive wrong:

.. math::

   2\,(\text{errors}) + (\text{erasures}) \le n - k.

The same code protects CDs and QR codes, and, on blockchains, lets a block
be rebuilt from any half of its extended shares.
"""

# %%
from contextlib import suppress
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.channels.visualizers import plot_shares

# %%
# Five letters, eleven shares
# ---------------------------
# The data are the polynomial's values at 0, ..., 4; the extension adds its
# values at 5, ..., 10.

message = b"HELLO"
k, n = len(message), 11
codeword = bk.channels.rs_encode(list(message), n)
assert codeword[:k] == tuple(message)

rng = Random(1)
kept = sorted(rng.sample(range(n), k))
print("kept shares at", kept)
recovered = bk.channels.rs_recover({i: codeword[i] for i in kept}, k, n)
assert bytes(recovered[:k]) == message

# %%
# Correcting errors with Berlekamp and Welch
# ------------------------------------------
# With no erasures, n - k = 6 spare symbols correct 3 wrong ones. For each
# number of errors, corrupt random positions and try to decode.

trials, rates = 40, []
error_counts = range(0, 7)
for errors in error_counts:
    decoded = 0
    for _ in range(trials):
        received = list(codeword)
        for i in rng.sample(range(n), errors):
            received[i] = (received[i] + rng.randrange(1, 65_537)) % 65_537
        with suppress(ValueError):  # Too many errors to correct.
            decoded += bk.channels.rs_decode(received, k) == tuple(message)
    rates.append(decoded / trials)
print("decoding success by number of errors:", rates)
assert rates[:4] == [1.0] * 4 and max(rates[4:]) < 1

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
plot_shares(bk.channels.commit_shares(k, codeword), withheld=set(range(n)) - set(kept), ax=left)
left.set_title("Any 5 of the 11 shares rebuild the rest")
right.bar(error_counts, rates, color=["#16a34a" if e <= 3 else "#dc2626" for e in error_counts])
right.axvline(3.5, color="black", linestyle="--", label="(n - k) / 2")
right.set(xlabel="symbols corrupted", ylabel="fraction decoded correctly")
right.set_title("Errors are corrected up to half the redundancy")
right.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Combine erasures and errors: with ``n = 11`` and ``k = 5``, erase two
# symbols (pass ``None``) and corrupt some others. How many corruptions can
# :func:`~blockchainkit.channels.systems.reed_solomon.rs_decode` still
# correct, and does it match the bound above?
# A worked solution is in :doc:`/exercises/channels`.
