"""BCH codes, check digits, Base58Check, Bech32 and Bech32m."""

import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.crypto import SECP256K1, public_key
from blockchainkit.wallets import (
    BECH32_CONSTANTS,
    CHARSET,
    BCHCode,
    base58_decode,
    base58_encode,
    base58check_decode,
    base58check_encode,
    bech32_decode,
    bech32_encode,
    convert_bits,
    detection_rates,
    is_valid_address,
    luhn_digit,
    luhn_valid,
    minimal_polynomial,
    p2pkh_address,
    p2wpkh_address,
    polymod,
    segwit_decode,
    segwit_encode,
    sum_digit,
    sum_valid,
    verhoeff_digit,
    verhoeff_valid,
)
from blockchainkit.wallets.utils import GaloisField

# Galois fields and BCH codes --------------------------------------------------


@pytest.mark.parametrize("m", range(3, 9))
def test_alpha_generates_every_nonzero_element(m):
    field = GaloisField(m)
    assert sorted(field.power(e) for e in range(field.order)) == list(range(1, field.order + 1))
    for a in range(1, field.order + 1):
        assert field.multiply(a, field.inverse(a)) == 1
        assert field.power(field.log(a)) == a
    assert field.multiply(0, 5) == field.multiply(5, 0) == 0


def test_galois_field_rejects_bad_degrees_and_zero_logarithms():
    for m in (2, 9):
        with pytest.raises(ValueError):
            GaloisField(m)
    with pytest.raises(ValueError, match="nonzero"):
        GaloisField(4).log(0)


def test_known_generators_and_dimensions():
    # Lin and Costello, Table 6.1 and Appendix C.
    assert BCHCode(4, 2).generator == 0b111010001
    assert BCHCode(4, 3).generator == 0b10100110111
    assert [(BCHCode(m, t).n, BCHCode(m, t).k) for m, t in [(4, 1), (5, 2), (5, 3), (8, 4)]] == [
        (15, 11),
        (31, 21),
        (31, 16),
        (255, 223),
    ]
    assert BCHCode(4, 2).designed_distance == 5
    assert minimal_polynomial(GaloisField(4), 0) == 0b11  # x + 1, the minimal polynomial of 1.


def test_bch_rejects_impossible_codes_and_malformed_words():
    with pytest.raises(ValueError, match="no message bits"):
        BCHCode(3, 4)
    code = BCHCode(4, 2)
    with pytest.raises(ValueError, match="7 bits"):
        code.encode([1, 0])
    with pytest.raises(ValueError, match="0 and 1"):
        code.decode([2] * 15)
    with pytest.raises(ValueError, match="0 and 1"):
        code.is_codeword([True] * 15)


@given(st.integers(0, 2**31), st.sampled_from([(4, 2), (4, 3), (5, 3), (6, 4)]))
def test_up_to_t_errors_are_corrected(seed, parameters):
    code = BCHCode(*parameters)
    rng = random.Random(seed)
    message = [rng.randrange(2) for _ in range(code.k)]
    word = list(code.encode(message))
    assert code.is_codeword(word) and not any(code.syndromes(word))
    flipped = rng.sample(range(code.n), rng.randrange(code.t + 1))
    for i in flipped:
        word[i] ^= 1
    decoded = code.decode(word)
    assert decoded.corrected and list(decoded.message) == message
    assert decoded.errors == tuple(sorted(flipped))


def test_berlekamp_massey_lengthens_without_resetting():
    # This pattern gives a nonzero discrepancy while 2L > step, the update that
    # keeps the previous polynomial; random draws reach it only sometimes.
    code = BCHCode(4, 3)
    word = list(code.encode([1, 0, 1, 1, 0]))
    for i in (0, 1, 12):
        word[i] ^= 1
    decoded = code.decode(word)
    assert decoded.corrected and decoded.errors == (0, 1, 12)
    assert decoded.message == (1, 0, 1, 1, 0)


def test_beyond_t_errors_are_detected_or_miscorrected():
    code = BCHCode(4, 2)
    word = list(code.encode([0] * 7))
    for i in (0, 1, 2):
        word[i] ^= 1
    decoded = code.decode(word)
    assert not code.is_codeword(word)
    # Three errors exceed t: the decoder either gives up or lands on another codeword.
    assert not decoded.corrected or decoded.message != (0,) * 7
    failed = [code.decode(_flip(code.encode([0] * 7), s)) for s in range(50)]
    assert any(not d.corrected for d in failed)


def _flip(word, seed):
    word = list(word)
    for i in random.Random(seed).sample(range(len(word)), 3):
        word[i] ^= 1
    return word


# Check digits -----------------------------------------------------------------


def test_published_check_digits():
    assert verhoeff_digit("236") == "3" and verhoeff_digit("12345") == "1"
    assert verhoeff_valid("2363") and not verhoeff_valid("2364")
    assert luhn_digit("7992739871") == "3" and luhn_valid("79927398713")
    assert not luhn_valid("79927398710")
    assert sum_digit("123") == "4" and sum_valid("1234")


def test_luhn_misses_only_09_and_90():
    assert luhn_digit("09") == luhn_digit("90")
    assert luhn_digit("18") != luhn_digit("81")
    assert verhoeff_digit("09") != verhoeff_digit("90")


def test_detection_rates():
    rates = {s: detection_rates(s, 3) for s in ("sum", "luhn", "verhoeff")}
    assert all(r.single_errors == 1.0 for r in rates.values())
    assert rates["sum"].transpositions == 0.0
    assert 0.95 < rates["luhn"].transpositions < 1.0
    assert rates["verhoeff"].transpositions == 1.0


def test_check_digit_validation():
    for bad in ("", "12a", "٣"):
        with pytest.raises(ValueError):
            verhoeff_digit(bad)
    with pytest.raises(TypeError):
        luhn_valid(123)
    with pytest.raises(ValueError, match="scheme"):
        detection_rates("isbn")
    with pytest.raises(ValueError, match="at most 4"):
        detection_rates("luhn", 5)


# Base58Check ------------------------------------------------------------------


def test_base58_vectors():
    assert base58_encode(b"hello world") == "StV1DL6CwTryKyV"
    assert base58_encode(b"\x00\x00\x01") == "112"
    assert base58_encode(b"") == "" and base58_decode("") == b""
    assert base58check_encode(0, bytes(20)) == "1111111111111111111114oLvT2"


def test_bitcoin_addresses_of_private_key_one():
    g = SECP256K1.generator
    assert p2pkh_address(g) == "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"
    assert p2pkh_address(g, compressed=False) == "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm"
    assert is_valid_address(p2pkh_address(g))


@given(st.binary(max_size=40))
def test_base58_round_trips(data):
    assert base58_decode(base58_encode(data)) == data
    assert base58check_decode(base58check_encode(7, data)) == (7, data)


def test_every_single_character_typo_is_caught():
    address = p2pkh_address(public_key(5))
    for i in range(len(address)):
        for c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz":
            if c != address[i]:
                assert not is_valid_address(address[:i] + c + address[i + 1 :])


def test_base58_rejects_bad_input():
    with pytest.raises(ValueError, match="base-58 digit"):
        base58_decode("0OIl")
    with pytest.raises(ValueError, match="too short"):
        base58check_decode("1")
    with pytest.raises(ValueError, match="checksum"):
        base58check_decode("1111111111111111111114oLvT3")
    with pytest.raises(ValueError, match="one byte"):
        base58check_encode(256, b"")
    for bad in (lambda: base58_encode("x"), lambda: base58_decode(b"x")):
        with pytest.raises(TypeError):
            bad()
    with pytest.raises(TypeError):
        base58check_encode(0, "x")
    assert not is_valid_address("not base58 0") and not is_valid_address(None)
    assert not is_valid_address(base58check_encode(9, bytes(20)))
    assert not is_valid_address(base58check_encode(0, bytes(19)))


# Bech32 and Bech32m -----------------------------------------------------------

BECH32_VALID = [
    "A12UEL5L",
    "a12uel5l",
    "an83characterlonghumanreadablepartthatcontainsthenumber1andtheexcludedcharactersbio1tt5tgs",
    "abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw",
    "split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w",
    "?1ezyfcl",
]
BECH32M_VALID = [
    "A1LQFN3A",
    "a1lqfn3a",
    "abcdef1l7aum6echk45nj3s0wdvt2fg8x9yrzpqzd3ryx",
    "?1v759aa",
]


@pytest.mark.parametrize("text", BECH32_VALID + BECH32M_VALID)
def test_bip173_and_bip350_checksums(text):
    decoded = bech32_decode(text)
    assert decoded.encoding == ("bech32" if text in BECH32_VALID else "bech32m")
    assert bech32_encode(decoded.hrp, decoded.data, decoded.encoding) == text.lower()


@pytest.mark.parametrize(
    "text",
    [
        "\x201nwldj5",  # A space in the human-readable part.
        "pzry9x0s0muk",  # No separator.
        "1pzry9x0s0muk",  # Empty human-readable part.
        "x1b4n0q5v",  # Invalid data character.
        "li1dgmt3",  # Too short a checksum.
        "A1G7SGD8",  # Checksum computed with an upper-case human-readable part.
        "aB1qqqqqqqq",  # Mixed case.
        "a" * 91,
    ],
)
def test_invalid_bech32_strings(text):
    with pytest.raises(ValueError):
        bech32_decode(text)


def test_segwit_vectors():
    program = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")
    address = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    assert segwit_encode("bc", 0, program) == address
    assert p2wpkh_address(SECP256K1.generator) == address
    assert segwit_decode("bc", address.upper()).program == program
    taproot = segwit_decode("bc", "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0")
    assert taproot.version == 1 and taproot.program == SECP256K1.generator[0].to_bytes(32, "big")


def test_segwit_rejects_mismatches():
    program = bytes(20)
    with pytest.raises(ValueError, match="not 'bc'"):
        segwit_decode("bc", segwit_encode("tb", 0, program))
    with pytest.raises(ValueError, match="must use bech32m"):
        segwit_decode("bc", bech32_encode("bc", [1, *convert_bits(program, 8, 5)]))
    with pytest.raises(ValueError, match="no witness version"):
        segwit_decode("bc", bech32_encode("bc", []))
    with pytest.raises(ValueError, match="20 or 32"):
        segwit_encode("bc", 0, bytes(21))
    with pytest.raises(ValueError, match="2 to 40"):
        segwit_encode("bc", 1, bytes(1))
    with pytest.raises(ValueError, match="0 to 16"):
        segwit_encode("bc", 17, program)


def test_bech32_encode_validation():
    with pytest.raises(ValueError, match="encoding"):
        bech32_encode("a", [], "base58")
    with pytest.raises(ValueError, match="1 to 83"):
        bech32_encode("", [])
    with pytest.raises(ValueError, match="lower-case"):
        bech32_encode("A", [])
    with pytest.raises(ValueError, match="5 bits"):
        bech32_encode("a", [32])
    with pytest.raises(ValueError, match="90"):
        bech32_encode("a", [0] * 83)
    with pytest.raises(TypeError):
        bech32_decode(b"a12uel5l")


def test_convert_bits_padding():
    assert convert_bits([255], 8, 5) == (31, 28)
    assert convert_bits([31, 28], 5, 8, pad=False) == (255,)
    with pytest.raises(ValueError, match="padding"):
        convert_bits([31, 29], 5, 8, pad=False)
    with pytest.raises(ValueError, match="padding"):
        convert_bits([0, 0, 0], 5, 8, pad=False)
    with pytest.raises(ValueError, match="8-bit"):
        convert_bits([256], 8, 5)


@given(st.integers(0, 2**31))
def test_any_single_substitution_is_detected(seed):
    rng = random.Random(seed)
    data = [rng.randrange(32) for _ in range(rng.randrange(1, 40))]
    text = bech32_encode("bc", data)
    i = rng.randrange(3, len(text))
    replacement = rng.choice([c for c in CHARSET if c != text[i]])
    with pytest.raises(ValueError):
        bech32_decode(text[:i] + replacement + text[i + 1 :])


def _ending_in_p(encoding):
    texts = (bech32_encode("bc", [n % 32, n // 32 % 32, 3, 1], encoding) for n in range(1_000))
    return next(text for text in texts if text.endswith("p"))


def test_bech32_insertion_flaw_and_its_fix():
    text = _ending_in_p("bech32")
    for inserted in ("q", "qq", "qqq"):
        assert bech32_decode(text[:-1] + inserted + "p").encoding == "bech32"
    fixed = _ending_in_p("bech32m")
    with pytest.raises(ValueError, match="checksum"):
        bech32_decode(fixed[:-1] + "qp")
    assert polymod([0]) == 32 and BECH32_CONSTANTS["bech32"] == 1
