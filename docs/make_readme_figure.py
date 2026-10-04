"""Regenerate the README hero figure: python docs/make_readme_figure.py

Writes docs/source/_static/images/readme_hero.png, which README.md embeds by
its raw.githubusercontent.com URL so it also renders on PyPI.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.network.visualizers import plot_space_time
from blockchainkit.structures.visualizers import plot_merkle_tree

OUT = Path(__file__).parent / "source" / "_static" / "images" / "readme_hero.png"

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)

tree = bk.structures.MerkleTree([f"tx {i}".encode() for i in range(8)])
plot_merkle_tree(tree, highlight=5, ax=ax1)
ax1.set_title("Merkle (1979): proving one payment in a block")

for q in (0.1, 0.2, 0.3, 0.4):
    z = range(0, 31)
    ax2.semilogy(
        z,
        [max(bk.consensus.attacker_success_probability(q, k), 1e-12) for k in z],
        label=f"attacker share {q}",
    )
ax2.set(xlabel="confirmations", ylabel="chance the attacker catches up", ylim=(1e-10, 1.5))
ax2.set_title("Nakamoto (2008): how many confirmations?")
ax2.legend()

history = [
    [("send", "m1"), ("local", "a"), ("receive", "m3")],
    [("receive", "m1"), ("send", "m2")],
    [("local", "b"), ("receive", "m2"), ("send", "m3")],
]
plot_space_time(history, ax=ax3)
ax3.set_title("Lamport (1978): ordering events without a clock")

fig.savefig(OUT, dpi=110)
print(f"wrote {OUT}")
