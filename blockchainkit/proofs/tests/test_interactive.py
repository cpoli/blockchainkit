"""Schwartz-Zippel, sum-check, IP = PSPACE, PCPs, and Kilian and Micali arguments."""

from dataclasses import replace
from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blockchainkit.proofs import (
    CNF,
    QBF,
    CSProof,
    HadamardProof,
    QuadraticSystem,
    hadamard_proof,
    identity_test,
    kilian_argument,
    micali_proof,
    multilinear_extension,
    pcp_verify,
    run_pcp_verifier,
    schwartz_zippel_bound,
    sumcheck,
    tqbf_operators,
    tqbf_protocol,
    verify_cs_proof,
    verify_sumcheck,
)
from blockchainkit.proofs.systems.ip_pspace import _targets

FORMULA = CNF(3, ((1, 2), (-2, 3), (-1, -3)))
SYSTEM = QuadraticSystem(3, ((((0, 1), (2, 2)), 1), (((1, 2),), 0), (((0, 0), (1, 1)), 0)))
UNSAT = QuadraticSystem(2, ((((0, 0),), 1), (((0, 0),), 0)))


def test_identity_test_never_rejects_equal_polynomials_and_bounds_false_acceptance():
    square = lambda v: (v[0] + v[1]) ** 2  # noqa: E731
    expanded = lambda v: v[0] ** 2 + 2 * v[0] * v[1] + v[1] ** 2  # noqa: E731
    assert identity_test(square, expanded, 2, trials=20).equal
    result = identity_test(square, lambda v: v[0] ** 2 + v[1] ** 2, 2, trials=5)
    assert not result.equal and result.trials == 1 and result.witness is not None
    # x(x-1)(x-2) vanishes at three of 97 points: the exact false-acceptance rate.
    cubic = lambda v: v[0] * (v[0] - 1) * (v[0] - 2)  # noqa: E731
    accepted = sum(identity_test(cubic, lambda v: 0, 1, 97, seed=s).equal for s in range(2000))
    assert abs(accepted / 2000 - 3 / 97) < 0.015
    assert schwartz_zippel_bound(3, 97) == 3 / 97 and schwartz_zippel_bound(200, 97) == 1.0
    with pytest.raises(TypeError, match="integers"):
        identity_test(lambda v: 1.0, lambda v: 1, 1)


def test_cnf_arithmetization_matches_truth_values():
    for bits in [(0, 0, 0), (1, 0, 1), (0, 1, 1), (1, 1, 0)]:
        assert FORMULA.evaluate(bits, 97) == FORMULA.is_satisfied(bits)
    assert FORMULA.count_solutions() == 2 and FORMULA.degree == 2
    with pytest.raises(ValueError, match="coordinates"):
        FORMULA.evaluate((1, 0), 97)
    with pytest.raises(ValueError, match="0s and 1s"):
        FORMULA.is_satisfied((2, 0, 0))
    for bad in [(), ((),), ((0,),), ((4,),), [(1,)]]:
        with pytest.raises(ValueError):
            CNF(3, bad)


@given(st.lists(st.integers(0, 96), min_size=8, max_size=8))
def test_multilinear_extension_agrees_on_the_cube(values):
    for index in range(8):
        bits = [index >> 2 & 1, index >> 1 & 1, index & 1]
        assert multilinear_extension(values, bits, 97) == values[index]
    with pytest.raises(ValueError):
        multilinear_extension(values, [0, 1], 97)


def test_sumcheck_accepts_the_true_count_and_rarely_a_false_one():
    f = lambda x: FORMULA.evaluate(x, 97)  # noqa: E731
    run = sumcheck(f, 3, FORMULA.degree, 97)
    assert run.accepted and run.claim == run.true_sum == 2 and len(run.challenges) == 3
    lucky = sum(sumcheck(f, 3, 2, 97, claim=5, seed=s).accepted for s in range(1500))
    assert 0 < lucky / 1500 <= 3 * 2 / 97 + 0.02
    assert not sumcheck(f, 3, 2, claim=5).accepted


def test_verify_sumcheck_rejects_tampered_transcripts():
    f = lambda x: FORMULA.evaluate(x, 97)  # noqa: E731
    run = sumcheck(f, 3, 2, 97)
    polys, challenges = list(run.polynomials), list(run.challenges)
    assert verify_sumcheck(f, run.claim, polys, challenges, 2, 97)
    assert not verify_sumcheck(f, run.claim + 1, polys, challenges, 2, 97)
    assert not verify_sumcheck(f, run.claim, [(0, 0, 0, 1)] + polys[1:], challenges, 2, 97)
    with pytest.raises(ValueError):
        verify_sumcheck(f, run.claim, polys, challenges[:2], 2, 97)
    with pytest.raises(TypeError, match="integers"):
        sumcheck(lambda x: None, 2, 1, 97)


def test_qbf_validation_and_evaluation():
    assert QBF("AE", CNF(2, ((1, 2), (-1, -2)))).evaluate()
    assert not QBF("EA", CNF(2, ((1, 2), (-1, -2)))).evaluate()
    with pytest.raises(TypeError):
        QBF("A", "x")
    with pytest.raises(ValueError):
        QBF("AX", CNF(2, ((1,),)))
    with pytest.raises(ValueError):
        QBF("A", CNF(2, ((1,),)))


@settings(max_examples=25, deadline=None)
@given(
    st.text("AE", min_size=2, max_size=3),
    st.lists(
        st.lists(
            st.integers(1, 3).flatmap(lambda v: st.sampled_from([v, -v])), min_size=1, max_size=3
        ),
        min_size=1,
        max_size=4,
    ),
)
def test_tqbf_protocol_accepts_the_truth_and_keeps_degrees_small(quantifiers, clauses):
    n = len(quantifiers)
    clauses = [[lit for lit in clause if abs(lit) <= n] or [1] for clause in clauses]
    qbf = QBF(quantifiers, CNF(n, tuple(tuple(c) for c in clauses)))
    run = tqbf_protocol(qbf, seed=3)
    assert run.accepted and run.true_value == int(qbf.evaluate())
    assert run.max_degree <= max(2, qbf.formula.degree)
    assert len(run.rounds) == len(tqbf_operators(qbf)) == n + n * (n + 1) // 2
    assert not tqbf_protocol(qbf, claim=1 - run.true_value, seed=3).accepted


def test_tqbf_without_linearization_has_growing_degrees():
    qbf = QBF("AEA", CNF(3, ((1, 2, 3), (-1, 2), (-2, -3), (1, -3))))
    linear = tqbf_protocol(qbf, seed=1)
    raw = tqbf_protocol(qbf, seed=1, linearize=False)
    assert linear.accepted and raw.accepted and len(raw.rounds) == 3
    assert raw.max_degree > linear.max_degree
    lucky = sum(
        tqbf_protocol(qbf, 13, claim=1 - linear.true_value, seed=s).accepted for s in range(300)
    )
    assert lucky < 300
    with pytest.raises(TypeError):
        tqbf_protocol("AE")
    with pytest.raises(ValueError, match="0 or 1"):
        tqbf_protocol(qbf, claim=2)


def test_cheating_targets_satisfy_every_operator_check():
    p = 97
    for operator in "AEL":
        for claim in (0, 1, 40):
            for high in (0, 1, 5):
                for x in (0, 1, 7):
                    low, top = _targets(operator, claim, high, x, p)
                    if operator == "A":
                        assert low * top % p == claim
                    elif operator == "E":
                        assert (1 - (1 - low) * (1 - top)) % p == claim
                    else:
                        assert ((1 - x) * low + x * top) % p == claim


def test_quadratic_systems_and_the_hadamard_pcp():
    assert SYSTEM.solutions() == ((0, 0, 1), (1, 1, 0))
    proof = hadamard_proof([1, 1, 0])
    assert len(proof.bits) == 8 + 512
    assert all(pcp_verify(SYSTEM, proof, seed=s).accepted for s in range(100))
    run = pcp_verify(SYSTEM, proof, repetitions=3)
    assert run.queries == 42 and run.failed_test is None
    wrong = hadamard_proof([1, 0, 1])  # A valid encoding of a non-solution.
    rejected = [pcp_verify(SYSTEM, wrong, seed=s) for s in range(400)]
    assert 0.3 < sum(not r.accepted for r in rejected) / 400 < 0.7
    assert {r.failed_test for r in rejected if not r.accepted} == {"the equations"}
    assert not pcp_verify(UNSAT, hadamard_proof([1, 0]), repetitions=12).accepted


def test_pcp_tests_catch_each_kind_of_corruption():
    proof = hadamard_proof([1, 1, 0])
    rng = Random(4)

    def failures(bits):
        corrupted = HadamardProof(tuple(bits[:8]), tuple(bits[8:]))
        return {pcp_verify(SYSTEM, corrupted, seed=s).failed_test for s in range(300)}

    linear = list(proof.bits)
    for i in rng.sample(range(8), 3):
        linear[i] ^= 1
    assert "linearity of the linear table" in failures(linear)
    quadratic = list(proof.bits)
    for i in rng.sample(range(8, 520), 200):
        quadratic[i] ^= 1
    assert "linearity of the quadratic table" in failures(quadratic)
    # Encode a different, consistent-looking tensor: u (x) u' with u != u'.
    mixed = hadamard_proof([1, 1, 0]).linear + hadamard_proof([0, 1, 1]).quadratic
    assert "tensor consistency" in failures(mixed)


def test_pcp_validation():
    with pytest.raises(ValueError):
        hadamard_proof([1, 0, 1, 0, 1])
    with pytest.raises(TypeError):
        pcp_verify(SYSTEM, [0, 1])
    with pytest.raises(ValueError, match="tables"):
        pcp_verify(SYSTEM, hadamard_proof([1, 1]))
    with pytest.raises(ValueError):
        QuadraticSystem(5, ((((0, 0),), 1),))
    with pytest.raises(ValueError):
        QuadraticSystem(2, ())
    with pytest.raises(ValueError):
        QuadraticSystem(2, ((((0, 0),), 2),))
    with pytest.raises(ValueError):
        QuadraticSystem(2, ((((0, 2),), 1),))
    with pytest.raises(ValueError):
        SYSTEM.is_satisfied((1, 1))
    assert run_pcp_verifier(SYSTEM, lambda i: 0, Random(0), 1).queries > 0


def test_kilian_argument_opens_only_the_queried_bits():
    proof = hadamard_proof([1, 1, 0])
    run = kilian_argument(SYSTEM, proof, repetitions=4)
    assert run.accepted and run.queries == 56 and run.proof_length == 520
    assert 32 + 56 * (9 + 32 * 9) <= run.communication <= 32 + 56 * (9 + 32 * 10)
    lying = kilian_argument(SYSTEM, proof, repetitions=4, respond=lambda i: 1 - proof.bits[i])
    assert not lying.accepted
    assert not kilian_argument(SYSTEM, proof, respond=lambda i: 2).accepted
    with pytest.raises(TypeError):
        kilian_argument(SYSTEM, list(proof.bits))


def test_micali_proofs_verify_and_resist_tampering_but_not_grinding():
    proof = hadamard_proof([0, 0, 1])
    cs = micali_proof(SYSTEM, proof, repetitions=4, salt=7)
    assert verify_cs_proof(SYSTEM, cs, repetitions=4)
    assert 40 + 56 * (9 + 32 * 9) <= cs.size <= 40 + 56 * (9 + 32 * 10)
    assert not verify_cs_proof(SYSTEM, cs, repetitions=5)  # Runs out of openings.
    assert not verify_cs_proof(
        SYSTEM, replace(cs, openings=cs.openings + cs.openings[:1]), repetitions=4
    )
    assert not verify_cs_proof(SYSTEM, replace(cs, salt=8), repetitions=4)
    first = cs.openings[0]
    for bad in (
        replace(first, bit=1 - first.bit),
        replace(first, bit=2),
        replace(first, position=first.position + 1),
        replace(first, path=next(o.path for o in cs.openings if o.position != first.position)),
    ):
        tampered = replace(cs, openings=(bad,) + cs.openings[1:])
        assert not verify_cs_proof(SYSTEM, tampered, repetitions=4)
    wrong = hadamard_proof([1, 0, 1])
    salts = [s for s in range(64) if verify_cs_proof(SYSTEM, micali_proof(SYSTEM, wrong, salt=s))]
    assert salts  # A cheater with one repetition finds a passing salt quickly.
    with pytest.raises(TypeError):
        verify_cs_proof(SYSTEM, "proof")
    assert isinstance(cs, CSProof)
