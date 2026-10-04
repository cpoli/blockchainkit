"""
Vector clocks: detecting concurrency (Fidge and Mattern 1988)
=============================================================

A Lamport timestamp orders events but cannot tell whether two events are
causally related. Fidge and Mattern independently gave each process a vector
of counters, one per process. Entry ``q`` of an event's vector counts the
events at process ``q`` that happened before or at it, so comparing two
vectors entry by entry answers exactly whether one event caused the other
or the two are concurrent.

What to look for
----------------

For every pair of events, vectors and Lamport timestamps never disagree on a
causal pair, but only vectors recognize the concurrent pairs. Concurrent
updates are the ones a replicated system must reconcile; two conflicting
transactions broadcast at the same time are concurrent in exactly this
sense.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
See :doc:`/exercises/network` for a worked solution to the exercise.
"""

# %%
# The same history as the Lamport example
# ---------------------------------------
import itertools

import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

history = [
    [("send", "m1"), ("local", "a"), ("receive", "m3")],
    [("receive", "m1"), ("send", "m2")],
    [("local", "b"), ("receive", "m2"), ("send", "m3")],
]
vectors = bk.network.vector_timestamps(history)
lamport = bk.network.lamport_timestamps(history)
events = [(p, i) for p, row in enumerate(history) for i in range(len(row))]
names = [f"P{p}:{history[p][i][1]}" for p, i in events]
for name, (p, i) in zip(names, events, strict=True):
    print(f"{name:7s} Lamport {lamport[p][i]}  vector {vectors[p][i]}")

# %%
# Classify every pair
# -------------------
relation = np.zeros((len(events), len(events)))
for (x, (p, i)), (y, (q, j)) in itertools.product(enumerate(events), repeat=2):
    a, b = vectors[p][i], vectors[q][j]
    if bk.network.happened_before(a, b):
        relation[x, y] = 1
        assert lamport[p][i] < lamport[q][j]  # Causal order implies Lamport order.
    elif bk.network.happened_before(b, a):
        relation[x, y] = -1
concurrent = int((relation[np.triu_indices(len(events), 1)] == 0).sum())
print(concurrent, "concurrent pairs")
assert bk.network.concurrent(vectors[0][1], vectors[2][0])  # "a" and "b".

fig, ax = plt.subplots(figsize=(6, 5))
ax.imshow(relation, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(events)), names, rotation=60)
ax.set_yticks(range(len(events)), names)
ax.set_title("row -> column (red), column -> row (blue), concurrent (grey)")
fig.tight_layout()

# %%
# Exercise
# --------
# A vector clock grows with the number of processes. Why can no scalar
# clock capture concurrency exactly? Hint: in this history, find events x,
# y, z with x concurrent to y and y concurrent to z, but x before z. Could
# "equal timestamps" ever mean "concurrent"?
