"""Zero-knowledge simulation, deterministic nonces (RFC 6979), and MuSig."""

import pytest

import blockchainkit as bk

c = bk.crypto

# RFC 6979, appendix A.2.5: NIST P-256 with SHA-256.
P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
P256_KEY = 0xC9AFA9D845BA75166B5C215767B1D6934E50C3DB36E89B127B8A622B120F6721


@pytest.mark.parametrize(
    "message,expected",
    [
        (b"sample", 0xA6E3C57DD01ABE90086538398355DD4C3B17AA873382B0F24D6129493D8AAD60),
        (b"test", 0xD16B6AE827F17175E040871A1C7EC3500192C4C92677336EC2537ACAEE0008E0),
    ],
)
def test_deterministic_nonce_matches_rfc6979_vectors(message, expected):
    assert c.deterministic_nonce(P256_KEY, message, P256_ORDER) == expected


def test_deterministic_nonces_differ_per_message_and_never_leak_the_key():
    first = c.deterministic_nonce(42, b"pay Bob")
    second = c.deterministic_nonce(42, b"pay Carol")
    assert first != second and first == c.deterministic_nonce(42, b"pay Bob")
    sig1 = c.sign(b"pay Bob", 42, nonce=first)
    sig2 = c.sign(b"pay Carol", 42, nonce=second)
    assert sig1.commitment != sig2.commitment


def test_deterministic_nonce_works_on_a_tiny_order_and_validates():
    curve = c.TOY_CURVE
    assert 1 <= c.deterministic_nonce(5, b"m", curve.order) < curve.order
    with pytest.raises(ValueError):
        c.deterministic_nonce(curve.order, b"m", curve.order)
    with pytest.raises(TypeError):
        c.deterministic_nonce(5, "m", curve.order)


def test_simulated_transcripts_verify_without_the_private_key():
    public = c.public_key(42)
    commitment = c.simulate_transcript(public, 11, 123)
    assert c.verify_transcript(public, commitment, 11, 123)
    assert not c.verify_transcript(public, commitment, 12, 123)


def test_musig_aggregate_signature_verifies_as_a_plain_schnorr_signature():
    privates, nonces = (3, 5, 7), (11, 13, 17)
    publics = tuple(c.public_key(x) for x in privates)
    aggregate = c.aggregate_public_keys(publics)
    signature = c.musig_sign(b"spend", privates, nonces)
    assert c.verify(b"spend", signature, aggregate)
    assert not c.verify(
        b"spend",
        signature,
        c.add(publics[0], c.add(publics[1], publics[2], c.SECP256K1), c.SECP256K1),
    )


def test_musig_coefficients_defeat_the_rogue_key_attack():
    honest = c.public_key(3)
    rogue_secret = 99
    rogue = c.add(c.public_key(rogue_secret), (honest[0], -honest[1] % c.SECP256K1.p), c.SECP256K1)
    # Naive sum: honest + rogue = rogue_secret * G, which the attacker alone can sign for.
    assert c.add(honest, rogue, c.SECP256K1) == c.public_key(rogue_secret)
    assert c.aggregate_public_keys((honest, rogue)) != c.public_key(rogue_secret)
    coefficients = c.musig_coefficients((honest, rogue))
    assert len(set(coefficients)) == 2


def test_musig_validates_its_inputs():
    with pytest.raises(ValueError):
        c.aggregate_public_keys(())
    with pytest.raises(ValueError):
        c.musig_sign(b"m", (3, 5), (11,))


def test_simulation_rejects_out_of_range_or_degenerate_scalars():
    public = c.public_key(42)
    with pytest.raises(ValueError, match="below the curve order"):
        c.simulate_transcript(public, c.SECP256K1.order, 1)
    with pytest.raises(ValueError, match="infinity"):
        c.simulate_transcript(public, 2, 84)  # s = c * x gives R = O.


def test_musig_rejects_nonces_that_cancel():
    with pytest.raises(ValueError, match="infinity"):
        c.musig_sign(b"m", (3, 5), (11, c.SECP256K1.order - 11))
