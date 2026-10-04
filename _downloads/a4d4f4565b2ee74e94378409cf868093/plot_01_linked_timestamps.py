"""
Linked timestamps: tamper evidence by hashing the past (Haber and Stornetta 1991)
=================================================================================

Haber and Stornetta asked how to timestamp a digital document so that not
even the timestamping service could backdate it. Their answer: each
certificate includes the hash of the previous one. Changing any old record
changes its hash, which breaks every later link. A blockchain is this
chain of linked timestamps, with blocks as the records.

What to look for
----------------

Edit one record in the middle and every link after it fails. Rewriting
history requires recomputing every later record, and anyone holding a
recent hash detects the change.

The history behind this experiment: :doc:`/history/structures_breakthroughs`.
"""

# %%
# Link ten records
# ----------------
from dataclasses import replace

import matplotlib.pyplot as plt

import blockchainkit as bk

documents = [f"lab notebook, page {page}".encode() for page in range(10)]
records = []
previous = bytes(32)
for time, document in enumerate(documents):
    header = bk.structures.BlockHeader(previous, bk.crypto.sha256(document), time, time, 0, 0)
    records.append(header)
    previous = header.hash


def broken_links(chain):
    return [i for i in range(1, len(chain)) if chain[i].previous_hash != chain[i - 1].hash]


assert broken_links(records) == []

# %%
# Backdate page 4
# ---------------
tampered = list(records)
tampered[4] = replace(records[4], merkle_root=bk.crypto.sha256(b"a better result"))
print("broken links after editing page 4:", broken_links(tampered))
assert broken_links(tampered) == [5]

# %%
# Repairing the break means rewriting everything after it
# -------------------------------------------------------
rewritten = list(tampered)
for i in range(5, len(rewritten)):
    rewritten[i] = replace(rewritten[i], previous_hash=rewritten[i - 1].hash)
assert broken_links(rewritten) == []
assert rewritten[-1].hash != records[-1].hash  # Anyone holding the latest hash notices.

# %%
fig, ax = plt.subplots(figsize=(8, 2.6))
status = ["#16a34a"] * 4 + ["#dc2626"] + ["#f59e0b"] * 5
ax.bar(range(10), [1] * 10, color=status)
ax.set(
    xticks=range(10),
    yticks=[],
    xlabel="record",
    title="Edited (red) and every record that must be rewritten (amber)",
)
fig.tight_layout()

# %%
# Exercise
# --------
# Haber and Stornetta also proposed publishing the latest hash in a newspaper.
# Why does one widely witnessed hash protect every earlier record? What plays
# the newspaper's role in Bitcoin?
