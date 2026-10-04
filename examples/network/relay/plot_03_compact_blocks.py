"""
Compact blocks: send what the peer lacks (Corallo, BIP 152, 2016)
=================================================================

By the time a block is found, peers have usually already received most of
its transactions as they were broadcast. Matt Corallo's compact blocks
(BIP 152) send only the header and a 6-byte short ID per transaction; the
receiver rebuilds the block from its mempool and asks for the few it lacks.
Short IDs are salted per block, so an attacker cannot craft transactions
whose IDs collide in every block.

What to look for
----------------

With a full mempool a 500 kB block shrinks to about 12 kB, in a single
round trip. The first missing transaction adds a second round trip, and each
one must then be sent in full, so the saving shrinks linearly as the
mempool's coverage falls. Shrinking the short IDs to a single byte backfires:
with 2000 transactions, every ID becomes ambiguous.

The history behind this experiment: :doc:`/history/network_breakthroughs`.
"""

# %%
# A 2000-transaction block
# ------------------------
from random import Random

import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

rng = Random(1)
block = [rng.randbytes(250) for _ in range(2000)]
others = [rng.randbytes(250) for _ in range(3000)]  # Unrelated mempool entries.
full = bk.network.compact_block_relay(block, block + others)
print(f"full {full.full_bytes} bytes, compact {full.compact_bytes} bytes")
assert full.missing == 0 and full.round_trips == 1
assert full.compact_bytes < full.full_bytes / 40

# %%
# As the mempool misses more of the block
# ---------------------------------------
coverage = np.linspace(1.0, 0.5, 11)
sizes = []
for c in coverage:
    known = block[: int(c * len(block))] + others
    sizes.append(bk.network.compact_block_relay(block, known).compact_bytes)
print([round(s / 1000) for s in sizes], "kB")
assert sizes[-1] < full.full_bytes

# %%
# Short-ID length
# ---------------
ambiguous = {
    width: bk.network.compact_block_relay(block, block + others, short_id_size=width).missing
    for width in (1, 2, 3, 4, 6)
}
print(ambiguous)
assert ambiguous[1] > 1500 and ambiguous[6] == 0

fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
left.plot(coverage * 100, np.array(sizes) / 1000, "o-", label="compact")
left.axhline(full.full_bytes / 1000, color="black", linestyle="--", label="full block")
left.invert_xaxis()
left.set(xlabel="% of block in mempool", ylabel="kB sent", title="Compact block size")
left.legend()
right.bar([str(w) for w in ambiguous], ambiguous.values(), color="#ea580c")
right.set(xlabel="short-ID bytes", ylabel="transactions re-requested", title="Collisions")
fig.tight_layout()

# %%
# Exercise
# --------
# With 6-byte short IDs, 2000 block transactions and a 300,000-transaction
# mempool, estimate the expected number of colliding pairs. Why does BIP 152
# still choose 6 bytes rather than 8?
