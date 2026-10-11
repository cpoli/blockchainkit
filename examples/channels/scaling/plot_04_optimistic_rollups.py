r"""
Optimistic rollups and fraud-proof challenge windows (2019)
===========================================================

An optimistic rollup, as Adler and Quintyne-Collins proposed in 2019,
posts its batches and state roots with no proof. A root becomes final once
a challenge window has passed, and anyone who recomputes a batch and
disagrees can prove fraud within it, taking the proposer's bond. The proof
is found by bisection, as in Arbitrum (Kalodner et al., 2018): the two
sides compare intermediate state roots, halving the disputed range each
round, until they disagree about one transaction, which the chain
re-executes. A batch of ``n`` transactions needs

.. math::

   \lceil \log_2 n \rceil

rounds, and one honest watcher suffices; the price is that withdrawals
wait for the window.
"""

# %%
from random import Random

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A fraudulent batch, challenged
# ------------------------------

rng = Random(2)
accounts = [f"user{i}" for i in range(10)]
genesis = {a: 100 for a in accounts}
rollup = bk.channels.OptimisticRollup(genesis, window=50, bond=25)
batch = [
    bk.channels.Transfer(rng.choice(accounts), rng.choice(accounts), rng.randint(1, 40))
    for _ in range(64)
]
_, honest = bk.channels.execute_batch(genesis, batch)
# From transaction 36 on, the proposer's roots include 1,000 coins for itself.
start = bk.channels.execute_batch(genesis, batch[:36])[0] | {"mallory": 1_000}
_, tail = bk.channels.execute_batch(start, batch[36:])
forged = (*honest[:37], *tail[1:])
rollup.propose("mallory", batch, forged, height=1)
proof = rollup.challenge(0, "watcher", height=30)
print(f"fraud at transaction {proof.step}, found in {proof.rounds} rounds")
assert proof.step == 36 and proof.rounds == 6 and rollup.payouts == {"watcher": 25}

# %%
# Bisection rounds grow with log n
# --------------------------------

sizes = [2**k for k in range(1, 15)]
rounds = []
for n in sizes:
    truth = [bytes([0])] + [i.to_bytes(4, "big") for i in range(n)]
    lie = truth[: n // 3 + 1] + [b"x" + root for root in truth[n // 3 + 1 :]]
    rounds.append(bk.channels.bisect(lie, truth)[1])
assert rounds == [k for k in range(1, 15)]

# %%
# The price of optimism: waiting to withdraw
# ------------------------------------------

honest_rollup = bk.channels.OptimisticRollup(genesis, window=50)
honest_rollup.propose("operator", batch, honest, height=1)
finalized_at = next(h for h in range(1, 200) if honest_rollup.finalize(height=h))
print("an honest batch becomes final at height", finalized_at)
assert finalized_at == 51

fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
left.semilogx(sizes, rounds, "o-", color="#2563eb", base=2)
left.set(xlabel="transactions in the batch", ylabel="bisection rounds")
left.set_title("One disputed step among n, in log2 n rounds")
right.bar(["zk-rollup", "optimistic rollup"], [1, finalized_at - 1], color=["#16a34a", "#d97706"])
right.set(ylabel="blocks until a withdrawal is final")
right.set_title("Validity proofs vs. challenge windows")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A challenge window must outlast a censorship attack: an attacker who can
# keep the honest challenger's transaction out of ``c`` consecutive blocks
# wins if ``c`` reaches the window. With block producers chosen at random
# and a fraction ``f`` of them censoring, how long a window makes the
# attack succeed with probability below one in a billion?
# A worked solution is in :doc:`/exercises/channels`.
