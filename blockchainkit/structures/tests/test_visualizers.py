"""Smoke tests for blockchainkit.structures.visualizers."""

import matplotlib.axes
import pytest

import blockchainkit as bk
from blockchainkit.structures.visualizers import plot_block_tree, plot_merkle_tree, plot_proof_trace

s = bk.structures


def test_plot_merkle_tree_colors_the_proof_path_and_siblings():
    tree = s.MerkleTree([b"a", b"b", b"c", b"d", b"e"])
    ax = plot_merkle_tree(tree, highlight=1)
    assert isinstance(ax, matplotlib.axes.Axes)
    colors = [tuple(c.get_facecolor()[0]) for c in ax.collections]
    blue = matplotlib.colors.to_rgba("#2563eb")
    orange = matplotlib.colors.to_rgba("#ea580c")
    assert colors.count(blue) == len(tree.levels)
    assert colors.count(orange) == sum(sib is not None for sib in tree.proof(1).siblings)
    assert plot_merkle_tree(tree)
    with pytest.raises(ValueError, match="empty"):
        plot_merkle_tree(s.MerkleTree([]))
    with pytest.raises(IndexError):
        plot_merkle_tree(tree, highlight=5)


@pytest.mark.parametrize("leaf,verdict", [(b"b", "matches"), (b"x", "does NOT match")])
def test_plot_proof_trace_states_the_verdict(leaf, verdict):
    tree = s.MerkleTree([b"a", b"b", b"c"])
    ax = plot_proof_trace(s.trace_proof(leaf, tree.proof(1), tree.root))
    cells = [cell.get_text().get_text() for cell in ax.tables[0].get_celld().values()]
    assert any(verdict in text for text in cells)


def test_plot_block_tree_puts_each_fork_in_its_own_lane():
    genesis = bk.consensus.mine(s.Block(difficulty=3)).block
    chain = s.Blockchain(genesis)
    a1 = bk.consensus.mine(s.Block(genesis.hash, height=1, timestamp=1, difficulty=3)).block
    b1 = bk.consensus.mine(s.Block(genesis.hash, height=1, timestamp=2, difficulty=3)).block
    a2 = bk.consensus.mine(s.Block(a1.hash, height=2, timestamp=3, difficulty=3)).block
    for block in (a1, b1, a2):
        chain.add(block)
    ax = plot_block_tree(chain)
    lanes = {round(c.get_offsets()[0][1]) for c in ax.collections}
    assert lanes == {0, -1}
    assert len(ax.collections) == 4
