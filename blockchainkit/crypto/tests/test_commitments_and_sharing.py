"""Pedersen commitments, Feldman verifiable secret sharing, and the teaching group."""

from itertools import combinations
from random import Random

import pytest

import blockchainkit as bk

c = bk.crypto
G = c.TEACHING_GROUP


def test_teaching_group_is_a_62_bit_safe_prime_subgroup():
    assert G.p == 2 * G.q + 1 and G.p.bit_length() == 62
    assert pow(G.g, G.q, G.p) == 1 and G.g != 1


def test_pedersen_generators_are_independent_subgroup_elements():
    g, h = c.pedersen_generators(G)
    assert g == G.g and h not in (0, 1, g)
    assert pow(h, G.q, G.p) == 1
    assert c.pedersen_generators(G) == (g, h)


def test_pedersen_commitments_are_additively_homomorphic():
    a = c.pedersen_commit(10, 111, G)
    b = c.pedersen_commit(32, 222, G)
    assert a * b % G.p == c.pedersen_commit(42, 333, G)
    assert c.pedersen_commit(G.q - 1, 1, G) * c.pedersen_commit(1, 1, G) % G.p == c.pedersen_commit(
        0, 2, G
    )


def test_pedersen_blinding_hides_the_value():
    # In a tiny group, every value has some blinding that gives the same commitment.
    small = c.DHGroup(1019, 509, 4)
    target = c.pedersen_commit(7, 100, small)
    assert any(c.pedersen_commit(8, r, small) == target for r in range(small.q))


@pytest.mark.parametrize("args", [(G.q, 1), (1, G.q), (-1, 1), (True, 1)])
def test_pedersen_validates_field_elements(args):
    with pytest.raises((TypeError, ValueError)):
        c.pedersen_commit(*args, G)


def test_feldman_shares_verify_and_reconstruct():
    dealt = c.feldman_split(123456789, 3, 5, G, randbelow=Random(1).randrange)
    assert len(dealt.commitments) == 3
    assert dealt.commitments[0] == pow(G.g, 123456789, G.p)
    assert all(c.feldman_verify(share, dealt.commitments, G) for share in dealt.shares)
    for subset in combinations(dealt.shares, 3):
        assert c.recover_secret(subset, prime=G.q) == 123456789


def test_feldman_detects_a_corrupted_share():
    dealt = c.feldman_split(5, 2, 3, G, randbelow=Random(2).randrange)
    x, y = dealt.shares[1]
    assert not c.feldman_verify((x, (y + 1) % G.q), dealt.commitments, G)
    assert not c.feldman_verify((0, y), dealt.commitments, G)
    assert not c.feldman_verify((x, G.q), dealt.commitments, G)


def test_feldman_validates_parameters():
    with pytest.raises(ValueError):
        c.feldman_split(G.q, 2, 3, G)
    with pytest.raises(ValueError):
        c.feldman_split(1, 4, 3, G)


def test_pedersen_rehashes_a_degenerate_second_generator():
    # Find a tiny group whose first hash-derived candidate lands on 1 or g, so
    # the derivation must retry; the result must still be a valid generator.
    from blockchainkit.constants import PEDERSEN_DOMAIN

    def first_candidate(group):
        seed = PEDERSEN_DOMAIN + f"{group.p}:{group.q}:{group.g}:0".encode()
        value = int.from_bytes(c.sha256(seed), "big") % group.p
        return pow(value, (group.p - 1) // group.q, group.p)

    groups = [c.DHGroup(p, (p - 1) // 2, 4) for p in (23, 47, 59, 83, 107, 167, 179, 227, 263)]
    degenerate = next(g for g in groups if first_candidate(g) in (0, 1, g.g))
    _, h = c.pedersen_generators(degenerate)
    assert h not in (0, 1, degenerate.g) and pow(h, degenerate.q, degenerate.p) == 1


def test_shamir_requires_a_prime_modulus():
    with pytest.raises(ValueError, match="prime"):
        c.split_secret(1, 2, 3, prime=15)
