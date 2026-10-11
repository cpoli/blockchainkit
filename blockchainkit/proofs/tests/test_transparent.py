"""Bulletproofs, FRI, STARKs and Halo: proofs without a trusted setup."""

from dataclasses import replace

import pytest

from blockchainkit.crypto import TEACHING_GROUP
from blockchainkit.proofs import (
    AccumulationProof,
    HaloAccumulator,
    StarkProof,
    accumulate,
    challenge_polynomial,
    decide,
    evaluate_on_domain,
    fibonacci_trace,
    fri_prove,
    fri_verify,
    ipa_commit,
    ipa_defer,
    ipa_generators,
    ipa_open,
    ipa_verify,
    range_commitment,
    range_proof,
    stark_prove,
    stark_verify,
    verify_accumulation,
    verify_range_proof,
)
from blockchainkit.structures import MerkleProof


@pytest.mark.parametrize("bits", [1, 8, 64])
def test_range_proofs_accept_the_extremes(bits):
    for value in (0, 2**bits - 1):
        proof = range_proof(value, blinding=77, bits=bits, seed=value)
        assert verify_range_proof(proof, bits)
        assert proof.commitment == range_commitment(value, 77)
    assert proof.size == (4 + 2 * (bits.bit_length() - 1), 5)


def test_range_proofs_reject_out_of_range_and_tampering():
    with pytest.raises(ValueError, match="below"):
        range_proof(2**16, 1, 16)
    proof = range_proof(1000, 77, 16)
    assert not verify_range_proof(replace(proof, commitment=range_commitment(70000, 77)), 16)
    assert not verify_range_proof(replace(proof, final_a=proof.final_a + 1), 16)
    assert not verify_range_proof(replace(proof, t_hat=proof.t_hat + 1), 16)
    assert not verify_range_proof(proof, 32)
    assert not verify_range_proof(replace(proof, left=proof.left[:-1]), 16)
    assert not verify_range_proof(replace(proof, mu=TEACHING_GROUP.q), 16)
    assert not verify_range_proof(
        replace(proof, a=TEACHING_GROUP.p - 1), 16
    )  # Not in the subgroup.
    assert not verify_range_proof("proof", 16)
    swapped = replace(proof, left=proof.right, right=proof.left)
    assert not verify_range_proof(swapped, 16)
    with pytest.raises(ValueError, match="power of two"):
        range_proof(1, 1, 12)


def test_fri_accepts_low_degree_and_rejects_high_degree():
    values = evaluate_on_domain(range(1, 65), 512, offset=31)
    proof = fri_prove(values, 64, num_queries=12)
    assert fri_verify(proof, domain_size=512, degree_bound=64, num_queries=12)
    assert len(proof.roots) == 6 and proof.size > 0
    high = fri_prove(evaluate_on_domain(range(1, 66), 512, offset=31), 64, num_queries=12)
    assert not fri_verify(high, domain_size=512, degree_bound=64, num_queries=12)
    assert not fri_verify(proof, domain_size=512, degree_bound=32, num_queries=12)
    assert not fri_verify(proof, domain_size=512, degree_bound=64, num_queries=11)
    assert not fri_verify(
        replace(proof, final=1.0), domain_size=512, degree_bound=64, num_queries=12
    )
    assert not fri_verify("proof", domain_size=512, degree_bound=64)


def test_fri_rejects_each_kind_of_tampered_query():
    proof = fri_prove(evaluate_on_domain(range(1, 9), 32, offset=31), 8, num_queries=2)
    verify = lambda p: fri_verify(p, domain_size=32, degree_bound=8, num_queries=2)  # noqa: E731
    query = proof.queries[0]
    layer = query.layers[1]

    def with_layer(new_layer, k=1):
        layers = query.layers[:k] + (new_layer,) + query.layers[k + 1 :]
        return replace(proof, queries=(replace(query, layers=layers),) + proof.queries[1:])

    assert verify(proof)
    assert not verify(
        replace(proof, queries=(replace(query, index=query.index ^ 1),) + proof.queries[1:])
    )
    assert not verify(
        replace(proof, queries=(replace(query, layers=query.layers[:-1]),) + proof.queries[1:])
    )
    assert not verify(with_layer(replace(layer, low=layer.low + 1)))
    assert not verify(with_layer(replace(layer, high=-1)))
    assert not verify(with_layer(replace(layer, low_path=layer.high_path)))
    bogus = MerkleProof(
        layer.low_path.index, layer.low_path.leaf_count, layer.low_path.siblings[::-1]
    )
    assert not verify(with_layer(replace(layer, low_path=bogus)))
    assert not verify(replace(proof, final=proof.final + 1))
    # A consistent but wrong layer: the root of another polynomial's layer.
    other = fri_prove(evaluate_on_domain(range(2, 10), 32, offset=31), 8, num_queries=2)
    assert not verify(replace(proof, roots=other.roots))


def test_fri_catches_a_prover_whose_layers_do_not_fold(monkeypatch):
    from blockchainkit.proofs.systems import fri

    honest_fold = fri._fold
    values = evaluate_on_domain(range(1, 9), 32, offset=31)
    monkeypatch.setattr(fri, "_fold", lambda *args: (honest_fold(*args) + 1) % fri._P)
    cheating = fri_prove(values, 8, num_queries=2)  # Each layer is the fold plus one.
    monkeypatch.setattr(fri, "_fold", honest_fold)
    assert not fri_verify(cheating, domain_size=32, degree_bound=8, num_queries=2)


def test_fri_parameter_validation():
    with pytest.raises(ValueError, match="power of two"):
        fri_prove([1] * 24, 4)
    with pytest.raises(ValueError, match="twice"):
        fri_prove([1] * 8, 8)
    with pytest.raises(ValueError):
        fri_prove([1] * 8, 1)


def test_stark_proves_fibonacci_and_rejects_false_claims():
    trace = fibonacci_trace(16)
    assert trace[:6] == (1, 1, 2, 3, 5, 8)
    proof = stark_prove(16, num_queries=6)
    assert stark_verify(proof, steps=16, result=trace[-1], num_queries=6)
    assert not stark_verify(proof, steps=16, result=trace[-1] + 1, num_queries=6)
    assert not stark_verify(proof, steps=16, result=trace[-1], num_queries=5)
    false = stark_prove(16, claimed=12345, num_queries=6)
    assert not stark_verify(false, steps=16, result=12345, num_queries=6)
    assert proof.size > proof.fri.size
    assert not stark_verify("proof", steps=16, result=1)


def test_stark_rejects_tampered_trace_openings():
    trace = fibonacci_trace(16)
    proof = stark_prove(16, num_queries=4)
    verify = lambda p: stark_verify(p, steps=16, result=trace[-1], num_queries=4)  # noqa: E731
    opening = proof.trace_openings[1]
    for bad in (
        replace(opening, values=opening.values[:2]),
        replace(opening, values=(opening.values[0] + 1,) + opening.values[1:]),
        replace(opening, values=(-1,) + opening.values[1:]),
        replace(opening, paths=opening.paths[::-1]),
        replace(opening, paths=(proof.trace_openings[0].paths[0],) + opening.paths[1:]),
    ):
        openings = proof.trace_openings[:1] + (bad,) + proof.trace_openings[2:]
        assert not verify(replace(proof, trace_openings=openings))
    other = stark_prove(16, num_queries=4)
    assert verify(other)
    assert not verify(StarkProof(proof.trace_root, proof.fri, proof.trace_openings[:-1]))
    root = stark_prove(32, num_queries=4).trace_root
    assert not verify(replace(proof, trace_root=root))
    with pytest.raises(ValueError, match="power of two"):
        stark_prove(12)


def test_stark_catches_a_composition_unrelated_to_the_trace(monkeypatch):
    from blockchainkit.proofs.systems import stark

    honest = stark._composition
    monkeypatch.setattr(stark, "_composition", lambda *args: (honest(*args) + 1) % stark._P)
    shifted = stark_prove(16, num_queries=4)  # FRI still passes: a constant shift is low degree.
    monkeypatch.setattr(stark, "_composition", honest)
    assert not stark_verify(shifted, steps=16, result=fibonacci_trace(16)[-1], num_queries=4)


def test_stark_proofs_are_deterministic():
    proof = stark_prove(32, num_queries=8)
    assert stark_prove(32, claimed=fibonacci_trace(32)[-1], num_queries=8) == proof


def test_ipa_commitments_open_and_verify():
    gens = ipa_generators(8)
    f = [3, 1, 4, 1, 5]
    commitment = ipa_commit(f, gens)
    opening = ipa_open(f, 2, gens)
    assert opening.value == 109 and ipa_verify(commitment, opening, gens)
    assert not ipa_verify(commitment, replace(opening, value=110), gens)
    assert not ipa_verify(commitment, replace(opening, final=opening.final + 1), gens)
    assert not ipa_verify(commitment, replace(opening, left=opening.left[:-1]), gens)
    assert not ipa_verify(commitment, replace(opening, right=opening.right[:-1]), gens)
    assert not ipa_verify(commitment, "opening", gens)
    with pytest.raises(ValueError):
        ipa_commit(range(9), gens)
    with pytest.raises(ValueError):
        ipa_generators(6)


def test_halo_defers_the_expensive_check_and_accumulates():
    gens = ipa_generators(16)
    claims = []
    for k in range(3):
        f = [k + i for i in range(10)]
        claim = ipa_defer(ipa_commit(f, gens), ipa_open(f, 7 + k, gens), gens)
        assert claim is not None and decide(claim, gens)
        claims.append(claim)
    proof = accumulate(claims, gens)
    merged = verify_accumulation(claims, proof, gens)
    assert merged is not None and decide(merged, gens)
    assert challenge_polynomial([2, 3], 5) == 51 * 16
    # A wrong G_final passes nothing at the end, even hidden inside an accumulation.
    fake = HaloAccumulator(claims[0].challenges, claims[0].g_final * 4 % TEACHING_GROUP.p)
    assert not decide(fake, gens)
    hidden = verify_accumulation([fake, claims[1]], accumulate([fake, claims[1]], gens), gens)
    assert hidden is None or not decide(hidden, gens)


def test_accumulation_validation():
    gens = ipa_generators(8)
    claim = ipa_defer(ipa_commit([1, 2], gens), ipa_open([1, 2], 3, gens), gens)
    proof = accumulate([claim], gens)
    assert verify_accumulation([claim], proof, gens) is not None
    assert verify_accumulation([], proof, gens) is None
    assert verify_accumulation([claim], "proof", gens) is None
    assert verify_accumulation(["claim"], proof, gens) is None
    shifted = AccumulationProof(replace(proof.opening, value=proof.opening.value + 1))
    assert verify_accumulation([claim], shifted, gens) is None
    moved = AccumulationProof(replace(proof.opening, point=proof.opening.point + 1))
    assert verify_accumulation([claim], moved, gens) is None
    assert not decide("claim", gens)
    assert not decide(HaloAccumulator((1,), 1), gens)
    with pytest.raises(ValueError):
        accumulate([], gens)
