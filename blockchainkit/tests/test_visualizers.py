"""Every visualizer draws on a caller-supplied Axes instead of creating a figure."""

import matplotlib.pyplot as plt
import pytest

import blockchainkit as bk
from blockchainkit.consensus.visualizers import plot_mining_trials, plot_stake_shares
from blockchainkit.crypto.visualizers import plot_curve_points, plot_hamming_distances
from blockchainkit.network.visualizers import plot_gossip_timeline
from blockchainkit.structures.visualizers import plot_block_tree, plot_merkle_tree, plot_proof_trace
from blockchainkit.vm.visualizers import plot_execution_trace


def _inputs():
    tree = bk.structures.MerkleTree([b"a", b"b"])
    chain = bk.structures.Blockchain(bk.consensus.mine(bk.structures.Block(difficulty=1)).block)
    network = bk.network.SimulatedNetwork(["a"])
    network.broadcast("a", b"x")
    trace = bk.vm.execute([("PUSH", 1)], trace=True).trace
    return [
        (plot_curve_points, (bk.crypto.TOY_CURVE,)),
        (plot_hamming_distances, ([128, 120, 131],)),
        (plot_merkle_tree, (tree,)),
        (plot_proof_trace, (bk.structures.trace_proof(b"a", tree.proof(0), tree.root),)),
        (plot_block_tree, (chain,)),
        (plot_mining_trials, ([1, 2], [2, 4])),
        (plot_stake_shares, ({"a": 1}, ["a"])),
        (plot_gossip_timeline, (network.deliveries,)),
        (plot_execution_trace, (trace,)),
    ]


@pytest.mark.parametrize("index", range(9))
def test_visualizers_draw_on_the_given_axes(index):
    function, args = _inputs()[index]
    _, ax = plt.subplots()
    assert function(*args, ax=ax) is ax
