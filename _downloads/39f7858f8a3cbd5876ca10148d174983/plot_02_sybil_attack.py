"""
The Sybil attack: identities are cheap (Douceur 2002)
=====================================================

In an open network, nothing stops one person from running many nodes.
Douceur showed that without a trusted authority to certify identities, an
attacker can always present as many as its resources allow, and any
protocol that counts identities, such as voting or choosing which nodes
store a key, can be taken over. Proof of work is one answer: it makes
influence cost computation instead of counting identities.

What to look for
----------------

When nodes choose their own identifiers, eight Sybils placed next to a key
become the eight closest nodes, so every honest lookup lands on the
attacker. When identifiers must be the hash of a public key, the attacker
has to grind keys instead: the cost doubles with every extra bit it must
match, but it is only a cost, not a barrier.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# Chosen identifiers
# ------------------
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

bits = 20
honest = Random(2).sample(range(2**bits), 300)
key = bk.network.node_id(b"block 7", bits)
sybils = [key ^ i for i in range(1, 9) if key ^ i not in honest]
network = bk.network.KademliaNetwork(honest + sybils, bits=bits, k=4, seed=1)
captured = [network.lookup(source, key).found in sybils for source in honest]
print(f"{sum(captured)} of {len(honest)} honest lookups end at a Sybil")
assert all(captured)
assert set(network.closest(key, len(sybils))) == set(sybils)

# %%
# Identifiers bound to keys
# -------------------------
# To land within d leading bits of the key, the attacker must try about
# 2**d public keys per Sybil.
costs = {}
for d in range(4, 15, 2):
    tries = 0
    for _ in range(4):  # Four Sybils per prefix length.
        while True:
            tries += 1
            candidate = bk.network.node_id(f"sybil key {tries}".encode(), bits)
            if (candidate ^ key) >> (bits - d) == 0:
                break
    costs[d] = tries / 4
print({d: round(c) for d, c in costs.items()})
assert costs[14] > 50 * costs[4]

nearest = min(bk.network.xor_distance(h, key) for h in honest)
print("closest honest node shares", bits - nearest.bit_length(), "leading bits with the key")

fig, ax = plt.subplots(figsize=(6, 4))
ax.semilogy(list(costs), list(costs.values()), "o", label="measured")
ax.semilogy(list(costs), [2**d for d in costs], color="black", label="2**d")
ax.set(xlabel="leading bits matched d", ylabel="key attempts per Sybil", title="Grinding cost")
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# S/Kademlia (2007) additionally requires each node ID to come with a
# proof-of-work puzzle solution. How does that change the attacker's cost
# compared with the honest nodes' cost of joining once?
