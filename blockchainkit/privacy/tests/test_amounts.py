"""Tests for Zerocoin, confidential transactions, RingCT, and Mimblewimble."""

import dataclasses
from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blockchainkit.crypto import TEACHING_GROUP as G
from blockchainkit.crypto import is_prime, pedersen_commit
from blockchainkit.privacy import (
    RingRangeProof,
    ZerocoinPool,
    accumulate,
    aggregate,
    commitments_balance,
    confidential_output,
    cut_through,
    hash_to_prime,
    membership_witness,
    mimblewimble_transaction,
    mint_coin,
    prove_range,
    prove_zerocoin_spend,
    ringct_spend,
    verify_confidential,
    verify_kernel,
    verify_membership,
    verify_mimblewimble,
    verify_range,
    verify_ringct,
)


def test_hash_to_prime_gives_primes_of_the_requested_size():
    for value in range(20):
        prime = hash_to_prime(value, bits=24)
        assert is_prime(prime) and prime.bit_length() == 24
    with pytest.raises(ValueError, match="at most 63"):
        hash_to_prime(1, bits=64)


def test_accumulator_witnesses():
    primes = [hash_to_prime(v) for v in range(5)]
    accumulator = accumulate(primes)
    for i, prime in enumerate(primes):
        assert verify_membership(accumulator, prime, membership_witness(primes, i))
    assert not verify_membership(accumulator, hash_to_prime(99), membership_witness(primes, 0))
    with pytest.raises(IndexError):
        membership_witness(primes, 5)


def test_zerocoin_spends_once_and_anonymously():
    pool = ZerocoinPool()
    coins = [(101, 7), (202, 8), (303, 9)]
    for serial, blinding in coins:
        pool.mint(mint_coin(serial, blinding))
    before = pool.accumulator
    spend = prove_zerocoin_spend(pool.coins, 202, 8, b"pay bob", seed=1)
    with pytest.raises(ValueError, match="invalid spend proof"):
        pool.spend(spend, b"pay eve")
    pool.spend(spend, b"pay bob")
    assert pool.spent == {202} and pool.accumulator == before
    with pytest.raises(ValueError, match="double spend"):
        pool.spend(spend, b"pay bob")
    forged = dataclasses.replace(spend, serial=404)
    with pytest.raises(ValueError, match="invalid spend proof"):
        pool.spend(forged, b"pay bob")
    with pytest.raises(ValueError, match="no minted coin"):
        prove_zerocoin_spend(pool.coins, 202, 9, b"m")
    with pytest.raises(ValueError, match="invalid spend proof"):
        ZerocoinPool().spend(spend, b"pay bob")
    with pytest.raises(ValueError, match="commitment in the group"):
        pool.mint(G.p - 1)


@settings(max_examples=15)
@given(st.integers(0, 2**16 - 1), st.integers(0, G.q - 1), st.integers(0, 2**32))
def test_range_proofs_accept_every_value_in_range(value, blinding, seed):
    proof = prove_range(value, blinding, seed=seed)
    assert proof.bits == 16 and verify_range(pedersen_commit(value, blinding), proof)


def test_range_proofs_reject_out_of_range_and_tampering():
    with pytest.raises(ValueError, match="not in"):
        prove_range(16, 5, bits=4)
    proof = prove_range(9, 5, bits=4)
    commitment = pedersen_commit(9, 5)
    assert verify_range(commitment, proof) and not verify_range(pedersen_commit(9, 6), proof)
    assert not verify_range(commitment, RingRangeProof((), ()))
    assert not verify_range(commitment, RingRangeProof(proof.bit_commitments, proof.signatures[:3]))
    swapped = RingRangeProof(proof.bit_commitments[::-1], proof.signatures)
    assert not verify_range(commitment, swapped)
    junk = RingRangeProof((1, *proof.bit_commitments[1:]), proof.signatures)
    assert not verify_range(commitment, junk)


def test_range_proof_avoids_a_zero_bit_blinding():
    # Choose the total blinding so that the last bit's blinding would be 0.
    rng = Random(0)
    blinding = sum(rng.randrange(1, G.q) for _ in range(3)) % G.q
    proof = prove_range(5, blinding, bits=4)
    assert verify_range(pedersen_commit(5, blinding), proof)


def test_confidential_transactions_balance_without_revealing_amounts():
    inputs = [pedersen_commit(50, 11)]
    outputs = [confidential_output(30, 5, seed=1), confidential_output(19, 6, seed=2)]
    assert verify_confidential(inputs, outputs, 1)
    assert not verify_confidential(inputs, outputs, 2)
    # An output of -1 (q - 1) balances a one-coin inflation, but has no range proof.
    minus_one = pedersen_commit(G.q - 1, 7)
    inflated = [pedersen_commit(51, 4), minus_one]
    assert commitments_balance(inputs, inflated, 0)
    fake = dataclasses.replace(outputs[0], commitment=minus_one)
    assert not verify_confidential(inputs, [fake, confidential_output(51, 4)], 0)


def _ring(real_amount=50, real_blinding=302):
    keys = [G.public(x) for x in range(101, 106)]
    return [
        (k, pedersen_commit(real_amount if i == 2 else 7 * i + 1, real_blinding if i == 2 else i))
        for i, k in enumerate(keys)
    ]


def test_ringct_hides_the_input_and_balances():
    ring = _ring()
    tx = ringct_spend(ring, 2, 103, 50, 302, [(30, 77), (19, 88)], 1, bits=8)
    assert verify_ringct(tx)
    assert not verify_ringct(dataclasses.replace(tx, fee=2))
    bad_range = dataclasses.replace(tx.outputs[0], commitment=tx.outputs[1].commitment)
    assert not verify_ringct(dataclasses.replace(tx, outputs=(bad_range, tx.outputs[1])))
    # A ring member committing to exactly the outputs plus fee gives an identity key.
    total = pow(G.g, tx.fee, G.p)
    for output in tx.outputs:
        total = total * output.commitment % G.p
    degenerate = dataclasses.replace(tx, ring=((tx.ring[0][0], total), *tx.ring[1:]))
    assert not verify_ringct(degenerate)
    other = ringct_spend(_ring(), 2, 103, 50, 302, [(49, 5)], 1, bits=8, seed=3)
    assert tx.signature.key_image == other.signature.key_image
    with pytest.raises(ValueError, match="must equal the outputs"):
        ringct_spend(ring, 2, 103, 50, 302, [(30, 77)], 1)
    with pytest.raises(ValueError, match="must not cancel"):
        ringct_spend(ring, 2, 103, 50, 302, [(49, 302)], 1)
    with pytest.raises(ValueError, match="not the key"):
        ringct_spend(ring, 1, 103, 50, 302, [(49, 5)], 1)


def test_mimblewimble_transactions_merge_and_cut_through():
    coinbase = mimblewimble_transaction([], [(50, 11)], minted=50, seed=1)
    pay = mimblewimble_transaction([(50, 11)], [(30, 22), (19, 33)], fee=1, seed=2)
    onward = mimblewimble_transaction([(30, 22)], [(30, 44)], seed=3)
    for tx in (coinbase, pay, onward):
        assert verify_mimblewimble(tx) and all(verify_kernel(k) for k in tx.kernels)
    block = aggregate([coinbase, pay, onward])
    assert verify_mimblewimble(block) and len(block.kernels) == 3
    compact = cut_through(block)
    assert verify_mimblewimble(compact)
    assert compact.inputs == () and len(compact.outputs) == 2
    assert not verify_mimblewimble(dataclasses.replace(pay, offset=pay.offset + 1))
    bad_kernel = dataclasses.replace(pay.kernels[0], fee=2)
    assert not verify_mimblewimble(dataclasses.replace(pay, kernels=(bad_kernel,)))
    with pytest.raises(ValueError, match="nothing to aggregate"):
        aggregate([])
    with pytest.raises(ValueError, match="must equal outputs"):
        mimblewimble_transaction([(50, 11)], [(50, 22)], fee=1)
