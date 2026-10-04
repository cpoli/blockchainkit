"""Known vectors, algebraic properties, malformed inputs, and teaching attacks."""

from dataclasses import replace
from itertools import combinations
from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import blockchainkit as bk
from blockchainkit.crypto import is_prime

c = bk.crypto


def test_hash_vectors():
    assert c.sha256(b"abc").hex() == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert c.sha256(b"").hex() == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert c.hash256(b"") == c.sha256(c.sha256(b""))
    with pytest.raises(TypeError):
        c.sha256("abc")


def test_commitments_bind_and_frame_openings():
    salt = b"s" * 16
    digest = c.commit(b"bid=10", salt)
    assert c.verify_commitment(digest, b"bid=10", salt)
    assert not c.verify_commitment(digest, b"bid=11", salt)
    assert not c.verify_commitment(digest, b"bid=10", b"t" * 16)
    assert c.commit(b"ab", salt) != c.commit(b"b", salt + b"a")
    with pytest.raises(ValueError):
        c.commit(b"data", b"short")
    with pytest.raises(TypeError):
        c.commit("data", salt)
    assert c.hamming_distance(bytes(2), b"\xff\x0f") == 12
    with pytest.raises(ValueError):
        c.hamming_distance(b"", b"a")


@pytest.mark.parametrize("value", [2, 3, 7919, 65537, 2**61 - 1])
def test_primes(value):
    assert is_prime(value)


@pytest.mark.parametrize("value", [-1, 0, 1, 4, 561, 1105, 341550071728321])
def test_composites(value):
    assert not is_prime(value)


def test_primality_bounds():
    with pytest.raises(ValueError):
        is_prime(2**64 + 1)
    with pytest.raises(ValueError):
        is_prime(True)


def test_diffie_hellman_and_impersonation():
    group = c.DHGroup()
    assert group.public(3) == 8
    assert group.shared(group.public(7), 3) == 12
    assert group.shared(group.public(7), 3) == group.shared(group.public(3), 7)
    # A substituted attacker key establishes a different, unauthenticated secret.
    assert group.shared(group.public(4), 3) == group.shared(group.public(3), 4)
    for peer in (0, 1, 5, 23, -1):
        with pytest.raises(ValueError):
            group.shared(peer, 3)
    for private in (0, 11, True):
        with pytest.raises(ValueError):
            group.public(private)
    for params in ((21, 5, 2), (23, 7, 2), (23, 11, 5)):
        with pytest.raises(ValueError):
            c.DHGroup(*params)


def test_rsa_known_vector_blinding_and_malleability():
    key = c.rsa_keypair()
    assert (key.n, key.e, key.d) == (3233, 17, 2753)
    assert key.encrypt(65) == 2790
    assert key.decrypt(2790) == 65
    for message in (0, 1, 53, 61, 123, 3232):
        assert key.decrypt(key.encrypt(message)) == message
    blinded = c.rsa_blind(42, 7, key)
    signature = c.rsa_unblind(key.decrypt(blinded), 7, key)
    assert key.encrypt(signature) == 42
    altered = key.encrypt(42) * pow(2, key.e, key.n) % key.n
    assert key.decrypt(altered) == 84
    for params in ((61, 61, 17), (15, 53, 17), (61, 53, 12)):
        with pytest.raises(ValueError):
            c.rsa_keypair(*params)
    for value in (-1, 3233, True):
        with pytest.raises(ValueError):
            key.encrypt(value)
    with pytest.raises(ValueError):
        c.rsa_blind(42, 61, key)


def test_shamir_all_threshold_subsets():
    shares = c.split_secret(1234, 3, 5, randbelow=Random(7).randrange)
    for subset in combinations(shares, 3):
        assert c.recover_secret(subset) == 1234
    assert c.recover_secret(shares) == 1234
    assert c.split_secret(12, 2, 3, randbelow=Random(1).randrange) == c.split_secret(
        12, 2, 3, randbelow=Random(1).randrange
    )
    # For one known point, every proposed secret admits a compatible line.
    x, y = shares[0]
    for secret in range(17):
        slope = (y - secret) * pow(x, -1, 2089) % 2089
        assert (secret + slope * x) % 2089 == y


@pytest.mark.parametrize("args", [(5, 1, 3), (5, 4, 3), (2089, 2, 3), (1, 2, 2089)])
def test_sharing_rejects_invalid_parameters(args):
    with pytest.raises(ValueError):
        c.split_secret(*args)


def test_sharing_rejects_invalid_shares():
    for shares in ([], [(1, 2), (1, 3)], [(0, 1)], [(1, 2089)]):
        with pytest.raises(ValueError):
            c.recover_secret(shares)
    with pytest.raises(ValueError):
        c.split_secret(5, 2, 3, randbelow=lambda n: n)


def test_curve_vectors_and_validation():
    curve = c.TOY_CURVE
    assert c.multiply(2, curve.generator, curve) == (6, 3)
    assert c.multiply(3, curve.generator, curve) == (10, 6)
    assert c.multiply(19, curve.generator, curve) is None
    assert c.add(curve.generator, (5, 16), curve) is None
    assert c.multiply(-1, curve.generator, curve) == (5, 16)
    assert c.multiply(0, curve.generator, curve) is None
    assert c.add(None, None, curve) is None
    assert c.public_key(2)[0] == int(
        "c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5", 16
    )
    assert not curve.contains((22, 1))
    assert not curve.contains((1,))
    assert not curve.contains((True, 1))
    for private in (0, 19, True):
        with pytest.raises(ValueError):
            c.public_key(private, curve)
    with pytest.raises(ValueError):
        c.add((0, 0), None, curve)
    with pytest.raises(ValueError):
        c.encode_point(None)
    for args in ((17, 0, 0, (0, 0), 19), (17, 2, 2, (1, 1), 19), (17, 2, 2, (5, 1), 17)):
        with pytest.raises(ValueError):
            c.Curve(*args)


@given(st.integers(-100, 100), st.integers(-100, 100))
def test_group_distributivity(a, b):
    curve = c.TOY_CURVE
    assert c.multiply(a + b, curve.generator, curve) == c.add(
        c.multiply(a, curve.generator, curve), c.multiply(b, curve.generator, curve), curve
    )


@settings(max_examples=15)
@given(st.binary(max_size=50), st.integers(1, 10_000), st.integers(1, 10_000))
def test_signature_roundtrip(message, private, nonce):
    signature = c.sign(message, private, nonce=nonce)
    assert c.verify(message, signature, c.public_key(private))
    assert not c.verify(message + b"!", signature, c.public_key(private))


def test_schnorr_nonce_reuse_and_transcript_simulation():
    public = c.public_key(42)
    first, second = c.sign(b"one", 42, nonce=17), c.sign(b"two", 42, nonce=17)
    c1 = c.challenge(b"one", first.commitment, public)
    c2 = c.challenge(b"two", second.commitment, public)
    assert c.recover_reused_nonce_key(first, second, c1, c2) == 42
    # A transcript simulator picks c,s first; it does not know the private key.
    challenge, response = 11, 123
    commitment = c.add(
        c.multiply(response, c.SECP256K1.generator, c.SECP256K1),
        c.multiply(-challenge, public, c.SECP256K1),
        c.SECP256K1,
    )
    assert c.verify_transcript(public, commitment, challenge, response)
    assert not c.verify_transcript(public, commitment, challenge + 1, response)
    assert not c.verify(b"one", replace(first, response=c.SECP256K1.order), public)
    assert not c.verify(b"one", replace(first, commitment=(0, 0)), public)
    assert not c.verify(b"one", first, None)
    assert not c.verify_transcript(public, first.commitment, -1, 0)
    with pytest.raises(ValueError):
        c.recover_reused_nonce_key(first, second, c1, c1)
    with pytest.raises(ValueError):
        c.recover_reused_nonce_key(first, c.sign(b"two", 42, nonce=18), c1, c2)
    assert c.verify(b"random nonce", c.sign(b"random nonce", 42), public)
