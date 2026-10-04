"""Boundary cases and rejection of malformed inputs in blockchainkit.consensus."""

import pytest

import blockchainkit as bk


def test_stake_lottery_ticket_boundaries(monkeypatch):
    sampler = bk.consensus.StakeSampler({"a": 0, "b": 2, "c": 0, "d": 3, "e": 0})
    # Enumerate every possible ticket to check exact weighting and zero stakes.
    tickets = iter(range(5))
    monkeypatch.setattr(sampler._random, "randrange", lambda total: next(tickets))
    assert sampler.sample(5) == ("b", "b", "d", "d", "d")
    assert sampler.sample(0) == ()
    with pytest.raises(ValueError, match="rounds"):
        sampler.sample(-1)
