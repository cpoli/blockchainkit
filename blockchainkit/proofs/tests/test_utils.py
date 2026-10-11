"""Field and polynomial arithmetic, transcripts, and group helpers."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.crypto import TEACHING_GROUP, TOY_CURVE, multiply
from blockchainkit.proofs import (
    FIELD_GENERATOR,
    FIELD_PRIME,
    Transcript,
    degree,
    domain,
    evaluate_on_domain,
    independent_generators,
    interpolate,
    interpolate_on_domain,
    linear_combination,
    multi_exponent,
    poly_add,
    poly_divmod,
    poly_eval,
    poly_mul,
    poly_scale,
    poly_sub,
    polynomial,
    root_of_unity,
    vanishing_polynomial,
)

P = 97
coefficients = st.lists(st.integers(-200, 200), max_size=8)


@given(coefficients, coefficients, st.integers(0, P - 1))
def test_ring_operations_agree_with_evaluation(a, b, x):
    assert poly_eval(poly_add(a, b, P), x, P) == (poly_eval(a, x, P) + poly_eval(b, x, P)) % P
    assert poly_eval(poly_sub(a, b, P), x, P) == (poly_eval(a, x, P) - poly_eval(b, x, P)) % P
    assert poly_eval(poly_mul(a, b, P), x, P) == poly_eval(a, x, P) * poly_eval(b, x, P) % P
    assert poly_eval(poly_scale(a, 5, P), x, P) == 5 * poly_eval(a, x, P) % P


@given(coefficients, coefficients.filter(lambda c: any(v % P for v in c)))
def test_division_with_remainder(numerator, denominator):
    quotient, remainder = poly_divmod(numerator, denominator, P)
    assert degree(remainder) < degree(polynomial(denominator, P))
    rebuilt = poly_add(poly_mul(quotient, denominator, P), remainder, P)
    assert rebuilt == polynomial(numerator, P)


@given(st.lists(st.integers(0, P - 1), min_size=1, max_size=8, unique=True), st.data())
def test_interpolation_passes_through_its_points(xs, data):
    ys = data.draw(st.lists(st.integers(0, P - 1), min_size=len(xs), max_size=len(xs)))
    poly = interpolate(list(zip(xs, ys, strict=True)), P)
    assert degree(poly) < len(xs)
    assert all(poly_eval(poly, x, P) == y for x, y in zip(xs, ys, strict=True))


@given(st.lists(st.integers(0, FIELD_PRIME - 1), max_size=16), st.sampled_from([1, 31, 7]))
def test_fft_matches_pointwise_evaluation_and_inverts(coeffs, offset):
    values = evaluate_on_domain(coeffs, 16, offset=offset)
    assert values == tuple(poly_eval(coeffs, x) for x in domain(16, offset=offset))
    assert interpolate_on_domain(values, offset=offset) == polynomial(coeffs)


def test_polynomial_helpers_and_their_validation():
    assert polynomial([3, -1, 0], 7) == (3, 6)
    assert degree(()) == -1 and degree([0, 0]) == -1 and degree([1, 2]) == 1
    assert poly_mul([], [1, 2], P) == ()
    assert poly_divmod([1, 2], [0, 0, 5], P) == ((), (1, 2))
    assert vanishing_polynomial([1, 2], P) == (2, P - 3, 1)
    assert interpolate([(0, 0), (1, 0)], P) == ()
    with pytest.raises(ZeroDivisionError):
        poly_divmod([1], [0], P)
    with pytest.raises(ValueError, match="distinct"):
        interpolate([(1, 2), (1 + P, 3)], P)
    with pytest.raises(TypeError, match="coefficients"):
        poly_add([1.5], [], P)
    with pytest.raises(TypeError, match="x must be"):
        poly_eval([1], 1.0, P)
    with pytest.raises(TypeError, match="scalar"):
        poly_scale([1], True, P)
    with pytest.raises(ValueError, match="prime"):
        poly_add([1], [1], 91)


def test_roots_of_unity_and_domains():
    w = root_of_unity(8)
    assert w == pow(FIELD_GENERATOR, (FIELD_PRIME - 1) // 8, FIELD_PRIME)
    assert root_of_unity(1, P) == 1
    w97 = root_of_unity(32, P)
    assert pow(w97, 32, P) == 1 and pow(w97, 16, P) != 1
    assert len(set(domain(8))) == 8
    with pytest.raises(ValueError, match="power of two"):
        root_of_unity(6)
    with pytest.raises(ValueError, match="power of two"):
        root_of_unity(64, P)
    with pytest.raises(ValueError, match="below n"):
        evaluate_on_domain([1, 2, 3], 2)
    with pytest.raises(ValueError, match="invertible"):
        interpolate_on_domain([1, 2], offset=FIELD_PRIME)


def test_transcripts_are_deterministic_and_bind_every_message():
    def run(*messages):
        transcript = Transcript(b"test")
        for label, value in messages:
            transcript.append(label, value)
        return transcript.challenge("c", 2**61)

    base = run(("a", 5), ("b", b"xy"), ("c", [1, None, (2, 3)]))
    assert base == run(("a", 5), ("b", b"xy"), ("c", [1, None, (2, 3)]))
    assert base != run(("a", 6), ("b", b"xy"), ("c", [1, None, (2, 3)]))
    assert base != run(("a", 5), ("b", b"xy"), ("c", [1, None, (2, 4)]))
    assert run(("a", b"\x01")) != run(("a", 1))
    transcript = Transcript(b"test")
    assert 0 <= transcript.challenge("c", 10) < 10
    with pytest.raises(TypeError):
        Transcript("text")
    with pytest.raises(TypeError, match="label"):
        transcript.append(3, 1)
    with pytest.raises(ValueError, match="non-negative"):
        transcript.append("x", -1)
    with pytest.raises(TypeError, match="absorb"):
        transcript.append("x", 1.5)
    with pytest.raises(ValueError, match="2\\*\\*64"):
        transcript.challenge("c", 2**64)


def test_generators_skip_degenerate_hashes(monkeypatch):
    from blockchainkit.proofs.utils import groups

    real = groups.sha256
    calls = []

    def first_hash_is_zero(data):
        calls.append(data)
        return bytes(32) if len(calls) == 1 else real(data)

    monkeypatch.setattr(groups, "sha256", first_hash_is_zero)
    assert len(independent_generators(2, "zero")) == 2 and len(calls) == 3


def test_generators_and_linear_combinations():
    gens = independent_generators(5, "test")
    assert len(set(gens)) == 5
    assert all(pow(g, TEACHING_GROUP.q, TEACHING_GROUP.p) == 1 for g in gens)
    assert independent_generators(3, "test") == gens[:3]
    assert independent_generators(3, "other") != gens[:3]
    assert multi_exponent(gens[:2], [2, 3], TEACHING_GROUP) == (
        pow(gens[0], 2, TEACHING_GROUP.p) * pow(gens[1], 3, TEACHING_GROUP.p) % TEACHING_GROUP.p
    )
    g = TOY_CURVE.generator
    assert linear_combination([2, 0, 3], [g, g, g], TOY_CURVE) == multiply(5, g, TOY_CURVE)
    assert linear_combination([], [], TOY_CURVE) is None
    with pytest.raises(TypeError):
        independent_generators(2, 3)
    with pytest.raises(ValueError):
        multi_exponent([1], [], TEACHING_GROUP)
    with pytest.raises(ValueError):
        linear_combination([1], [], TOY_CURVE)
