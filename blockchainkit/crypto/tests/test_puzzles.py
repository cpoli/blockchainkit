"""Merkle's puzzles: quadratic advantage from symmetric primitives alone."""

from random import Random

import pytest

import blockchainkit as bk

c = bk.crypto


def _puzzles(count=16, bits=8, seed=3):
    return c.merkle_puzzles(count, bits, randbits=Random(seed).getrandbits)


def test_bob_solves_one_puzzle_and_shares_its_key_with_alice():
    puzzles, table = _puzzles()
    solution = c.solve_puzzle(puzzles[5], bits=8)
    assert table[solution.puzzle_id] == solution.key
    assert 1 <= solution.trials <= 2**8


def test_an_eavesdropper_must_solve_puzzles_until_the_announced_id_appears():
    puzzles, _ = _puzzles(count=32)
    bob = c.solve_puzzle(puzzles[20], bits=8)
    eve_trials, solved = 0, 0
    for puzzle in puzzles:
        found = c.solve_puzzle(puzzle, bits=8)
        eve_trials, solved = eve_trials + found.trials, solved + 1
        if found.puzzle_id == bob.puzzle_id:
            break
    assert solved == 21
    assert eve_trials > 5 * 2**8 >= 5 * bob.trials  # Eve's work grows with the puzzle count.


def test_puzzles_are_reproducible_and_validated():
    assert _puzzles()[0] == _puzzles()[0]
    with pytest.raises(ValueError, match="bits"):
        c.merkle_puzzles(4, 30)
    with pytest.raises(ValueError, match="no weak key"):
        c.solve_puzzle(bytes(32), bits=4)
    with pytest.raises(ValueError, match="32 bytes"):
        c.solve_puzzle(b"short", bits=4)


def test_solving_rejects_oversized_weak_keys():
    with pytest.raises(ValueError, match="bits"):
        c.solve_puzzle(bytes(32), bits=25)
