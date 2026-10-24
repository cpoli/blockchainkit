r"""
Chaum's mix-nets: untraceable mail (1981)
=========================================

David Chaum wanted to hide who writes to whom, even from someone watching
every wire. A sender wraps its message in one layer of encryption per
*mix*, innermost for the last. Each mix collects a batch, removes one
layer from every message, and sends them on in a random order. The bytes
change at every hop and so does the order, so an observer cannot match
what goes in to what comes out.

Following a message needs every mix's shuffle. If the mixes are
:math:`M_1, \dots, M_k` and the observer learns the permutations of the
corrupt ones, a sender stays hidden among the whole batch as soon as one
mix is honest:

.. math::

   \Pr[\text{link}] = \begin{cases} 1 & \text{all mixes corrupt,} \\
   1/n & \text{otherwise, for a batch of } n. \end{cases}
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Wrapping and peeling
# --------------------
# Each mix learns only the next hop.

mixes = [bk.privacy.MixNode(f"mix{i}", 1_000 + i) for i in range(3)]
onion = bk.privacy.wrap(b"meet at noon", mixes, "bob", Random(1))
for mix in mixes:
    hop, onion = mix.peel(onion)
    print(f"{mix.name} forwards {len(onion):>3} bytes to {hop}")
assert onion == b"meet at noon"

# %%
# A batch through the cascade
# ---------------------------
# Eight senders write to eight recipients at once.

rng = Random(2)
onions = [bk.privacy.wrap(f"note {i}".encode(), mixes, f"r{i}", rng) for i in range(8)]
run = bk.privacy.mix_cascade(onions, mixes, seed=3)
print("delivered:", [recipient for recipient, _ in run.delivered])
for sender in range(8):
    assert run.delivered[run.output_of(sender)][0] == f"r{sender}"

corrupt_sets = {
    "none": frozenset(),
    "mix0": frozenset({0}),
    "mix0, mix2": frozenset({0, 2}),
    "all three": frozenset({0, 1, 2}),
}
candidates = {
    name: sum(len(run.candidates(s, corrupt)) for s in range(8)) / 8
    for name, corrupt in corrupt_sets.items()
}
print(candidates)
assert candidates["mix0, mix2"] == 8 and candidates["all three"] == 1

fig, ax = plt.subplots(figsize=(7, 3.5))
ax.bar(list(candidates), list(candidates.values()), color="#2563eb")
ax.set(xlabel="mixes that reveal their shuffle", ylabel="possible recipients per sender")
ax.set_title("One honest mix hides each sender among the whole batch")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The observer watches the cascade at a quiet hour, when only two
# messages pass. What is the chance of linking a sender now, and what did
# Chaum propose to keep batches large?
# A worked solution is in :doc:`/exercises/privacy`.
