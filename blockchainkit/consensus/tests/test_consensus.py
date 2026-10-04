"""Target arithmetic, bounded mining, and sampling statistics."""

from collections import Counter
from dataclasses import replace

import pytest

import blockchainkit as bk


def test_mining_and_target_boundaries():
    assert bk.consensus.target(0) == 2**256 - 1
    assert bk.consensus.target(256) == 0
    assert bk.consensus.expected_trials(8) == 256
    block = bk.structures.Block(difficulty=4)
    result = bk.consensus.mine(block)
    assert result.attempts == result.block.nonce + 1
    assert bk.consensus.valid_pow(result.block)
    assert block.nonce == 0
    for nonce in range(result.block.nonce):
        assert not bk.consensus.valid_pow(replace(block, nonce=nonce))
    with pytest.raises(TimeoutError):
        bk.consensus.mine(bk.structures.Block(difficulty=256), max_attempts=2)
    with pytest.raises(ValueError):
        bk.consensus.mine(replace(block, nonce=2**64 - 1), max_attempts=2)
    with pytest.raises(ValueError):
        bk.consensus.mine(block, max_attempts=0)
    for difficulty in (-1, 257):
        with pytest.raises(ValueError):
            bk.consensus.target(difficulty)
    with pytest.raises(TypeError):
        bk.consensus.target(True)


def test_catch_up_model():
    assert bk.consensus.eventual_catch_up(0, 3) == 0
    assert bk.consensus.eventual_catch_up(0, 0) == 1
    assert bk.consensus.eventual_catch_up(0.5, 100) == 1
    assert bk.consensus.eventual_catch_up(1, 100) == 1
    assert bk.consensus.eventual_catch_up(0.25, 2) == pytest.approx(1 / 9)
    for fraction in (-0.1, 1.1, float("nan")):
        with pytest.raises(ValueError):
            bk.consensus.eventual_catch_up(fraction, 2)


def test_stake_sampling_reproducibility_and_statistics():
    a = bk.consensus.StakeSampler({"a": 1, "b": 3, "c": 0}, seed=12)
    b = bk.consensus.StakeSampler({"c": 0, "b": 3, "a": 1}, seed=12)
    rounds = a.sample(20_000)
    assert rounds == b.sample(20_000)
    counts = Counter(rounds)
    assert abs(counts["a"] / len(rounds) - 0.25) < 0.02
    assert counts["c"] == 0
    # Integer sampling works even when weights exceed floating-point precision.
    assert bk.consensus.StakeSampler({"a": 10**100}, seed=1).choose() == "a"
    for stakes in ({}, {"a": 0}, {"a": -1}, {"": 1}):
        with pytest.raises(ValueError):
            bk.consensus.StakeSampler(stakes)
    for stakes in ({"a": 0.5}, {"a": True}):
        with pytest.raises(TypeError):
            bk.consensus.StakeSampler(stakes)
