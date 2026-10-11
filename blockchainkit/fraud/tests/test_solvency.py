"""Merkle sum trees, proofs of reserves and solvency, and custodians."""

from dataclasses import replace
from random import Random

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk
from blockchainkit.contracts import ContractError, World
from blockchainkit.fraud import (
    TRACKING,
    BitRangeProof,
    Custodian,
    MerkleSumTree,
    SolvencyProver,
    SumProofStep,
    audit,
    detection_probability,
    liability_tree,
    prove_either,
    prove_range,
    reissue_missing,
    reserve_ratio,
    sum_leaf,
    verify_either,
    verify_liability,
    verify_range,
    verify_solvency,
    verify_sum_proof,
)

balances = st.lists(st.integers(0, 10**6), min_size=1, max_size=20)

# Merkle sum trees -------------------------------------------------------------


@given(balances)
def test_every_customer_verifies_and_the_root_carries_the_total(amounts):
    entries = [(f"c{i}", amount) for i, amount in enumerate(amounts)]
    tree = MerkleSumTree(entries, salt=b"s")
    assert tree.total == sum(amounts) and len(tree) == len(amounts)
    for i, (label, amount) in enumerate(entries):
        proof = tree.proof(i)
        assert verify_sum_proof(label, amount, proof, tree.root, tree.total, salt=b"s")
        assert not verify_sum_proof(label, amount + 1, proof, tree.root, tree.total, salt=b"s")
        assert not verify_sum_proof(label, amount, proof, tree.root, tree.total + 1, salt=b"s")
        assert not verify_sum_proof(label, amount, proof, tree.root, tree.total)


def test_sum_tree_shape_and_accessors():
    tree = MerkleSumTree([("a", 1), ("b", 2), ("c", 3)])
    assert [len(level) for level in tree.levels] == [3, 2, 1]
    assert tree.index("c") == 2 and tree.index("zed") is None and tree.salt == b""
    assert len(tree.proof(2).steps) == 1  # The odd leaf is promoted.
    assert repr(tree) == "MerkleSumTree(leaves=3, total=6)"
    single = MerkleSumTree([("a", 5)])
    assert single.proof(0).steps == () and single.root == sum_leaf("a", 5)[0]
    with pytest.raises(ValueError):
        MerkleSumTree([])
    with pytest.raises(IndexError):
        tree.proof(3)
    with pytest.raises(TypeError):
        sum_leaf(1, 1)
    with pytest.raises(TypeError):
        sum_leaf("a", 1, salt="s")


def test_a_negative_balance_hides_liabilities_but_is_caught():
    tree = MerkleSumTree([("alice", 50), ("fake", -40), ("bob", 30), ("carol", 20)])
    assert tree.total == 60  # 100 owed, 60 declared.
    alice = tree.proof(0)
    assert alice.steps[0] == SumProofStep("right", sum_leaf("fake", -40)[0], -40)
    assert not verify_sum_proof("alice", 50, alice, tree.root, tree.total)
    assert verify_sum_proof("bob", 30, tree.proof(2), tree.root, tree.total)
    assert not verify_sum_proof("fake", -40, tree.proof(1), tree.root, tree.total)


# Proofs of reserves and liabilities --------------------------------------------


def test_audit_catches_omitted_customers():
    owed = {f"c{i:02}": 10 + i for i in range(40)}
    honest = liability_tree(owed)
    assert audit(honest, owed, checking=1.0).complaints == ()
    cheat = liability_tree({c: v for c, v in owed.items() if c not in {"c03", "c07"}})
    result = audit(cheat, owed, checking=1.0)
    assert result.caught and result.complaints == ("c03", "c07") and len(result.checked) == 40
    lowered = liability_tree({**owed, "c05": 1})
    assert audit(lowered, owed, checking=1.0).complaints == ("c05",)
    assert audit(cheat, owed, checking=0.0) == audit(cheat, {}, checking=0.5)


def test_detection_rate_matches_the_formula():
    owed = {f"c{i}": 5 for i in range(20)}
    cheat = liability_tree({c: v for c, v in owed.items() if c not in {"c1", "c2", "c3"}})
    caught = sum(audit(cheat, owed, checking=0.2, seed=s).caught for s in range(400))
    assert caught / 400 == pytest.approx(detection_probability(3, 0.2), abs=0.06)
    assert detection_probability(0, 0.5) == 0.0 and detection_probability(5, 1.0) == 1.0


def test_reserve_ratio():
    assert reserve_ratio(0, 10) == 0.0
    with pytest.raises(ValueError):
        reserve_ratio(5, 0)


# Provisions -------------------------------------------------------------------


def test_or_proofs_hold_only_for_zero_or_the_value():
    rng = Random(0)
    for opened in (0, 42):
        commitment = bk.crypto.pedersen_commit(opened, 99)
        proof = prove_either(commitment, 42, opened, 99, rng, bk.crypto.TEACHING_GROUP)
        assert verify_either(commitment, 42, proof, bk.crypto.TEACHING_GROUP)
        assert not verify_either(commitment, 41 if opened else 0, proof, bk.crypto.TEACHING_GROUP)
    liar = bk.crypto.pedersen_commit(7, 5)
    forged = prove_either(liar, 42, 7, 5, rng, bk.crypto.TEACHING_GROUP)
    assert not verify_either(liar, 42, forged, bk.crypto.TEACHING_GROUP)


@given(st.integers(0, 2**8 - 1), st.integers(0, 2**60))
def test_range_proofs(value, blinding):
    proof = prove_range(value, blinding, 8, Random(value))
    assert proof.bits == 8
    assert verify_range(bk.crypto.pedersen_commit(value, blinding), proof)
    assert not verify_range(bk.crypto.pedersen_commit(value, blinding + 1), proof)


def test_range_proof_rejects_out_of_range_and_tampering():
    with pytest.raises(ValueError, match="not in"):
        prove_range(256, 1, 8, Random(0))
    with pytest.raises(ValueError, match="not in"):
        prove_range(-1, 1, 8, Random(0))
    proof = prove_range(5, 3, 4, Random(0))
    commitment = bk.crypto.pedersen_commit(5, 3)
    assert not verify_range(commitment, BitRangeProof(proof.bit_commitments, proof.bit_proofs[:3]))
    swapped = (proof.bit_proofs[1], *proof.bit_proofs[1:])
    assert not verify_range(commitment, BitRangeProof(proof.bit_commitments, swapped))


def test_a_solvent_exchange_proves_it_and_customers_check_their_balance():
    assets, owed = [50, 70, 20, 90], [30, 25, 60, 10]
    prover = SolvencyProver(assets, {0, 2, 3}, owed, seed=3)
    assert prover.assets == 160 and prover.surplus == 35
    proof = prover.prove()
    assert verify_solvency(assets, proof)
    for customer, balance in enumerate(owed):
        commitment = proof.liability_commitments[customer]
        assert verify_liability(commitment, balance, prover.blinding(customer))
        assert not verify_liability(commitment, balance + 1, prover.blinding(customer))
    assert not verify_solvency([50, 70, 20, 91], proof)
    assert not verify_solvency(assets[:3], proof)
    assert not verify_solvency(assets, replace(proof, asset_proofs=proof.asset_proofs[:3]))
    assert not verify_solvency(assets, replace(proof, liability_proofs=proof.liability_proofs[:1]))
    dropped = replace(
        proof,
        liability_commitments=proof.liability_commitments[1:],
        liability_proofs=proof.liability_proofs[1:],
    )
    assert not verify_solvency(assets, dropped)  # Hiding a debt breaks the surplus proof.
    negative = replace(proof, liability_proofs=(proof.surplus_proof, *proof.liability_proofs[1:]))
    assert not verify_solvency(assets, negative)


def test_an_insolvent_exchange_cannot_prove_solvency():
    with pytest.raises(ValueError, match="insolvent"):
        SolvencyProver([50, 70], {0}, [30, 25]).prove()
    with pytest.raises(ValueError, match="not in"):
        SolvencyProver([50], {0}, [2**20]).prove()
    with pytest.raises(ValueError, match="owned"):
        SolvencyProver([50], {1}, [1])
    with pytest.raises(ValueError, match="owned"):
        SolvencyProver([50], {True}, [1])
    with pytest.raises(ValueError):
        SolvencyProver([50], {0}, [-1])


# Custodians -------------------------------------------------------------------


def _withdrawals(n=10):
    exchange = 7
    sender = bk.crypto.public_key(exchange)
    return exchange, [
        bk.structures.Transaction(
            sender, bk.structures.address(bk.crypto.public_key(100 + i)), 10, i
        ).signed(exchange, signing_nonce=1_000 + i)
        for i in range(n)
    ]


def test_tracking_by_txid_pays_malleated_withdrawals_twice():
    key, sent = _withdrawals()
    malleated = [
        tx.signed(key, signing_nonce=9_000 + tx.nonce) if tx.nonce < 3 else tx for tx in sent
    ]
    assert [tx.nonce for tx in reissue_missing(sent, malleated)] == [0, 1, 2]
    assert reissue_missing(sent, malleated, by="unsigned_id") == ()
    assert set(TRACKING) == {"txid", "unsigned_id"}
    with pytest.raises(ValueError, match="by must"):
        reissue_missing(sent, malleated, by="amount")


def _custodian(credit_line=400):
    world = World()
    for k in range(5):
        world.fund(f"c{k}", 100)
    exchange = world.deploy("operator", Custodian, "affiliate", credit_line)
    for k in range(5):
        world.transact(f"c{k}", exchange, "deposit", value=100)
    return world, exchange


def test_custodian_pays_while_reserves_last():
    world, exchange = _custodian()
    assert world.view(exchange, "reserves") == world.view(exchange, "liabilities") == 500
    assert world.transact("operator", exchange, "lend_to_affiliate", 300).success
    assert world.view(exchange, "reserves") == 200 and world.balance("affiliate") == 300
    assert world.view(exchange, "balances") == {f"c{k}": 100 for k in range(5)}
    errors = [world.transact(f"c{k}", exchange, "withdraw", 100).error for k in range(5)]
    assert errors == [None, None, "withdrawals paused", "withdrawals paused", "withdrawals paused"]
    assert world.view(exchange, "balance_of", "c4") == 100
    assert world.view(exchange, "liabilities") == 300
    world.fund("affiliate", 0)
    assert world.transact("affiliate", exchange, "repay", value=300).success
    assert world.view(exchange, "reserves") == 300
    assert world.transact("c4", exchange, "withdraw", 100).success


def test_custodian_rules():
    world, exchange = _custodian(credit_line=100)
    assert world.transact("c0", exchange, "lend_to_affiliate", 50).error == "only the operator"
    assert world.transact("operator", exchange, "lend_to_affiliate", 200).error == (
        "credit line exceeded"
    )
    assert not world.transact("operator", exchange, "lend_to_affiliate", 0).success
    assert world.transact("c0", exchange, "withdraw", 101).error == "insufficient balance"
    assert not world.transact("c0", exchange, "deposit").success
    world.fund("x", 10)
    world.transact("x", exchange, "repay", value=10)
    assert world.read(exchange, "lent") == 0
    with pytest.raises(ContractError):
        world.deploy("operator", Custodian, "a", -1)
