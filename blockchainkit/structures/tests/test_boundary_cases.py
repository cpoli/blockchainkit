"""Boundary cases and rejection of malformed inputs in blockchainkit.structures."""

import json
from dataclasses import replace

import pytest

import blockchainkit as bk


def test_block_rejects_non_transaction_entries():
    with pytest.raises(TypeError, match="Transaction instances"):
        bk.structures.Block(transactions=(b"not a transaction",))


@pytest.mark.parametrize("chain_id", [None, "", "x" * 129])
def test_ledger_requires_bounded_chain_identifier(chain_id):
    with pytest.raises(ValueError, match="chain_id"):
        bk.structures.Ledger(chain_id=chain_id)


@pytest.mark.parametrize("account", [3, "short", "G" * 64])
@pytest.mark.parametrize("mapping", ["balances", "nonces"])
def test_ledger_rejects_malformed_account_identifiers(account, mapping):
    with pytest.raises(ValueError, match="account IDs"):
        bk.structures.Ledger(**{mapping: {account: 0}})


def test_genesis_requires_valid_work():
    genesis = bk.structures.Block(difficulty=256)
    assert not bk.consensus.valid_pow(genesis)
    with pytest.raises(ValueError, match="genesis proof of work"):
        bk.structures.Blockchain(genesis)


@pytest.mark.parametrize("proof", [None, object()])
def test_merkle_rejects_wrong_proof_type(proof):
    tree = bk.structures.MerkleTree([b"leaf"])
    assert not bk.structures.verify_proof(b"leaf", proof, tree.root)


@pytest.mark.parametrize("count", [True, 0, -1, 2**64])
def test_merkle_rejects_invalid_leaf_counts(count):
    tree = bk.structures.MerkleTree([b"leaf"])
    proof = replace(tree.proof(0), leaf_count=count)
    assert not bk.structures.verify_proof(b"leaf", proof, tree.root)


@pytest.mark.parametrize("chain_id", [None, "", "x" * 129])
def test_transaction_requires_bounded_chain_identifier(chain_id):
    with pytest.raises(ValueError, match="chain_id"):
        bk.structures.Transaction(bk.crypto.public_key(7), "0" * 64, 1, 0, chain_id=chain_id)


def test_unsigned_transaction_serialization():
    tx = bk.structures.Transaction(bk.crypto.public_key(7), "0" * 64, 1, 0)
    encoded = json.loads(tx.to_bytes())
    assert encoded == {"payload": tx.payload().decode(), "signature": None}
    assert not tx.is_valid()
    signed = tx.signed(7, signing_nonce=11)
    assert json.loads(signed.to_bytes())["signature"] is not None
    assert signed.txid != tx.txid
    assert tx.signature is None


@pytest.mark.parametrize("field", ["amount", "nonce"])
def test_transaction_integer_encoding_boundaries(field):
    tx = bk.structures.Transaction(bk.crypto.public_key(7), "0" * 64, 1, 0)
    maximum = replace(tx, **{field: 2**64 - 1})
    assert json.loads(maximum.payload())[field] == 2**64 - 1
    with pytest.raises(ValueError, match="unsigned 64-bit"):
        replace(tx, **{field: 2**64})


def _signed_transfers(count):
    sender = bk.crypto.public_key(7)
    recipient = bk.structures.address(bk.crypto.public_key(11))
    return tuple(
        bk.structures.Transaction(sender, recipient, 1, nonce).signed(7, signing_nonce=100 + nonce)
        for nonce in range(count)
    )


def test_mining_builds_the_merkle_tree_once_not_per_nonce(monkeypatch):
    # A miner varies only the header nonce; the transaction commitment is fixed.
    from blockchainkit.structures.systems import block as block_module

    built = []
    real_tree = block_module.MerkleTree

    def counting_tree(leaves):
        built.append(1)
        return real_tree(leaves)

    monkeypatch.setattr(block_module, "MerkleTree", counting_tree)
    result = bk.consensus.mine(bk.structures.Block(transactions=_signed_transfers(3), difficulty=6))
    assert result.attempts > 1
    assert bk.consensus.valid_pow(result.block)
    assert len(built) <= 2


def test_header_for_a_candidate_nonce_matches_the_mined_block():
    block = bk.structures.Block(transactions=_signed_transfers(2), difficulty=4)
    assert block.header(nonce=block.nonce) == block.header()
    assert block.header(nonce=5) == replace(block, nonce=5).header()
    for bad in (-1, 2**64, True):
        with pytest.raises((TypeError, ValueError)):
            block.header(nonce=bad)


def test_transaction_rejects_a_signature_that_is_not_a_schnorr_signature():
    with pytest.raises(TypeError, match="SchnorrSignature"):
        bk.structures.Transaction(bk.crypto.public_key(7), "0" * 64, 1, 0, signature="junk")


def test_structures_have_informative_reprs():
    tree = bk.structures.MerkleTree([b"a", b"b", b"c"])
    assert repr(tree) == f"MerkleTree(leaves=3, root={tree.root.hex()[:16]}...)"
    alice = bk.structures.address(bk.crypto.public_key(7))
    ledger = bk.structures.Ledger({alice: 100})
    assert repr(ledger) == "Ledger(chain_id='blockchainkit-demo', accounts=1, supply=100)"
    genesis = bk.consensus.mine(bk.structures.Block(difficulty=2)).block
    chain = bk.structures.Blockchain(genesis, ledger)
    assert repr(chain) == (
        f"Blockchain(height=0, blocks=1, tip={genesis.hash.hex()[:16]}..., cumulative_work=4)"
    )


def test_blockchain_keeps_an_explicit_empty_initial_state():
    genesis = bk.consensus.mine(bk.structures.Block(difficulty=2)).block
    state = bk.structures.Ledger(chain_id="other-net")
    assert bk.structures.Blockchain(genesis, state).state is state
