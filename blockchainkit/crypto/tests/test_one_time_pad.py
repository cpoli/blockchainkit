"""The one-time pad: perfect secrecy, and what key reuse leaks."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk

c = bk.crypto


@given(st.binary(min_size=1, max_size=64), st.data())
def test_pad_is_its_own_inverse(message, data):
    key = data.draw(st.binary(min_size=len(message), max_size=len(message)))
    assert c.one_time_pad(c.one_time_pad(message, key), key) == message


def test_every_plaintext_is_possible_for_a_given_ciphertext():
    # Shannon: for each candidate plaintext there is exactly one key.
    ciphertext = c.one_time_pad(b"ATTACK", b"\x13\x37\x00\xff\x42\x99")
    for candidate in (b"ATTACK", b"RETIRE", b"HOLD!!"):
        key = c.xor_bytes(ciphertext, candidate)
        assert c.one_time_pad(ciphertext, key) == candidate


def test_reusing_a_pad_leaks_the_xor_of_the_plaintexts():
    key = bytes(range(7, 19))
    first, second = b"meet at noon", b"send gold 42"
    leaked = c.xor_bytes(c.one_time_pad(first, key), c.one_time_pad(second, key))
    assert leaked == c.xor_bytes(first, second)


def test_pad_validation():
    with pytest.raises(ValueError, match="as long as"):
        c.one_time_pad(b"abc", b"ab")
    with pytest.raises(ValueError, match="equal length"):
        c.xor_bytes(b"a", b"ab")
    with pytest.raises(TypeError, match="bytes"):
        c.xor_bytes("a", b"a")
