"""
Casper FFG: finality by two-thirds votes and slashing (Buterin and Griffith 2017)
=================================================================================

Casper the Friendly Finality Gadget overlays finality on a block chain.
Validators vote for links between checkpoints; a checkpoint is justified
when two thirds of the stake link to it from a justified checkpoint, and
finalized when its direct child is justified. Two slashing rules (no two
votes for one height; no vote surrounding another) guarantee that two
conflicting finalized checkpoints cost at least a third of all stake.
Ethereum's proof of stake uses it.

What to look for
----------------

Checkpoints are finalized one behind the justified frontier. A validator
who equivocates or casts a surrounding vote is caught by comparing votes,
with no need to know which fork is correct.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
See :doc:`/exercises/consensus` for a worked solution to the exercise.
"""

# %%
# Justify and finalize
# --------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

stakes = {"v1": 25, "v2": 25, "v3": 25, "v4": 25}
ffg = bk.consensus.FinalityGadget(stakes)
history = []
for height in range(1, 7):
    voters = ["v1", "v2", "v3"] if height != 4 else ["v1", "v2"]  # Height 4 misses quorum.
    for v in voters:
        ffg.vote(v, source=max(ffg.justified), target=height)
    history.append((height, max(ffg.justified), max(ffg.finalized)))
print("justified:", sorted(ffg.justified), "finalized:", sorted(ffg.finalized))
assert 4 not in ffg.justified and 3 not in ffg.finalized

# %%
# Slashable behaviour
# -------------------
ffg.vote("v4", source=0, target=7, checkpoint=b"fork A")
ffg.vote("v4", source=0, target=7, checkpoint=b"fork B")  # Two votes for height 7.
ffg.vote("v1", source=1, target=8)  # Surrounds v1's earlier vote (5 -> 6).
offenses = {(o.validator, o.kind) for o in ffg.slashable}
print(offenses)
assert offenses == {("v4", "double vote"), ("v1", "surround vote")}

# %%
fig, ax = plt.subplots(figsize=(7, 3.5))
heights, justified, finalized = zip(*history, strict=True)
ax.step(heights, justified, where="post", label="latest justified")
ax.step(heights, finalized, where="post", label="latest finalized")
ax.set(
    xlabel="checkpoint voted for",
    ylabel="checkpoint height",
    title="Finality trails justification by one checkpoint",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Two conflicting checkpoints are each finalized by two thirds of the stake.
# Show that at least a third of the stake must have voted for both, and so
# broke a slashing rule.
