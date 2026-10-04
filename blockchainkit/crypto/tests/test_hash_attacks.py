"""Birthday collisions, Lamport signatures, Merkle-Damgard length extension, HMAC."""

import hashlib
import hmac as std_hmac

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk

c = bk.crypto


@pytest.mark.parametrize("bits", [8, 16, 24])
def test_birthday_collisions_cost_about_the_square_root(bits):
    result = c.find_collision(bits)
    assert result.first != result.second
    assert c.truncated_hash(result.first, bits) == c.truncated_hash(result.second, bits)
    assert result.digest == c.truncated_hash(result.first, bits)
    assert result.trials < 8 * 2 ** (bits / 2)


def test_collision_search_is_bounded_and_validated():
    with pytest.raises(TimeoutError):
        c.find_collision(40, max_trials=10)
    with pytest.raises(ValueError, match="bits"):
        c.find_collision(0)
    assert c.truncated_hash(b"abc", 8) == hashlib.sha256(b"abc").digest()[0]


def test_lamport_signature_verifies_and_rejects_changes():
    key = c.lamport_keypair(b"seed")
    signature = c.lamport_sign(b"pay Bob", key)
    assert len(signature) == 256
    assert c.lamport_verify(b"pay Bob", signature, key.public)
    assert not c.lamport_verify(b"pay Eve", signature, key.public)
    assert not c.lamport_verify(b"pay Bob", signature[:-1], key.public)
    assert not c.lamport_verify(b"pay Bob", (bytes(32),) + signature[1:], key.public)


def test_lamport_signing_reveals_half_the_private_key():
    key = c.lamport_keypair(b"seed")
    revealed = set(c.lamport_sign(b"one", key))
    private = {value for pair in key.private for value in pair}
    assert revealed <= private and len(revealed) == 256


@given(st.binary(max_size=200))
def test_merkle_damgard_sha256_matches_hashlib(data):
    assert c.merkle_damgard_sha256(data) == hashlib.sha256(data).digest()


def test_padding_makes_whole_blocks_and_encodes_the_length():
    for length in (0, 55, 56, 64, 119):
        padding = c.sha256_padding(length)
        assert (length + len(padding)) % 64 == 0
        assert padding[0] == 0x80 and padding[-8:] == (8 * length).to_bytes(8, "big")


def test_length_extension_forges_a_naive_mac_without_the_key():
    secret, message, suffix = b"k" * 16, b"amount=10", b"&amount=1000000"
    tag = c.naive_mac(secret, message)
    glue, forged = c.length_extension(tag, len(secret) + len(message), suffix)
    assert forged == c.naive_mac(secret, message + glue + suffix)


def test_hmac_matches_the_standard_library_and_resists_extension():
    key, message = b"key", b"amount=10"
    tag = c.hmac_sha256(key, message)
    assert tag == std_hmac.new(key, message, hashlib.sha256).digest()
    glue, forged = c.length_extension(tag, len(key) + len(message), b"&x")
    assert forged != c.hmac_sha256(key, message + glue + b"&x")


def test_hash_helpers_validate_inputs():
    with pytest.raises(ValueError, match="32 bytes"):
        c.length_extension(b"short", 1, b"x")
    with pytest.raises(ValueError, match="64 bytes"):
        c.sha256_compress(c.SHA256_IV, b"x")
    for function in (c.naive_mac, c.hmac_sha256):
        with pytest.raises(TypeError):
            function("key", b"m")


@pytest.mark.parametrize(
    "call,error",
    [
        (lambda: c.truncated_hash(b"x", 257), ValueError),
        (lambda: c.find_collision(49), ValueError),
        (lambda: c.find_collision(8, prefix="p"), TypeError),
        (lambda: c.lamport_keypair("seed"), TypeError),
        (lambda: c.lamport_sign("m", c.lamport_keypair(b"s")), TypeError),
        (lambda: c.sha256_compress((0,) * 7, bytes(64)), ValueError),
        (lambda: c.merkle_damgard_sha256("abc"), TypeError),
        (lambda: c.length_extension(bytes(32), 3, "x"), TypeError),
    ],
)
def test_hash_constructions_reject_bad_arguments(call, error):
    with pytest.raises(error):
        call()


def test_lamport_key_repr_is_short():
    assert repr(c.lamport_keypair(b"s")).endswith("pairs=256)")
