"""Prime-field arithmetic, Reed-Solomon codes, and data-availability sampling."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.channels import (
    EncodingFraudProof,
    commit_shares,
    detection_probability,
    encoding_fraud_proof,
    extend,
    is_codeword,
    prove_share,
    rs_decode,
    rs_encode,
    rs_recover,
    simulate_sampling,
    verify_encoding_fraud_proof,
    verify_share,
)
from blockchainkit.channels.utils.field import (
    PRIME,
    check_prime,
    divide,
    evaluate,
    interpolate,
    inverse,
    solve,
)

P = 97

# Field arithmetic -------------------------------------------------------------


def test_field_helpers():
    assert inverse(3, P) * 3 % P == 1
    with pytest.raises(ZeroDivisionError):
        inverse(P, P)
    assert evaluate([1, 2, 3], 2, P) == 17  # 1 + 2x + 3x^2.
    assert interpolate([(0, 1), (1, 6), (2, 17)], 2, P) == 17
    with pytest.raises(ValueError, match="prime"):
        check_prime(91)
    with pytest.raises(TypeError):
        check_prime(True)


def test_solve_handles_unique_free_and_inconsistent_systems():
    assert solve([[1, 1], [1, -1]], [3, 1], P) == [2, 1]
    assert solve([[1, 1], [2, 2]], [3, 6], P) == [3, 0]  # Free variable set to 0.
    assert solve([[0, 1], [0, 2]], [1, 2], P) == [0, 1]  # Column without a pivot.
    assert solve([[1, 1], [1, 1]], [1, 2], P) is None
    assert solve([], [], P) == []


@given(
    st.lists(st.integers(0, P - 1), min_size=1, max_size=6),
    st.lists(st.integers(0, P - 1), min_size=1, max_size=4).filter(lambda d: d[-1] != 0),
)
def test_division_reconstructs_the_numerator(numerator, denominator):
    quotient, remainder = divide(numerator, denominator, P)
    product = [0] * (len(quotient) + len(denominator))
    for i, q in enumerate(quotient):
        for j, d in enumerate(denominator):
            product[i + j] += q * d
    rebuilt = [
        (product[i] + (remainder[i] if i < len(remainder) else 0)) % P
        for i in range(len(numerator))
    ]
    assert rebuilt == [c % P for c in numerator]
    assert len(remainder) == len(denominator) - 1


# Reed-Solomon -----------------------------------------------------------------


def test_encode_is_systematic_and_validated():
    codeword = rs_encode([3, 1, 4], 6)
    assert codeword[:3] == (3, 1, 4) and is_codeword(dict(enumerate(codeword)), 3)
    assert rs_encode([5], 3) == (5, 5, 5)  # Degree 0: a constant.
    with pytest.raises(ValueError, match="below the field"):
        rs_encode([PRIME], 2)
    with pytest.raises(ValueError):
        rs_encode([], 2)
    with pytest.raises(ValueError):
        rs_encode([1, 2], 1)
    with pytest.raises(ValueError, match="longer"):
        rs_encode([1], 8, prime=7)
    with pytest.raises(TypeError):
        rs_encode([1.5], 2)


@given(
    st.lists(st.integers(0, P - 1), min_size=1, max_size=5),
    st.integers(0, 5),
    st.randoms(use_true_random=False),
)
def test_any_k_shares_recover_the_codeword(data, extra, rng):
    n = len(data) + extra
    codeword = rs_encode(data, n, prime=P)
    kept = rng.sample(range(n), len(data))
    assert rs_recover({i: codeword[i] for i in kept}, len(data), n, prime=P) == codeword


def test_recover_rejects_bad_inputs():
    with pytest.raises(ValueError, match="at least k"):
        rs_recover({0: 1}, 2, 4)
    with pytest.raises(ValueError, match="out of range"):
        rs_recover({0: 1, 9: 2}, 2, 4)
    with pytest.raises(ValueError, match="not on one polynomial"):
        rs_recover({0: 3, 1: 1, 2: 4, 3: 13}, 3, 6)
    with pytest.raises(ValueError, match="at least k"):
        is_codeword({}, 1)


@given(
    st.lists(st.integers(0, P - 1), min_size=1, max_size=4),
    st.integers(0, 6),
    st.randoms(use_true_random=False),
)
def test_berlekamp_welch_corrects_up_to_half_the_redundancy(data, extra, rng):
    k, n = len(data), len(data) + extra
    received: list[int | None] = list(rs_encode(data, n, prime=P))
    erased = rng.randint(0, extra)
    positions = rng.sample(range(n), n)
    for p in positions[:erased]:
        received[p] = None
    capacity = (n - erased - k) // 2
    for p in positions[erased : erased + capacity]:
        received[p] = (received[p] + rng.randint(1, P - 1)) % P
    assert rs_decode(received, k, prime=P) == tuple(data)


def test_decode_reports_too_many_errors():
    with pytest.raises(ValueError, match="at least k"):
        rs_decode([1, None, None], 2)
    # Inconsistent system: no locator of degree e fits.
    with pytest.raises(ValueError, match="too many errors"):
        rs_decode([0, 0, 0, 1, 2], 2, prime=P)
    # A locator is found but does not divide Q.
    with pytest.raises(ValueError, match="too many errors"):
        rs_decode([0, 0, 1, 1], 2, prime=P)


# Data availability ------------------------------------------------------------


def test_shares_verify_against_the_root():
    block = extend([3, 1, 4])
    assert block.k == 3 and len(block.shares) == 6
    for position, value in enumerate(block.shares):
        assert verify_share(value, prove_share(block, position), block.root)
    assert not verify_share(13, prove_share(block, 3), block.root)
    with pytest.raises(ValueError, match="fewer shares"):
        commit_shares(3, (1, 2))


def test_detection_probability_matches_sampling():
    assert detection_probability(0.5, 0) == 0
    assert detection_probability(0.0, 50) == 0
    assert detection_probability(0.5, 10) == pytest.approx(1 - 2**-10)
    with pytest.raises(ValueError):
        detection_probability(1.5, 3)
    block = extend(list(range(32)))
    withheld = set(range(33, 64))  # 31 of 64: one fewer than needed to hide anything.
    result = simulate_sampling(block, withheld, clients=400, samples=1, seed=3)
    assert result.detected == pytest.approx(31 / 64, abs=0.06)
    assert result.collected == 33 and result.recoverable
    hidden = simulate_sampling(block, set(range(31, 64)), clients=200, samples=8, seed=3)
    assert hidden.detected > 0.99 and not hidden.recoverable
    few = simulate_sampling(block, (), clients=1, samples=2, seed=0)
    assert few.detected == 0 and few.collected == 2 and not few.recoverable
    with pytest.raises(ValueError, match="more samples"):
        simulate_sampling(block, (), clients=1, samples=65)


def test_encoding_fraud_proofs():
    honest = extend([3, 1, 4])
    assert encoding_fraud_proof(honest) is None
    bad = commit_shares(3, (3, 1, 4, 12, 26, 43))
    proof = encoding_fraud_proof(bad)
    assert proof is not None and proof.positions == (0, 1, 2, 4)
    assert verify_encoding_fraud_proof(proof, bad.root, 3)
    assert not verify_encoding_fraud_proof(proof, honest.root, 3)  # Shares not committed.
    assert not verify_encoding_fraud_proof(proof, bad.root, 2)  # Wrong size.
    shuffled = EncodingFraudProof((1, 0, 2, 4), proof.shares, (proof.proofs[1], *proof.proofs[1:]))
    assert not verify_encoding_fraud_proof(shuffled, bad.root, 3)  # Proof for another position.
    # A "proof" built from shares that are on the polynomial proves nothing.
    consistent = EncodingFraudProof(
        (0, 1, 2, 3),
        honest.shares[:4],
        tuple(prove_share(honest, p) for p in range(4)),
    )
    assert not verify_encoding_fraud_proof(consistent, honest.root, 3)
