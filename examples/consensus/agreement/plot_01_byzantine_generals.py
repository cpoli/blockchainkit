"""
The Byzantine generals problem (Lamport, Shostak and Pease 1982)
================================================================

Generals surrounding a city must agree to attack or retreat, communicating
by messenger, while some of them are traitors who tell different generals
different things. Lamport, Shostak and Pease proved agreement possible if
and only if more than two thirds of the generals are loyal, and gave the
oral-messages algorithm OM(m): every lieutenant relays what it heard, and
everyone takes a majority.

What to look for
----------------

With four generals and one traitor, the loyal ones always agree, and follow
a loyal commander. With three generals and one traitor, a loyal lieutenant
can be talked out of the commander's order: n > 3m is necessary. This
3f + 1 bound reappears in every Byzantine fault-tolerant blockchain.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Four generals, one traitor anywhere
# -----------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

for traitor in range(4):
    result = bk.consensus.oral_messages(4, {traitor}, "attack", rounds=1)
    assert result.agreement and result.validity
    print(f"traitor {traitor}: loyal decisions {result.decisions}")

# %%
# Three generals are not enough
# -----------------------------
result = bk.consensus.oral_messages(3, {2}, "attack", rounds=1)
print("loyal lieutenant 1 decides:", result.decisions[1], "although the commander said attack")
assert not result.validity

# %%
# When does OM(1) survive one traitor?
# ------------------------------------
sizes = range(3, 9)
survives = []
for n in sizes:
    runs = [bk.consensus.oral_messages(n, {t}, "attack", rounds=1) for t in range(n)]
    survives.append(all(r.agreement and r.validity for r in runs))
assert survives == [n > 3 for n in sizes]
fig, ax = plt.subplots(figsize=(7, 3))
ax.bar([str(n) for n in sizes], survives, color=["#16a34a" if ok else "#dc2626" for ok in survives])
ax.set(
    xlabel="generals n (one traitor)",
    yticks=[0, 1],
    yticklabels=["fails", "works"],
    title="OM(1) needs n > 3",
)
fig.tight_layout()

# %%
# Exercise
# --------
# Run ``oral_messages(7, {a, b}, "attack", rounds=2)`` for every pair of
# traitors, then with rounds=1. Why does tolerating m traitors need m + 1
# rounds of relaying?
