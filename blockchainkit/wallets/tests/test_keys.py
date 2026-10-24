"""Key stretching, brain wallets, HD keys, mnemonics, derivation paths, and the utilities."""

import hashlib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blockchainkit.crypto import SECP256K1, public_key
from blockchainkit.wallets import (
    PHRASEBOOK,
    WORDLIST,
    base58check_encode,
    bip44_path,
    block_mix,
    brain_wallet_address,
    brain_wallet_key,
    crack_brain_wallet,
    crack_pin,
    derive_path,
    derive_private,
    derive_public,
    discover_accounts,
    entropy_to_mnemonic,
    fingerprint,
    format_path,
    is_valid_mnemonic,
    master_key,
    mnemonic_to_entropy,
    mnemonic_to_seed,
    neuter,
    p2pkh_address,
    parse_extended_key,
    parse_path,
    pbkdf2,
    recover_parent_private,
    romix,
    salsa20_8,
    scrypt,
    serialize_extended_key,
    simulate_brain_drain,
)
from blockchainkit.wallets.utils import compress, decompress, hash160, ripemd160

# RIPEMD-160 and compressed keys -----------------------------------------------


@pytest.mark.parametrize(
    ("data", "digest"),
    [
        (b"", "9c1185a5c5e9fc54612808977ee8f548b2258d31"),
        (b"abc", "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc"),
        (b"message digest", "5d0689ef49d2fae572b881b123a85ffa21595f36"),
        (b"a" * 1_000_000, "52783243c1697bdbe16d37f97f68f08325dc1528"),
    ],
)
def test_ripemd160_vectors(data, digest):
    # Dobbertin, Bosselaers and Preneel's published test values.
    assert ripemd160(data).hex() == digest


@given(st.binary(max_size=200))
def test_hash160_is_ripemd160_of_sha256(data):
    assert hash160(data) == ripemd160(hashlib.sha256(data).digest())


def test_ripemd160_rejects_text():
    with pytest.raises(TypeError):
        ripemd160("abc")


@given(st.integers(1, SECP256K1.order - 1))
@settings(max_examples=20)
def test_compression_round_trips(private):
    point = public_key(private)
    assert decompress(compress(point)) == point


def test_decompress_rejects_bad_encodings():
    with pytest.raises(TypeError):
        decompress("02")
    for bad in (b"\x04" + bytes(32), b"\x02" + bytes(31), b"\x02" + b"\xff" * 32):
        with pytest.raises(ValueError):
            decompress(bad)
    with pytest.raises(ValueError, match="no point"):
        decompress(b"\x02" + (5).to_bytes(32, "big"))  # 5**3 + 7 is not a square mod p.
    with pytest.raises(ValueError):
        compress(None)


# PBKDF2 and scrypt ------------------------------------------------------------


def test_pbkdf2_rfc6070_vectors():
    assert pbkdf2(b"password", b"salt", 2, 20, "sha1").hex() == (
        "ea6c014dc72d6f8ccd1ed92ace1d41f0d8de8957"
    )
    assert pbkdf2(b"password", b"salt", 4096, 20, "sha1").hex() == (
        "4b007901b765489abead49d926f721d065a429c1"
    )


@given(
    st.binary(max_size=20),
    st.binary(max_size=20),
    st.integers(1, 20),
    st.integers(1, 130),
    st.sampled_from(["sha1", "sha256", "sha512"]),
)
def test_pbkdf2_matches_hashlib(password, salt, iterations, length, name):
    expected = hashlib.pbkdf2_hmac(name, password, salt, iterations, length)
    assert pbkdf2(password, salt, iterations, length, name) == expected


def test_pbkdf2_validation():
    with pytest.raises(TypeError):
        pbkdf2("pw", b"s", 1, 1)
    with pytest.raises(ValueError, match="hash_name"):
        pbkdf2(b"pw", b"s", 1, 1, "md5")
    with pytest.raises(ValueError):
        pbkdf2(b"pw", b"s", 0, 1)


def test_cracking_a_pin_costs_guesses_times_iterations():
    key = pbkdf2(b"17", b"salt", 5, 40)  # Two SHA-256 blocks.
    assert crack_pin(key, b"salt", 5, 2) == crack_pin(key, b"salt", 5, 2)
    result = crack_pin(key, b"salt", 5, 2)
    assert (result.secret, result.guesses, result.hash_calls) == ("17", 18, 18 * 5 * 2)
    missed = crack_pin(key, b"pepper", 5, 1)
    assert missed.secret is None and missed.hash_calls == 10 * 5 * 2
    for kwargs in ({"digits": 7}, {"digits": 2, "hash_name": "md5"}):
        with pytest.raises(ValueError):
            crack_pin(key, b"salt", 5, **kwargs)
    with pytest.raises(ValueError, match="non-empty"):
        crack_pin(b"", b"salt", 5, 2)


def test_scrypt_rfc7914_vectors():
    assert scrypt(b"", b"", 16, 1, 1, 64).hex() == (
        "77d6576238657b203b19ca42c18a0497f16b4844e3074ae8dfdffa3fede21442"
        "fcd0069ded0948f8326a753a0fc81f17e8d3e0fb2e0d3628cf35e20c38d18906"
    )


@given(st.binary(max_size=10), st.integers(1, 4), st.integers(1, 2), st.integers(1, 3))
@settings(max_examples=10, deadline=None)
def test_scrypt_matches_hashlib(password, log_n, r, p):
    expected = hashlib.scrypt(password, salt=b"salt", n=2**log_n, r=r, p=p, dklen=32)
    assert scrypt(password, b"salt", 2**log_n, r, p, 32) == expected


def test_salsa20_8_rfc7914_vector():
    block = bytes.fromhex(
        "7e879a214f3ec9867ca940e641718f26baee555b8c61c1b50df846116dcd3b1d"
        "ee24f319df9b3d8514121e4b5ac5aa3276021d2909c74829edebc68db8b8c25e"
    )
    assert salsa20_8(block).hex() == (
        "a41f859c6608cc993b81cacb020cef05044b2181a2fd337dfd7b1c6396682f29"
        "b4393168e3c9e6bcfe6bc5b7a06d96bae424cc102c91745c24ad673dc7618f81"
    )


def test_forgetting_table_entries_costs_time_not_correctness():
    block = bytes(range(128))
    full, cost = romix(block, 64)
    assert (cost.stored, cost.block_mixes, cost.memory) == (64, 128, 64 * 128)
    previous = cost
    for k in (2, 4, 8, 16, 64):
        out, frugal = romix(block, 64, keep_every=k)
        assert out == full and frugal.stored == 64 // k
        assert frugal.block_mixes > previous.block_mixes
        previous = frugal


def test_scrypt_validation():
    for bad in (b"\x00" * 63, "x" * 64):
        with pytest.raises(ValueError):
            salsa20_8(bad)
    with pytest.raises(ValueError, match="128"):
        block_mix(bytes(64))
    with pytest.raises(ValueError, match="power of two"):
        romix(bytes(128), 6)
    with pytest.raises(ValueError, match="at most n"):
        romix(bytes(128), 4, keep_every=5)
    with pytest.raises(ValueError):
        scrypt(b"", b"", 16, 0, 1, 16)


# Brain wallets ----------------------------------------------------------------


def test_brain_wallet_of_password():
    assert brain_wallet_key("password") == int(hashlib.sha256(b"password").hexdigest(), 16)
    assert brain_wallet_address("password") == "16ga2uqnF1NqpAuQeeg7sTCAdtDUwDyJav"
    assert crack_brain_wallet(brain_wallet_address("satoshi"), PHRASEBOOK) == "satoshi"
    assert crack_brain_wallet(brain_wallet_address("a long random phrase"), PHRASEBOOK) is None
    with pytest.raises(TypeError):
        brain_wallet_key(b"password")


def test_brain_drain_simulation():
    drain = simulate_brain_drain(40, seed=3)
    assert drain.wallets == 40 and drain.drained <= drain.weak <= 40
    assert sum(drain.hauls) == drain.drained == len(drain.delays)
    assert all(d >= 1 for d in drain.delays)
    assert simulate_brain_drain(40, seed=3) == drain
    safe = simulate_brain_drain(10, weak_share=0.0, seed=1)
    assert safe.weak == safe.drained == 0
    total = simulate_brain_drain(10, weak_share=1.0, thieves=[(1.0, 1.0)], seed=2)
    assert total.drained == total.weak == 10 and total.hauls == (10,)


def test_brain_drain_validation():
    with pytest.raises(ValueError, match="positive"):
        simulate_brain_drain(5, thieves=[(0.5, 0.0)])
    with pytest.raises(ValueError):
        simulate_brain_drain(5, thieves=[(1.5, 1.0)])
    with pytest.raises(TypeError):
        simulate_brain_drain(5, seed="0")


# BIP32 ------------------------------------------------------------------------

VECTOR_1 = [
    (
        "m",
        "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8",
        "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi",
    ),
    (
        "m/0'",
        "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw",
        "xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7",
    ),
    (
        "m/0'/1",
        "xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ",
        "xprv9wTYmMFdV23N2TdNG573QoEsfRrWKQgWeibmLntzniatZvR9BmLnvSxqu53Kw1UmYPxLgboyZQaXwTCg8MSY3H2EU4pWcQDnRnrVA1xe8fs",
    ),
]


@pytest.mark.parametrize(("path", "xpub", "xprv"), VECTOR_1)
def test_bip32_test_vector_1(path, xpub, xprv):
    key = derive_path(master_key(bytes(range(16))), path)
    assert serialize_extended_key(key) == xprv
    assert serialize_extended_key(neuter(key)) == xpub
    assert parse_extended_key(xprv) == key and parse_extended_key(xpub) == neuter(key)


def test_public_derivation_matches_private_for_normal_children():
    master = master_key(bytes(range(16)))
    for index in (0, 1, 2**31 - 1):
        private_child = derive_private(master, index)
        public_child = derive_public(neuter(master), index)
        assert public_child.public == private_child.public
        assert public_child.chain_code == private_child.chain_code
        assert public_child.parent_fingerprint == fingerprint(master)
    assert derive_path(neuter(master), "m/5/6").public == derive_path(master, "m/5/6").public


def test_leaked_xpub_and_child_key_reveal_the_parent():
    account = derive_path(master_key(bytes(range(32))), "m/44'/0'/0'")
    child = derive_private(account, 3)
    assert recover_parent_private(neuter(account), child.private, 3) == account.private
    hardened = derive_private(account, 2**31 + 3)
    with pytest.raises(ValueError, match="hardened"):
        recover_parent_private(neuter(account), hardened.private, 2**31 + 3)


def test_extended_key_properties_and_validation():
    master = master_key(bytes(range(16)))
    assert master.is_private and not neuter(master).is_private
    assert derive_private(master, 2**31).hardened and not derive_private(master, 1).hardened
    with pytest.raises(ValueError, match="16 to 64"):
        master_key(bytes(15))
    with pytest.raises(ValueError, match="private key"):
        derive_private(neuter(master), 0)
    with pytest.raises(ValueError, match="32-bit"):
        derive_private(master, 2**32)
    with pytest.raises(ValueError, match="hardened"):
        derive_public(master, 2**31)
    with pytest.raises(ValueError, match="hardened"):
        derive_path(neuter(master), "m/0'")


def test_parse_extended_key_rejects_bad_strings():
    xprv = VECTOR_1[0][2]
    with pytest.raises(ValueError, match="checksum"):
        parse_extended_key(xprv[:-1] + ("j" if xprv[-1] != "j" else "k"))
    with pytest.raises(ValueError, match="78 bytes"):
        parse_extended_key(base58check_encode(4, bytes(10)))
    with pytest.raises(ValueError, match="version"):
        parse_extended_key(base58check_encode(1, bytes(77)))
    # A private-key version with a key byte other than 0x00.
    body = bytes.fromhex("88ade4") + bytes(41) + b"\x01" + (1).to_bytes(32, "big")
    with pytest.raises(ValueError, match="private key"):
        parse_extended_key(base58check_encode(4, body))
    zero = bytes.fromhex("88ade4") + bytes(42) + bytes(32)
    with pytest.raises(ValueError, match="private key"):
        parse_extended_key(base58check_encode(4, zero))


# BIP39 ------------------------------------------------------------------------


def test_word_list_is_sorted_and_unique():
    assert len(WORDLIST) == len(set(WORDLIST)) == 2048
    assert list(WORDLIST) == sorted(WORDLIST) and all(len(w) == 4 for w in WORDLIST)


def test_bip39_seed_vectors():
    phrase = " ".join(["abandon"] * 11 + ["about"])
    assert mnemonic_to_seed(phrase, "TREZOR").hex() == (
        "c55257c360c07c72029aebc1b53c05ed0362ada38ead3e3e9efa3708e53495531f09a6987599d18264c1e1c92f2cf141630c7a3c4ab7c81b2f001698e7463b04"
    )
    assert mnemonic_to_seed(phrase) != mnemonic_to_seed(phrase, "TREZOR")
    # NFKD: a composed and a decomposed accent give the same seed.
    assert mnemonic_to_seed(phrase, "café") == mnemonic_to_seed(phrase, "café")
    with pytest.raises(TypeError):
        mnemonic_to_seed(phrase.encode())


@given(st.sampled_from([16, 20, 24, 28, 32]), st.data())
def test_mnemonics_round_trip(length, data):
    entropy = data.draw(st.binary(min_size=length, max_size=length))
    phrase = entropy_to_mnemonic(entropy)
    assert len(phrase.split()) == length * 3 // 4
    assert mnemonic_to_entropy(phrase) == entropy and is_valid_mnemonic(phrase)


def test_a_miscopied_word_is_caught_15_times_in_16():
    phrase = entropy_to_mnemonic(bytes(range(16))).split()
    caught = 0
    for word in WORDLIST:
        caught += not is_valid_mnemonic(" ".join([*phrase[:5], word, *phrase[6:]]))
    # Each other word is a different 11-bit value; the 4 checksum bits catch all but 1/16.
    assert 2047 * 0.9 < caught < 2047


def test_mnemonic_validation():
    with pytest.raises(ValueError, match="16, 20"):
        entropy_to_mnemonic(bytes(17))
    with pytest.raises(ValueError, match="12, 15"):
        mnemonic_to_entropy("bada " * 11)
    with pytest.raises(ValueError, match="not in the word list"):
        mnemonic_to_entropy("abandon " * 12)
    with pytest.raises(TypeError):
        mnemonic_to_entropy(None)
    assert not is_valid_mnemonic("bada " * 12)
    assert not is_valid_mnemonic(None)


# BIP44 ------------------------------------------------------------------------


def test_paths_parse_and_format():
    assert parse_path("m") == ()
    assert parse_path("m/44h/0'/1") == (2**31 + 44, 2**31, 1)
    assert format_path(parse_path("m/44'/60'/0'/0/7")) == "m/44'/60'/0'/0/7"
    assert bip44_path(0, 1, 1, 9) == "m/44'/0'/1'/1/9"
    for bad in ("44'/0'", "m/x", "m/-1", "m/2147483648", "m/"):
        with pytest.raises(ValueError):
            parse_path(bad)
    with pytest.raises(TypeError):
        parse_path(None)
    with pytest.raises(ValueError, match="32-bit"):
        format_path([2**32])
    with pytest.raises(ValueError, match="change"):
        bip44_path(0, 0, 2, 0)


def _address(master, account, index):
    return p2pkh_address(derive_path(master, bip44_path(0, account, 0, index)).public)


def test_account_discovery_and_the_gap_limit():
    master = master_key(bytes(range(16)))
    used = {_address(master, 0, i) for i in (0, 2)} | {_address(master, 1, 0)}
    scan = discover_accounts(master, used, gap_limit=3)
    assert scan.accounts == 2
    assert scan.found == ("m/44'/0'/0'/0/0", "m/44'/0'/0'/0/2", "m/44'/0'/1'/0/0")
    assert scan.derived == 6 + 4 + 3
    hidden = used | {_address(master, 0, 7)}  # Four unused addresses before it: past the gap.
    assert discover_accounts(master, hidden, gap_limit=3).found == scan.found
    assert "m/44'/0'/0'/0/7" in discover_accounts(master, hidden, gap_limit=5).found
    assert discover_accounts(master, set(), gap_limit=2).accounts == 0
    capped = discover_accounts(master, used, gap_limit=2, max_accounts=1)
    assert capped.accounts == 1


def test_invalid_bip32_keys_are_refused(monkeypatch):
    # Each case has probability below 2**-127; force it by replacing the HMAC.
    from blockchainkit.wallets.systems import hd

    master = master_key(bytes(range(16)))
    n = SECP256K1.order
    monkeypatch.setattr(hd, "_hmac512", lambda key, data: (n, bytes(32)))
    with pytest.raises(ValueError, match="invalid master key"):
        master_key(bytes(16))
    with pytest.raises(ValueError, match="invalid child"):
        derive_private(master, 0)
    with pytest.raises(ValueError, match="invalid child"):
        derive_public(master, 0)
    monkeypatch.setattr(hd, "_hmac512", lambda key, data: (n - master.private, bytes(32)))
    with pytest.raises(ValueError, match="invalid child"):
        derive_private(master, 0)  # The child key would be 0.
    with pytest.raises(ValueError, match="invalid child"):
        derive_public(master, 0)  # The child point would be at infinity.


def test_a_passphrase_hashing_to_zero_is_refused(monkeypatch):
    from blockchainkit.wallets.systems import brainwallets

    monkeypatch.setattr(brainwallets, "sha256", lambda data: bytes(32))
    with pytest.raises(ValueError, match="key range"):
        brain_wallet_key("anything")
