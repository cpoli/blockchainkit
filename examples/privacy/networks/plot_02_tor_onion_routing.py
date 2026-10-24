r"""
Onion routing in Tor: fast, but exposed end to end (2004)
=========================================================

Tor wraps traffic in layers like a mix-net, through a circuit of three
relays, but forwards each packet at once: no batching, no reordering. That
makes browsing fast enough to use. The design paper states the price: an
adversary that watches both ends of a circuit can match the packet timing
going in to the timing coming out. Delays shift every packet alike, so the
gaps between packets survive the trip.

An adversary running a fraction :math:`f` of the relays sees both ends of
a random circuit with probability about

.. math::

   \Pr[\text{entry and exit malicious}] \approx f^2 .
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A three-hop circuit
# -------------------
# The guard knows the user, the exit knows the destination, nobody knows both.

guard, middle, exit_ = (
    bk.privacy.MixNode(name, s) for name, s in (("guard", 7), ("middle", 8), ("exit", 9))
)
cell = bk.privacy.wrap(b"GET /", [guard, middle, exit_], "example.org", Random(0))
for relay in (guard, middle, exit_):
    hop, cell = relay.peel(cell)
    print(f"{relay.name} sends to {hop}")

# %%
# Timing correlation
# ------------------
# Fifty users browse at once; the adversary records packet times at
# entry and exit and matches flows by their gaps.

observed = bk.privacy.simulate_flows(50, 30, seed=3)
guesses = bk.privacy.match_flows(observed.entering, observed.leaving)
correct = sum(g == t for g, t in zip(guesses, observed.truth, strict=True))
print(f"flows matched correctly: {correct} of 50")
assert correct == 50

# %%
# How often both ends are watched
# -------------------------------

fractions = [0.05, 0.1, 0.2, 0.3, 0.4]
rates = [
    bk.privacy.circuit_compromise_rate(100, range(int(f * 100)), 20_000, seed=1) for f in fractions
]
for f, rate in zip(fractions, rates, strict=True):
    assert abs(rate - f * f) < 0.02

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(fractions, rates, marker="o", label="simulated circuits")
ax.plot(fractions, [f * f for f in fractions], linestyle="--", color="#64748b", label="$f^2$")
ax.set(xlabel="fraction of relays malicious", ylabel="circuits exposed end to end")
ax.set_title("Low latency trades away timing protection")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Tor clients keep the same entry guard for months. If 10% of relays are
# malicious, what is the chance a user's guard is bad, and why is that
# better than choosing a fresh entry for every circuit?
# A worked solution is in :doc:`/exercises/privacy`.
