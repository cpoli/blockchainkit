"""Commitment integrity, replay rejection, atomic state, and fork reorganizations."""

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk

s, c = bk.structures, bk.crypto


@given(st.lists(st.binary(max_size=30), min_size=1, max_size=30))
def test_every_merkle_leaf_verifies(leaves):
    tree = s.MerkleTree(leaves)
    for index, leaf in enumerate(leaves):
        proof = tree.proof(index)
        assert s.verify_proof(leaf, proof, tree.root)
        assert not s.verify_proof(leaf + b"x", proof, tree.root)
        assert not s.verify_proof(leaf, replace(proof, leaf_count=len(leaves) + 1), tree.root)


def test_merkle_shape_and_empty_tree():
    assert s.MerkleTree([]).root == c.sha256(b"\x02" + bytes(8))
    assert s.MerkleTree([b"a", b"b", b"c"]).root != s.MerkleTree([b"a", b"b", b"c", b"c"]).root
    tree = s.MerkleTree([b"a", b"b", b"c"])
    proof = tree.proof(2)
    assert proof.siblings[0] is None
    assert not s.verify_proof(b"c", replace(proof, siblings=()), tree.root)
    assert not s.verify_proof(b"c", replace(proof, siblings=proof.siblings + (None,)), tree.root)
    assert not s.verify_proof(b"c", replace(proof, index=-1), tree.root)
    assert not s.verify_proof(b"c", replace(proof, siblings=(bytes(32),) * 2), tree.root)
    assert not s.verify_proof(b"a", replace(tree.proof(0), siblings=(None, None)), tree.root)
    assert not s.verify_proof(b"a", tree.proof(0), b"bad")
    assert not s.verify_proof(b"a", s.MerkleProof(0, 1, None), tree.root)
    with pytest.raises(IndexError):
        s.MerkleTree([]).proof(0)
    with pytest.raises(TypeError):
        s.MerkleTree(["text"])


def transfer(amount=10, nonce=0, chain_id="blockchainkit-demo"):
    return s.Transaction(
        c.public_key(7), s.address(c.public_key(11)), amount, nonce, chain_id
    ).signed(7, signing_nonce=13 + nonce)


def test_transaction_and_ledger_rules():
    tx = transfer()
    alice, bob = tx.sender_address, tx.recipient
    ledger = s.Ledger({alice: 100})
    state = ledger.apply([tx])
    assert state.balances == {alice: 90, bob: 10}
    assert ledger.balances == {alice: 100}
    assert state.nonces[alice] == 1
    assert tx.is_valid()
    assert not replace(tx, amount=11).is_valid()
    assert tx.txid != replace(tx, amount=11).txid
    assert not replace(tx, signature=None).is_valid()
    for invalid in (tx, transfer(1000, 1), transfer(1, 1, "another-chain"), transfer(1, 3)):
        with pytest.raises(ValueError):
            state.apply([invalid])
    with pytest.raises(ValueError):
        ledger.apply([tx, transfer(1000, 1)])
    assert ledger.balances[alice] == 100
    with pytest.raises(TypeError):
        ledger.balances[alice] = 0
    with pytest.raises(ValueError):
        tx.signed(8)
    self_tx = s.Transaction(c.public_key(7), alice, 10, 0).signed(7, signing_nonce=21)
    self_state = ledger.apply([self_tx])
    assert self_state.balances[alice] == 100 and self_state.nonces[alice] == 1


@pytest.mark.parametrize(
    "change", [{"amount": 0}, {"amount": True}, {"nonce": -1}, {"recipient": "x"}, {"chain_id": ""}]
)
def test_invalid_transaction_fields(change):
    with pytest.raises(ValueError):
        replace(transfer(), **change)


def test_block_header_commits_to_all_fields():
    block = s.Block(transactions=(transfer(),), difficulty=0)
    for change in (
        {"nonce": 1},
        {"height": 1},
        {"timestamp": 1},
        {"difficulty": 1},
        {"previous_hash": b"x" * 32},
        {"transactions": ()},
    ):
        assert replace(block, **change).hash != block.hash
    for change in (
        {"nonce": -1},
        {"timestamp": True},
        {"difficulty": 257},
        {"previous_hash": b"x"},
        {"height": 2**64},
    ):
        with pytest.raises(ValueError):
            replace(block, **change)


def test_fork_reorganization_restores_balances_and_nonces():
    genesis = s.Block(difficulty=0)
    tx = transfer()
    state = s.Ledger({tx.sender_address: 100})
    first = s.Block(genesis.hash, (tx,), 1, 1, 0)
    alternate = s.Block(genesis.hash, (), 1, 2, 0)
    second = s.Block(alternate.hash, (), 2, 3, 0)
    chain = s.Blockchain(genesis, state)
    chain.add(first)
    assert chain.state.balances[tx.sender_address] == 90
    chain.add(alternate)
    assert chain.add(second)
    assert chain.tip == second
    assert chain.state.balances[tx.sender_address] == 100
    assert chain.state.nonces.get(tx.sender_address, 0) == 0
    assert chain.canonical_blocks() == (genesis, alternate, second)
    assert chain.cumulative_work == 3
    assert not chain.add(second)
    assert chain.contains(first.hash)
    # Peers seeing the same fork set in opposite order converge.
    other = s.Blockchain(genesis, state)
    other.add(alternate)
    other.add(first)
    other.add(second)
    assert other.tip == chain.tip


def test_chain_rejects_invalid_children_without_mutation():
    genesis = s.Block(difficulty=0)
    chain = s.Blockchain(genesis)
    block = s.Block(genesis.hash, (), 1, 1, 0)
    for invalid in (
        replace(block, previous_hash=b"x" * 32),
        replace(block, height=2),
        replace(block, difficulty=1),
        replace(block, transactions=(transfer(),)),
    ):
        with pytest.raises(ValueError):
            chain.add(invalid)
        assert chain.tip == genesis
        assert not chain.contains(invalid.hash)
    chain.add(block)
    with pytest.raises(ValueError):
        chain.add(s.Block(block.hash, (), 2, 0, 0))
    with pytest.raises(ValueError):
        s.Blockchain(block)
