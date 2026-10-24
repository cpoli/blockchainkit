"""Tests for the TumbleBit tumbler and the Tornado Cash-style mixer contract."""

import dataclasses
from random import Random

import pytest

from blockchainkit.contracts import World
from blockchainkit.privacy import (
    TUMBLER_KEY,
    Mixer,
    Tumbler,
    deposit_root,
    mixer_report,
    open_promise,
    prove_withdrawal,
    recipient_commitment,
    run_tumbler,
    tumbler_links,
)
from blockchainkit.proofs import Groth16Trapdoor, Note, note_commitment, owner_key, spend_setup


def test_tumbler_solves_puzzles_it_cannot_link():
    pairs = [("p1", "q1"), ("p2", "q2"), ("p3", "q3")]
    blinded = run_tumbler(pairs, seed=1)
    assert blinded.paid == (True, True, True) and tumbler_links(blinded) == ()
    plain = run_tumbler(pairs, blind=False, seed=1)
    assert plain.paid == (True, True, True) and tumbler_links(plain) == tuple(pairs)


def test_a_wrong_solution_does_not_open_the_promise():
    tumbler = Tumbler()
    promise = tumbler.promise("bob", b"pay bob", Random(0))
    solution = tumbler.solve("alice", promise.puzzle)
    assert pow(solution, TUMBLER_KEY.e, TUMBLER_KEY.n) == promise.puzzle
    assert open_promise(promise, solution) == b"pay bob"
    assert open_promise(promise, solution + 1) != b"pay bob"


@pytest.fixture(scope="module")
def proving_key():
    return spend_setup(2, Groth16Trapdoor(5, 6, 7, 8, 9))


def _mixer(proving_key, deposits=3):
    world = World()
    mixer = world.deploy("deployer", Mixer, 100, 2, proving_key.verifying_key)
    notes = []
    for i in range(deposits):
        world.fund(f"user{i}", 1_000)
        note = Note(owner_key(500 + i), 100, rho=i + 1, randomness=900 + i)
        notes.append(note)
        receipt = world.transact(f"user{i}", mixer, "deposit", note_commitment(note), value=100)
        assert receipt.success and receipt.result == i
    return world, mixer, notes


def test_mixer_pays_a_valid_withdrawal_once(proving_key):
    world, mixer, notes = _mixer(proving_key)
    deposits = world.view(mixer, "deposits")
    assert len(deposits) == 3 and world.balance(mixer) == 300
    withdrawal = prove_withdrawal(proving_key, deposits, 2, 501, notes[1], "fresh")
    assert withdrawal.root == deposit_root(deposits, 2)
    receipt = world.transact("relayer", mixer, "withdraw", withdrawal)
    assert receipt.success and world.balance("fresh") == 100
    assert [e.name for e in receipt.events] == ["Withdrawal"]
    again = world.transact("relayer", mixer, "withdraw", withdrawal)
    assert again.error == "the note was already withdrawn"


def test_mixer_rejects_redirected_and_forged_withdrawals(proving_key):
    world, mixer, notes = _mixer(proving_key)
    deposits = world.view(mixer, "deposits")
    withdrawal = prove_withdrawal(proving_key, deposits, 2, 500, notes[0], "fresh")
    stolen = dataclasses.replace(withdrawal, recipient="front-runner")
    assert world.transact("x", mixer, "withdraw", stolen).error == "invalid proof"
    unknown = dataclasses.replace(withdrawal, root=withdrawal.root + 1)
    assert world.transact("x", mixer, "withdraw", unknown).error == "unknown root"
    with pytest.raises(ValueError, match="never deposited"):
        prove_withdrawal(proving_key, deposits, 2, 500, Note(1, 100, 9, 9), "fresh")
    # A proof by someone who does not own the note fails inside the prover.
    with pytest.raises(ValueError):
        prove_withdrawal(proving_key, deposits, 2, 999, notes[0], "fresh")


def test_mixer_deposit_rules(proving_key):
    world, mixer, _ = _mixer(proving_key, deposits=4)
    world.fund("late", 1_000)
    assert world.transact("late", mixer, "deposit", 5, value=100).error == "the mixer is full"
    world2, mixer2, _ = _mixer(proving_key, deposits=0)
    world2.fund("cheap", 50)
    receipt = world2.transact("cheap", mixer2, "deposit", 5, value=50)
    assert receipt.error == "send exactly the denomination"


def test_mixer_payment_failure_reverts(proving_key):
    from blockchainkit.contracts import Contract

    class Refuser(Contract):
        def receive(self) -> None:
            self.require(False, "no thanks")

    world, mixer, notes = _mixer(proving_key)
    refuser = world.deploy("deployer", Refuser)
    withdrawal = prove_withdrawal(
        proving_key, world.view(mixer, "deposits"), 2, 500, notes[0], refuser
    )
    assert world.transact("x", mixer, "withdraw", withdrawal).error == "payment failed"


def test_recipient_commitments_and_roots():
    assert recipient_commitment("a") != recipient_commitment("b")
    assert deposit_root([], 2) == deposit_root([0, 0, 0, 0], 2)
    with pytest.raises(ValueError, match="more leaves"):
        deposit_root([1, 2, 3], 1)


def test_mixer_report_counts_anonymity_sets_and_address_reuse():
    report = mixer_report([("a", 1), ("b", 2), ("c", 3)], [("x", 4), ("b", 5), ("y", 5)])
    assert report.anonymity_sets == (3, 2, 2)
    assert report.address_links == ((1, 1),)
