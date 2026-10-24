"""Tests for ring signatures, linkable ring signatures and key images, and stealth addresses."""

import dataclasses

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blockchainkit.crypto import TEACHING_GROUP as G
from blockchainkit.crypto import pedersen_generators
from blockchainkit.privacy import (
    LinkableRingSignature,
    RingSignature,
    key_image,
    linked,
    lsag_sign,
    lsag_verify,
    mlsag_sign,
    mlsag_verify,
    one_time_secret,
    owns_output,
    ring_sign,
    ring_verify,
    stealth_keys,
    stealth_payment,
)

SECRETS = [11, 22, 33, 44, 55]
RING = [G.public(x) for x in SECRETS]


@settings(max_examples=20)
@given(st.integers(0, 4), st.binary(max_size=20), st.integers(0, 2**32))
def test_any_member_can_sign_for_the_ring(index, message, seed):
    signature = ring_sign(message, RING, index, SECRETS[index], seed=seed)
    assert ring_verify(message, RING, signature)
    assert not ring_verify(message + b"!", RING, signature)


def test_ring_signature_rejects_tampering_and_bad_input():
    signature = ring_sign(b"m", RING, 2, 33)
    assert not ring_verify(b"m", RING[::-1], signature)
    assert not ring_verify(b"m", RING, RingSignature(signature.challenge, signature.responses[:-1]))
    swapped = RingSignature(signature.challenge, (1, *signature.responses[1:]))
    assert not ring_verify(b"m", RING, swapped)
    assert ring_verify(b"m", RING[:1], ring_sign(b"m", RING[:1], 0, 11))
    with pytest.raises(ValueError, match="not the key"):
        ring_sign(b"m", RING, 2, 22)
    with pytest.raises(ValueError, match="not the key"):
        ring_sign(b"m", RING, 5, 22)
    with pytest.raises(ValueError, match="at least one member"):
        ring_sign(b"m", [], 0, 1)
    with pytest.raises(ValueError, match="key in the group"):
        ring_verify(b"m", [G.p - 1], signature)
    with pytest.raises(ValueError, match="key in the group"):
        ring_verify(b"m", [G.p + 1], signature)


def test_ring_signature_with_another_base():
    _, h = pedersen_generators()
    ring = [pow(h, x, G.p) for x in SECRETS]
    signature = ring_sign(b"m", ring, 1, 22, base=h)
    assert ring_verify(b"m", ring, signature, base=h)
    assert not ring_verify(b"m", ring, signature)


def test_key_images_link_signatures_by_the_same_key_across_rings():
    first = lsag_sign(b"spend 1", RING, 1, 22, seed=1)
    other_ring = [G.public(x) for x in (22, 66, 77)]
    second = lsag_sign(b"spend 2", other_ring, 0, 22, seed=2)
    third = lsag_sign(b"spend 3", RING, 3, 44)
    assert lsag_verify(b"spend 1", RING, first) and lsag_verify(b"spend 2", other_ring, second)
    assert linked(first, second) and not linked(first, third)
    assert first.key_image == key_image(22)


def test_lsag_rejects_a_forged_key_image():
    signature = lsag_sign(b"m", RING, 0, 11)
    forged = dataclasses.replace(signature, key_image=key_image(55))
    assert not lsag_verify(b"m", RING, forged)
    for image in (0, G.p, G.p - 1):
        assert not lsag_verify(b"m", RING, dataclasses.replace(signature, key_image=image))
    assert not lsag_verify(b"m", RING[:4], signature)
    short = LinkableRingSignature(signature.challenge, ((1, 2),) * 5, signature.key_image)
    assert not lsag_verify(b"m", RING, short)


def test_mlsag_signs_two_columns_with_different_bases():
    _, h = pedersen_generators()
    second = [7, 8, 9]
    ring = [[G.public(x), pow(h, z, G.p)] for x, z in zip((11, 22, 33), second, strict=True)]
    signature = mlsag_sign(b"m", ring, 2, [33, 9], bases=[G.g, h])
    assert mlsag_verify(b"m", ring, signature, bases=[G.g, h])
    assert not mlsag_verify(b"m", ring, signature)
    with pytest.raises(ValueError, match="one base per column"):
        mlsag_verify(b"m", ring, signature, bases=[G.g])
    with pytest.raises(ValueError, match="not the key"):
        mlsag_sign(b"m", ring, 2, [33, 8], bases=[G.g, h])
    with pytest.raises(ValueError, match="one secret per column"):
        mlsag_sign(b"m", ring, 2, [33], bases=[G.g, h])
    with pytest.raises(ValueError, match="same number of keys"):
        mlsag_sign(b"m", [[RING[0]], RING[1:3]], 0, [11])
    with pytest.raises(ValueError, match="at least one member"):
        mlsag_sign(b"m", [], 0, [11])


def test_stealth_payments_are_found_and_spent_only_by_the_payee():
    bob, eve = stealth_keys(5, 7), stealth_keys(6, 8)
    outputs = [
        stealth_payment(bob.view_public, bob.spend_public, r, index=i)
        for i, r in enumerate((1234, 5678))
    ]
    assert outputs[0].one_time_key != outputs[1].one_time_key != bob.spend_public
    for i, output in enumerate(outputs):
        assert owns_output(output, bob.view_secret, bob.spend_public, index=i)
        assert not owns_output(output, eve.view_secret, eve.spend_public, index=i)
        x = one_time_secret(output, bob.view_secret, bob.spend_secret, index=i)
        assert G.public(x) == output.one_time_key
    assert not owns_output(outputs[1], bob.view_secret, bob.spend_public, index=0)
    with pytest.raises(ValueError, match="does not pay this wallet"):
        one_time_secret(outputs[0], eve.view_secret, eve.spend_secret)
