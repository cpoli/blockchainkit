"""Baby-step giant-step and Pohlig-Hellman discrete logarithms."""

from math import isqrt

import pytest

import blockchainkit as bk

c = bk.crypto
SMOOTH_P = 8101  # p - 1 = 8100 = 2^2 * 3^4 * 5^2
SMOOTH_G = 6  # A primitive root modulo 8101.


def test_primitive_root_fixture():
    assert all(pow(SMOOTH_G, 8100 // f, SMOOTH_P) != 1 for f in (2, 3, 5))


@pytest.mark.parametrize("exponent", [0, 1, 2, 4049, 8099])
def test_baby_step_giant_step_recovers_the_exponent(exponent):
    target = pow(SMOOTH_G, exponent, SMOOTH_P)
    result = c.baby_step_giant_step(SMOOTH_G, target, SMOOTH_P, 8100)
    assert result.exponent == exponent
    assert result.group_operations <= 2 * (isqrt(8100) + 1)


@pytest.mark.parametrize("exponent", [0, 1, 777, 8099])
def test_pohlig_hellman_matches_and_is_cheaper_on_a_smooth_order(exponent):
    target = pow(SMOOTH_G, exponent, SMOOTH_P)
    result = c.pohlig_hellman(SMOOTH_G, target, SMOOTH_P, 8100)
    assert result.exponent == exponent
    bsgs = c.baby_step_giant_step(SMOOTH_G, target, SMOOTH_P, 8100)
    assert result.group_operations < bsgs.group_operations / 3


def test_pohlig_hellman_gains_nothing_in_a_prime_order_subgroup():
    # With q = 509 prime, Pohlig-Hellman has a single subproblem: baby-step
    # giant-step on the whole group, so it saves no work.
    small = c.DHGroup(1019, 509, 4)
    target = pow(small.g, 300, small.p)
    ph = c.pohlig_hellman(small.g, target, small.p, small.q)
    bsgs = c.baby_step_giant_step(small.g, target, small.p, small.q)
    assert ph.exponent == bsgs.exponent == 300
    assert ph.group_operations >= bsgs.group_operations


def test_discrete_log_rejects_targets_outside_the_subgroup():
    # 4 generates the quadratic residues modulo 23; 5 is a non-residue.
    for solver in (c.baby_step_giant_step, c.pohlig_hellman):
        with pytest.raises(ValueError, match="not a power"):
            solver(4, 5, 23, 11)


def test_order_factorization_by_trial_division():
    from blockchainkit.crypto.systems.discrete_log import factor_order

    assert factor_order(8100) == {2: 2, 3: 4, 5: 2}
    assert factor_order(2**61 - 1) == {2**61 - 1: 1}  # Prime cofactor left after trial division.
    with pytest.raises(ValueError, match="factor"):
        factor_order((2**31 - 1) * 2147483629)  # Two primes above the trial-division bound.


@pytest.mark.parametrize("args", [(True, 1, 23, 11), (4, 1, 23, 0), (4, 23, 23, 11)])
def test_discrete_log_validates_arguments(args):
    with pytest.raises((TypeError, ValueError)):
        c.baby_step_giant_step(*args)


def test_a_multiple_of_the_order_is_accepted():
    # Regression: 4 has order 11 modulo 23; passing order 22 must still work.
    for solver in (c.baby_step_giant_step, c.pohlig_hellman):
        assert solver(4, pow(4, 7, 23), 23, 22).exponent == 7


def test_discrete_log_requires_base_to_have_the_stated_order():
    with pytest.raises(ValueError, match="base\\*\\*order"):
        c.baby_step_giant_step(5, 1, 23, 11)  # 5 has order 22.
