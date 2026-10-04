"""Read-only views for teaching: Merkle levels, proof traces, and the block tree."""

from dataclasses import replace

import pytest

import blockchainkit as bk

s, c = bk.structures, bk.crypto


def test_merkle_levels_run_from_leaf_hashes_to_the_top_digest():
    tree = s.MerkleTree([b"a", b"b", b"c"])
    assert tree.leaf_count == 3
    assert [len(level) for level in tree.levels] == [3, 2, 1]
    assert tree.levels[0][0] == c.sha256(bk.constants.MERKLE_LEAF_PREFIX + b"a")
    assert tree.levels[1][1] == tree.levels[0][2]  # The odd leaf is promoted unchanged.


def test_proof_trace_reconstructs_the_root_step_by_step():
    tree = s.MerkleTree([b"a", b"b", b"c"])
    trace = s.trace_proof(b"b", tree.proof(1), tree.root)
    assert trace.valid
    assert [step.side for step in trace.steps] == ["left", "right"]
    assert trace.steps[0].sibling == tree.levels[0][0]
    assert trace.steps[-1].digest == tree.levels[-1][0]
    assert trace.root == tree.root

    promoted = s.trace_proof(b"c", tree.proof(2), tree.root)
    assert [step.side for step in promoted.steps] == ["promoted", "left"]
    assert promoted.steps[0].digest == tree.levels[0][2]


def test_proof_trace_of_a_wrong_leaf_is_invalid_but_complete():
    tree = s.MerkleTree([b"a", b"b", b"c"])
    trace = s.trace_proof(b"x", tree.proof(1), tree.root)
    assert not trace.valid and len(trace.steps) == 2
    assert trace.root != tree.root


def test_proof_trace_rejects_malformed_proofs():
    tree = s.MerkleTree([b"a", b"b", b"c"])
    with pytest.raises(ValueError, match="malformed"):
        s.trace_proof(b"b", replace(tree.proof(1), siblings=()), tree.root)


def _chain_with_fork():
    genesis = bk.consensus.mine(s.Block(difficulty=3)).block
    chain = s.Blockchain(genesis)
    a1 = bk.consensus.mine(s.Block(genesis.hash, height=1, timestamp=1, difficulty=3)).block
    b1 = bk.consensus.mine(s.Block(genesis.hash, height=1, timestamp=2, difficulty=3)).block
    a2 = bk.consensus.mine(s.Block(a1.hash, height=2, timestamp=3, difficulty=3)).block
    for block in (a1, b1, a2):
        chain.add(block)
    return chain, genesis, a1, b1, a2


def test_block_tree_accessors_expose_side_forks():
    chain, genesis, a1, b1, a2 = _chain_with_fork()
    assert set(chain.blocks) == {genesis.hash, a1.hash, b1.hash, a2.hash}
    assert chain.blocks[b1.hash] == b1
    assert chain.tips() == (a2, b1)  # Most work first.
    assert chain.work_at(a2.hash) == 3 * 8 and chain.work_at(b1.hash) == 2 * 8
    assert chain.state_at(a2.hash) is chain.state
    assert isinstance(chain.state_at(b1.hash), s.Ledger)
    with pytest.raises(KeyError):
        chain.work_at(bytes(32))
    with pytest.raises(TypeError):
        chain.blocks[bytes(32)] = genesis
