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
