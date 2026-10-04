"""APIs behind the structures history: supply, Bloom filters, hash chains,
headers, Bitcoin's Merkle convention, consistency proofs, UTXOs, ids,
sparse Merkle trees, and Merkle mountain ranges."""

from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import blockchainkit as bk

s, c = bk.structures, bk.crypto
ALICE_KEY, BOB_KEY = 7, 11
ALICE = s.address(c.public_key(ALICE_KEY))
BOB = s.address(c.public_key(BOB_KEY))


# Double-entry bookkeeping -------------------------------------------------


def test_transfers_conserve_total_supply():
    ledger = s.Ledger({ALICE: 100, BOB: 5})
    tx = s.Transaction(c.public_key(ALICE_KEY), BOB, 30, 0).signed(ALICE_KEY, signing_nonce=3)
    after = ledger.apply([tx])
    assert ledger.total_supply == after.total_supply == 105
    assert s.Ledger().total_supply == 0


# Bloom filters ------------------------------------------------------------


def test_bloom_filter_has_no_false_negatives():
    bloom = s.BloomFilter(1024, 4)
    items = [f"tx {i}".encode() for i in range(100)]
    for item in items:
        bloom.add(item)
    assert all(item in bloom for item in items)
    assert len(bloom) == 100


def test_bloom_false_positive_rate_matches_the_formula():
    bloom = s.BloomFilter(2048, 3)
    for i in range(300):
        bloom.add(f"in {i}".encode())
    false_positives = sum(f"out {i}".encode() in bloom for i in range(5000)) / 5000
    expected = s.BloomFilter.false_positive_rate(2048, 3, 300)
    assert abs(false_positives - expected) < 0.02
    assert s.BloomFilter.optimal_hash_count(2048, 300) == 5


def test_bloom_filter_validation():
    with pytest.raises(ValueError):
        s.BloomFilter(0, 1)
    with pytest.raises(TypeError):
        s.BloomFilter(8, 1).add("text")
    assert "not bytes" not in s.BloomFilter(8, 1)


# Hash chains --------------------------------------------------------------


def test_hash_chain_reveals_passwords_backwards():
    chain = s.hash_chain(b"seed", 5)
    assert len(chain) == 5
    assert chain[0] == c.sha256(b"seed") and chain[1] == c.sha256(chain[0])
    anchor = chain[-1]  # The server stores only the last link.
    for password in reversed(chain[:-1]):
        assert s.verify_one_time_password(password, anchor)
        anchor = password
    assert not s.verify_one_time_password(chain[-1], chain[0])
    with pytest.raises(ValueError):
        s.hash_chain(b"seed", 0)


# Block headers and SPV ----------------------------------------------------


def _headers(count=4, difficulty=4):
    genesis = bk.consensus.mine(s.Block(difficulty=difficulty)).block
    blocks = [genesis]
    for height in range(1, count):
        block = s.Block(blocks[-1].hash, height=height, timestamp=height, difficulty=difficulty)
        blocks.append(bk.consensus.mine(block).block)
    return blocks


def test_a_header_hashes_like_its_block():
    block = _headers(2)[1]
    header = block.to_header()
    assert header.hash == block.hash and header.encode() == block.header()
    assert header.merkle_root == block.merkle_root


def test_header_chain_verification_sums_work_and_rejects_breaks():
    headers = [b.to_header() for b in _headers()]
    assert s.verify_header_chain(headers) == 4 * 2**4
    with pytest.raises(ValueError, match="link"):
        s.verify_header_chain([headers[0], headers[2]])
    with pytest.raises(ValueError, match="proof of work"):
        s.verify_header_chain([headers[0], replace(headers[1], nonce=headers[1].nonce + 1)])
    with pytest.raises(ValueError, match="empty"):
        s.verify_header_chain([])


def test_header_validation():
    with pytest.raises(ValueError):
        s.BlockHeader(previous_hash=b"short")
    with pytest.raises(ValueError):
        s.BlockHeader(merkle_root=b"short")


# Bitcoin's duplicated-leaf convention (CVE-2012-2459) ----------------------


def test_bitcoin_convention_gives_two_lists_one_root():
    leaves = [b"a", b"b", b"c"]
    assert s.bitcoin_merkle_root(leaves) == s.bitcoin_merkle_root(leaves + [b"c"])
    assert s.MerkleTree(leaves).root != s.MerkleTree(leaves + [b"c"]).root
    assert s.bitcoin_merkle_root([b"a"]) == c.hash256(b"a")
    with pytest.raises(ValueError):
        s.bitcoin_merkle_root([])


# Consistency proofs (Certificate Transparency) ----------------------------


@settings(max_examples=150, deadline=None)
@given(st.integers(1, 70), st.integers(0, 70))
def test_every_prefix_is_provably_consistent(old_size, extra):
    leaves = [str(i).encode() for i in range(old_size + extra)]
    old, new = s.MerkleTree(leaves[:old_size]), s.MerkleTree(leaves)
    proof = new.consistency_proof(old_size)
    assert s.verify_consistency(old_size, old.root, new.leaf_count, new.root, proof)


def test_a_rewritten_history_fails_the_consistency_check():
    leaves = [str(i).encode() for i in range(13)]
    new = s.MerkleTree(leaves)
    forged_old = s.MerkleTree([b"X"] + leaves[1:6])
    proof = new.consistency_proof(6)
    assert not s.verify_consistency(6, forged_old.root, 13, new.root, proof)
    assert not s.verify_consistency(6, s.MerkleTree(leaves[:6]).root, 13, new.root, proof[:-1])
    assert not s.verify_consistency(
        6, s.MerkleTree(leaves[:6]).root, 13, new.root, proof + (bytes(32),)
    )
    assert s.verify_consistency(13, new.root, 13, new.root, ())
    assert not s.verify_consistency(13, new.root, 13, new.root, (bytes(32),))
    assert not s.verify_consistency(14, new.root, 13, new.root, ())
    with pytest.raises(ValueError):
        new.consistency_proof(0)
    with pytest.raises(ValueError):
        new.consistency_proof(14)


# UTXOs --------------------------------------------------------------------


def test_utxo_spends_whole_coins_and_returns_change():
    genesis = s.UTXOSet.genesis({ALICE: 50})
    (coin,) = genesis.coins_of(ALICE)
    spend = s.UTXOTransaction((coin,), ((BOB, 30), (ALICE, 18))).signed([ALICE_KEY])
    after = genesis.apply(spend)
    assert after.balance(BOB) == 30 and after.balance(ALICE) == 18
    assert spend.fee(genesis) == 2
    assert coin not in after
    with pytest.raises(ValueError, match="unspent"):
        after.apply(spend)  # The same coin cannot be spent twice.


def test_utxo_rejects_wrong_signer_and_overspending():
    genesis = s.UTXOSet.genesis({ALICE: 50, BOB: 5})
    (alice_coin,) = genesis.coins_of(ALICE)
    with pytest.raises(ValueError, match="signature"):
        genesis.apply(s.UTXOTransaction((alice_coin,), ((BOB, 50),)).signed([BOB_KEY]))
    with pytest.raises(ValueError, match="exceed"):
        genesis.apply(s.UTXOTransaction((alice_coin,), ((BOB, 51),)).signed([ALICE_KEY]))
    with pytest.raises(ValueError, match="signature"):
        genesis.apply(s.UTXOTransaction((alice_coin,), ((BOB, 1),)))
    with pytest.raises(ValueError):
        s.UTXOTransaction((), ((BOB, 1),))
    with pytest.raises(ValueError):
        s.UTXOTransaction((alice_coin,), ((BOB, 0),))
    with pytest.raises(ValueError, match="one private key per input"):
        s.UTXOTransaction((alice_coin,), ((BOB, 1),)).signed([ALICE_KEY, BOB_KEY])


# Transaction ids ----------------------------------------------------------


def test_unsigned_id_ignores_the_signature_but_txid_does_not():
    tx = s.Transaction(c.public_key(ALICE_KEY), BOB, 5, 0)
    first = tx.signed(ALICE_KEY, signing_nonce=3)
    second = tx.signed(ALICE_KEY, signing_nonce=4)  # Same payment, different signature.
    assert first.txid != second.txid
    assert first.unsigned_id == second.unsigned_id == tx.unsigned_id


# Sparse Merkle trees ------------------------------------------------------


def test_sparse_merkle_tree_membership_and_non_membership():
    tree = s.SparseMerkleTree(depth=16).set(b"alice", b"100").set(b"bob", b"5")
    member = tree.prove(b"alice")
    assert member.value == b"100" and s.verify_sparse_proof(member, tree.root)
    absent = tree.prove(b"carol")
    assert absent.value is None and s.verify_sparse_proof(absent, tree.root)
    assert not s.verify_sparse_proof(replace(member, value=b"999"), tree.root)
    assert not s.verify_sparse_proof(replace(absent, value=b"1"), tree.root)
    assert tree.get(b"bob") == b"5" and tree.get(b"carol") is None
    assert (
        s.SparseMerkleTree(depth=16).root
        == s.SparseMerkleTree(depth=16).set(b"x", b"1").delete(b"x").root
    )


def test_sparse_merkle_root_is_independent_of_insertion_order():
    items = [(f"k{i}".encode(), f"v{i}".encode()) for i in range(20)]
    forward, backward = s.SparseMerkleTree(), s.SparseMerkleTree()
    for key, value in items:
        forward = forward.set(key, value)
    for key, value in reversed(items):
        backward = backward.set(key, value)
    assert forward.root == backward.root and len(forward) == 20
    assert len(forward.prove(b"k3").siblings) == 256


def test_sparse_merkle_validation():
    with pytest.raises(ValueError):
        s.SparseMerkleTree(depth=0)
    with pytest.raises(TypeError):
        s.SparseMerkleTree().set("key", b"v")
    proof = s.SparseMerkleTree(depth=8).prove(b"k")
    assert not s.verify_sparse_proof(
        replace(proof, siblings=proof.siblings[:-1]), s.SparseMerkleTree(depth=8).root
    )


# Merkle mountain ranges ---------------------------------------------------


@settings(max_examples=60, deadline=None)
@given(st.integers(1, 80))
def test_mountain_range_proofs_verify_for_every_leaf(size):
    mmr = s.MerkleMountainRange()
    leaves = [str(i).encode() for i in range(size)]
    for leaf in leaves:
        mmr = mmr.append(leaf)
    assert len(mmr.peaks) == bin(size).count("1")
    for index in (0, size // 2, size - 1):
        assert s.verify_mmr_proof(leaves[index], mmr.proof(index), mmr.root)
        assert not s.verify_mmr_proof(b"forged", mmr.proof(index), mmr.root)


def test_appending_only_merges_peaks():
    mmr = s.MerkleMountainRange()
    for i in range(7):
        mmr = mmr.append(str(i).encode())
    before = mmr.peaks
    grown = mmr.append(b"7")
    assert len(before) == 3 and len(grown.peaks) == 1  # 7 = 4+2+1 -> 8.
    assert len(mmr) == 7 and len(grown) == 8
    with pytest.raises(IndexError):
        mmr.proof(7)
    with pytest.raises(TypeError):
        mmr.append("text")
    assert not s.verify_mmr_proof(b"0", replace(mmr.proof(0), size=8), mmr.root)


def _genesis_coin():
    return s.UTXOSet.genesis({ALICE: 5}).coins_of(ALICE)[0]


@pytest.mark.parametrize(
    "call,error",
    [
        (lambda: s.OutPoint(b"short", 0), ValueError),
        (lambda: s.BlockHeader(difficulty=257), ValueError),
        (lambda: s.hash_chain("seed", 2), TypeError),
        (lambda: s.SparseMerkleTree(depth=257), ValueError),
        (lambda: s.UTXOTransaction((_genesis_coin(), _genesis_coin()), ((BOB, 1),)), ValueError),
        (lambda: s.UTXOTransaction((_genesis_coin(),), (("nobody", 1),)), ValueError),
        (lambda: s.UTXOTransaction((_genesis_coin(),), ((BOB, 2**64),)), ValueError),
    ],
)
def test_structure_constructors_reject_bad_arguments(call, error):
    with pytest.raises(error):
        call()


def test_malformed_consistency_and_inclusion_proofs_are_rejected():
    leaves = [bytes([i]) for i in range(5)]
    old, new = s.MerkleTree(leaves[:2]), s.MerkleTree(leaves)
    proof = new.consistency_proof(2)
    assert not s.verify_consistency(True, old.root, 5, new.root, proof)
    assert not s.verify_consistency(2, old.root, 5, new.root, ("not bytes",))
    assert not s.verify_consistency(2, old.root, 5, new.root, ())
    mmr = s.MerkleMountainRange()
    for leaf in leaves:
        mmr = mmr.append(leaf)
    good = mmr.proof(1)
    assert not s.verify_mmr_proof(b"\x01", replace(good, index=9), mmr.root)
    assert not s.verify_mmr_proof(b"\x01", replace(good, siblings=good.siblings[:-1]), mmr.root)
    sparse = s.SparseMerkleTree(depth=8).prove(b"k")
    assert not s.verify_sparse_proof(replace(sparse, siblings=("x",) * 8), bytes(32))


def test_inspection_helpers_summarize_state():
    bloom = s.BloomFilter(64, 2)
    bloom.add(b"a")
    assert 0 < bloom.fill_ratio <= 2 / 64
    mmr = s.MerkleMountainRange().append(b"a")
    assert repr(mmr) == "MerkleMountainRange(leaves=1, peaks=1)"
    utxos = s.UTXOSet.genesis({ALICE: 5, BOB: 7})
    assert len(utxos) == 2 and repr(utxos) == "UTXOSet(coins=2, total=12)"
    assert repr(_genesis_coin()).startswith("OutPoint(")
    assert repr(s.SparseMerkleTree(depth=4)).startswith("SparseMerkleTree(depth=4, keys=0")
