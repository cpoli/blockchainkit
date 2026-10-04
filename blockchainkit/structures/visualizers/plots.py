"""Plotting helpers for blockchainkit.structures: Merkle trees, proof traces, block trees."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from blockchainkit.structures.core.base import MerkleTrace
from blockchainkit.structures.systems.chain import Blockchain
from blockchainkit.structures.systems.merkle import MerkleTree

__all__ = ["plot_merkle_tree", "plot_proof_trace", "plot_block_tree"]

_PATH, _SIBLING, _OTHER = "#2563eb", "#ea580c", "#cbd5e1"


def plot_merkle_tree(
    tree: MerkleTree, *, highlight: int | None = None, ax: Axes | None = None
) -> Axes:
    """Draw every level of a Merkle tree, optionally highlighting one proof.

    Parameters
    ----------
    tree : MerkleTree
        A tree with at least one leaf.
    highlight : int, optional
        Leaf index whose authentication path (blue) and proof siblings
        (orange) are colored: the siblings are exactly what a proof sends.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if tree.leaf_count == 0:
        raise ValueError("cannot draw an empty tree")
    if ax is None:
        _, ax = plt.subplots(figsize=(max(6, 1.4 * tree.leaf_count), 1.3 * len(tree.levels) + 1))
    width = len(tree.levels[0])
    positions: list[list[float]] = [[i + 0.5 for i in range(width)]]
    for level in tree.levels[1:]:
        below = positions[-1]
        positions.append(
            [(below[2 * i] + below[min(2 * i + 1, len(below) - 1)]) / 2 for i in range(len(level))]
        )
    path = {}
    if highlight is not None:
        tree.proof(highlight)  # Validates the index.
        position = highlight
        for depth in range(len(tree.levels)):
            path[(depth, position)] = _PATH
            if (position ^ 1) < len(tree.levels[depth]):
                path[(depth, position ^ 1)] = _SIBLING
            position //= 2
    for depth, level in enumerate(tree.levels):
        for i, digest in enumerate(level):
            x, y = positions[depth][i], depth
            if depth + 1 < len(tree.levels):
                ax.plot([x, positions[depth + 1][i // 2]], [y, y + 1], color="#94a3b8", zorder=1)
            color = path.get((depth, i), _OTHER)
            ink = "black" if color == _OTHER else "white"
            ax.scatter([x], [y], s=900, color=color, zorder=2)
            ax.text(
                x, y, digest.hex()[:6], ha="center", va="center", fontsize=7, color=ink, zorder=3
            )
    top_x = positions[-1][0]
    note = f"root = H(0x02 || count={tree.leaf_count} || top digest)"
    ax.text(top_x, len(tree.levels) - 0.55, note, ha="center", fontsize=9)
    ax.set_ylim(-0.7, len(tree.levels) - 0.2)
    ax.set_xlim(0, width)
    ax.axis("off")
    title = "Merkle tree (digest prefixes)"
    if highlight is not None:
        title += f": proof for leaf {highlight} sends the orange siblings"
    ax.set_title(title)
    return ax


def plot_proof_trace(trace: MerkleTrace, ax: Axes | None = None) -> Axes:
    """Tabulate each step of reconstructing a root from a leaf and its proof.

    Parameters
    ----------
    trace : MerkleTrace
        From :func:`~blockchainkit.structures.systems.merkle.trace_proof`.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 0.5 * len(trace.steps) + 1.6))
    describe = {
        "left": "hash(sibling || node)",
        "right": "hash(node || sibling)",
        "promoted": "no sibling: promote",
    }
    rows = [["hash(0x00 || leaf)", "", trace.leaf_digest.hex()[:16]]]
    for step in trace.steps:
        sibling = "" if step.sibling is None else step.sibling.hex()[:16]
        rows.append([describe[step.side], sibling, step.digest.hex()[:16]])
    verdict = "matches trusted root" if trace.valid else "does NOT match trusted root"
    rows.append([f"bind leaf count; {verdict}", "", trace.root.hex()[:16]])
    ax.axis("off")
    table = ax.table(
        cellText=rows, colLabels=["step", "sibling", "result"], cellLoc="center", loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)
    ax.set_title("A Merkle proof is a recipe for reconstructing the root")
    return ax


def plot_block_tree(chain: Blockchain, ax: Axes | None = None) -> Axes:
    """Draw every stored block by height, one lane per fork, canonical chain highlighted.

    Parameters
    ----------
    chain : Blockchain
        A chain, possibly holding side forks.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3))
    canonical = {block.hash for block in chain.canonical_blocks()}
    lane: dict[bytes, int] = {}
    for index, tip in enumerate(chain.tips()):
        block = tip
        while block.hash not in lane:
            lane[block.hash] = index
            if block.height == 0:
                break
            block = chain.blocks[block.previous_hash]
    for digest, block in chain.blocks.items():
        x, y = block.height, -lane[digest]
        if block.height:
            parent = chain.blocks[block.previous_hash]
            ax.plot([parent.height, x], [-lane[parent.hash], y], color="#94a3b8", zorder=1)
        color = _PATH if digest in canonical else _OTHER
        ax.scatter([x], [y], s=700, marker="s", color=color, zorder=2)
        ax.text(x, y, digest.hex()[:4], ha="center", va="center", fontsize=7, zorder=3)
    ax.set_xlabel("height")
    ax.set_yticks([])
    ax.set_title(f"Block tree: canonical chain in blue (work {chain.cumulative_work})")
    return ax
