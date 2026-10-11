"""Plasma exit games, sharding and Atomix, and zk and optimistic rollups."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.channels import (
    CoinTransfer,
    InclusionProof,
    OptimisticRollup,
    PlasmaChain,
    Transfer,
    ZKRollup,
    apply_transfer,
    assign_shards,
    atomix_transfer,
    batch_digest,
    batch_gas,
    bisect,
    compromised_epochs,
    execute_batch,
    shard_failure_probability,
    sign_transfer,
    state_root,
)
from blockchainkit.crypto import public_key

ALICE, BOB, CAROL, DAVE = 7, 5, 11, 13

# Plasma -----------------------------------------------------------------------


def plasma():
    chain = PlasmaChain(period=7, depth=8)
    deposit = chain.deposit(public_key(ALICE))  # Block 1.
    to_bob = chain.submit_block([sign_transfer(ALICE, 0, public_key(BOB), 1)])  # Block 2.
    to_carol = chain.submit_block([sign_transfer(BOB, 0, public_key(CAROL), to_bob)])  # Block 3.
    return chain, deposit, to_bob, to_carol


def test_a_spent_coins_exit_is_challenged():
    chain, deposit, to_bob, to_carol = plasma()
    stale = chain.start_exit(chain.prove(0, to_bob), deposit, height=10)
    assert not chain.challenge(stale, chain.prove(0, to_bob), height=11)  # Not a spend.
    assert chain.challenge(stale, chain.prove(0, to_carol), height=12)
    assert chain.exits[stale].status == "challenged"
    with pytest.raises(ValueError, match="challenged"):
        chain.finalize(stale, height=20)


def test_a_double_spend_is_challenged_and_the_true_owner_exits():
    chain, deposit, to_bob, to_carol = plasma()
    # Alice signs the coin away a second time, and a colluding operator includes it.
    to_dave = chain.submit_block([sign_transfer(ALICE, 0, public_key(DAVE), 1)])  # Block 4.
    forged = chain.start_exit(chain.prove(0, to_dave), deposit, height=20)
    assert chain.challenge(forged, chain.prove(0, to_bob), height=21)
    exit_id = chain.start_exit(chain.prove(0, to_carol), chain.prove(0, to_bob), height=30)
    assert not chain.challenge(exit_id, chain.prove(0, to_dave), height=31)
    with pytest.raises(ValueError, match="not over"):
        chain.finalize(exit_id, height=36)
    assert not chain.challenge(exit_id, chain.prove(0, to_carol), height=37)  # Too late.
    assert chain.finalize(exit_id, height=37).owner == public_key(CAROL)
    with pytest.raises(ValueError, match="already exited"):
        chain.start_exit(chain.prove(0, to_carol), chain.prove(0, to_bob), height=40)


def test_deposits_exit_alone_and_invalid_exits_are_refused():
    chain, deposit, to_bob, to_carol = plasma()
    second = chain.deposit(public_key(DAVE))
    exit_id = chain.start_exit(second, None, height=0)
    assert chain.finalize(exit_id, height=7).owner == public_key(DAVE)
    exit_again = chain.start_exit(chain.prove(0, to_carol), chain.prove(0, to_bob), height=0)
    other = chain.start_exit(chain.prove(0, to_carol), chain.prove(0, to_bob), height=0)
    chain.finalize(exit_again, height=7)
    with pytest.raises(ValueError, match="already exited"):
        chain.finalize(other, height=7)
    fresh, deposit, to_bob, to_carol = plasma()
    with pytest.raises(ValueError, match="only a deposit"):
        fresh.start_exit(fresh.prove(0, to_bob), None, height=0)
    with pytest.raises(ValueError, match="does not validly spend"):
        fresh.start_exit(fresh.prove(0, to_carol), deposit, height=0)  # Skips Bob.
    fake = InclusionProof(CoinTransfer(0, public_key(DAVE), 1), to_bob, deposit.proof)
    with pytest.raises(ValueError, match="not in that block"):
        fresh.start_exit(fake, deposit, height=0)
    exit_id = fresh.start_exit(fresh.prove(0, to_bob), deposit, height=0)
    unrelated = fresh.deposit(public_key(DAVE))
    assert not fresh.challenge(exit_id, unrelated, height=1)  # Another coin.
    unproven = InclusionProof(fresh.prove(0, to_carol).transfer, 99, deposit.proof)
    assert not fresh.challenge(exit_id, unproven, height=1)  # Not in any block.
    with pytest.raises(ValueError, match="did not move"):
        fresh.prove(1, to_bob)


def test_operator_cannot_move_coins_twice_or_invent_them():
    chain = PlasmaChain(depth=1)
    chain.deposit(public_key(ALICE))
    transfer = sign_transfer(ALICE, 0, public_key(BOB), 1)
    with pytest.raises(ValueError, match="at most once"):
        chain.submit_block([transfer, transfer])
    with pytest.raises(ValueError, match="at most once"):
        chain.submit_block([sign_transfer(ALICE, 5, public_key(BOB), 1)])
    chain.deposit(public_key(ALICE))
    with pytest.raises(ValueError, match="no coin slots"):
        chain.deposit(public_key(ALICE))


# Sharding ---------------------------------------------------------------------


def test_shard_failure_probability_is_hypergeometric():
    assert shard_failure_probability(10, 0, 4) == 0
    assert shard_failure_probability(10, 10, 4) == 1
    # Committee of 3 from 4 with 1 malicious: fails whenever it is chosen (3 of 4 committees).
    assert shard_failure_probability(4, 1, 3) == pytest.approx(0.75)
    small = shard_failure_probability(1_000, 250, 20)
    large = shard_failure_probability(1_000, 250, 200)
    assert large < small / 100
    with pytest.raises(ValueError, match="exceed"):
        shard_failure_probability(5, 6, 2)


def test_random_assignment_and_epochs():
    committees = assign_shards(12, 3, seed=5)
    assert sorted(v for c in committees for v in c) == list(range(12))
    assert committees == assign_shards(12, 3, seed=5) != assign_shards(12, 3, seed=6)
    with pytest.raises(ValueError, match="more shards"):
        assign_shards(2, 3)
    rate = compromised_epochs(400, 100, 4, epochs=300, seed=2)
    expected = 1 - (1 - shard_failure_probability(400, 100, 100)) ** 4
    assert rate == pytest.approx(expected, abs=0.04)
    assert compromised_epochs(400, 0, 4, epochs=5) == 0


def test_atomix_commits_or_unlocks_everything():
    shards = [{"alice": 5}, {"alice": 3}, {}]
    done = atomix_transfer(shards, [(0, "alice", 5), (1, "alice", 3)], (2, "bob"))
    assert done.committed and done.rejected == ()
    assert [dict(s) for s in done.balances] == [{"alice": 0}, {"alice": 0}, {"bob": 8}]
    aborted = atomix_transfer(shards, [(0, "alice", 5), (1, "alice", 4)], (2, "bob"))
    assert not aborted.committed and aborted.rejected == (1,)
    assert [dict(s) for s in aborted.balances] == shards  # Shard 0 unlocked.
    with pytest.raises(ValueError, match="no such shard"):
        atomix_transfer(shards, [(3, "alice", 1)], (2, "bob"))
    with pytest.raises(ValueError, match="no such shard"):
        atomix_transfer(shards, [(0, "alice", 1)], (5, "bob"))


# Rollups ----------------------------------------------------------------------

BATCH = [Transfer("alice", "bob", 4), Transfer("bob", "carol", 10), Transfer("bob", "carol", 1)]


def test_state_transition_skips_invalid_transactions():
    after, trace = execute_batch({"alice": 10}, BATCH)
    assert after == {"alice": 6, "bob": 3, "carol": 1}
    assert len(trace) == 4 and trace[2] == trace[1] != trace[0]  # The overdraft is skipped.
    assert apply_transfer({"a": 1}, Transfer("a", "b", 0)) == {"a": 1}
    assert state_root({"b": 1, "a": 2}) == state_root({"a": 2, "b": 1})
    assert batch_digest(BATCH) != batch_digest(BATCH[:2])


def test_zk_rollup_accepts_only_proven_transitions():
    rollup = ZKRollup({"alice": 10}, verifier_gas=300_000, bytes_per_transaction=12)
    proof = rollup.prove(BATCH)
    with pytest.raises(ValueError, match="false state transition"):
        rollup.prove(BATCH, claimed_root=state_root({"mallory": 10}))
    with pytest.raises(ValueError, match="another state or batch"):
        rollup.submit(BATCH[:2], proof)
    forged = proof.__class__(proof.old_root, state_root({"mallory": 10}), proof.batch_digest)
    with pytest.raises(ValueError, match="does not verify"):
        rollup.submit(BATCH, forged)
    assert rollup.submit(BATCH, proof) == 300_000 + 3 * 12 * 16
    assert dict(rollup.balances) == {"alice": 6, "bob": 3, "carol": 1}
    with pytest.raises(ValueError, match="another state"):
        rollup.submit(BATCH, proof)  # Replaying the proof: the root has moved on.
    assert rollup.submit([], rollup.prove([])) == 300_000 + 12 * 16


def test_batch_gas_amortizes_the_verification():
    per_transaction = [
        batch_gas(n, bytes_per_transaction=12, fixed_gas=300_000) / n for n in (1, 100, 1_000)
    ]
    assert per_transaction[0] > 21_000 > per_transaction[1] > per_transaction[2] > 192


@given(st.lists(st.integers(0, 3), min_size=2, max_size=40), st.data())
def test_bisection_finds_the_first_disagreement(prefix, data):
    n = len(prefix)
    first = data.draw(st.integers(1, n - 1))
    honest = [bytes([v]) for v in prefix]
    claimed = honest[:first] + [b"x" + h for h in honest[first:]]
    step, rounds = bisect(claimed, honest)
    assert step == first - 1 and rounds <= (n - 1).bit_length()


def test_bisection_validation():
    with pytest.raises(ValueError, match="same length"):
        bisect([b"a"], [b"a"])
    with pytest.raises(ValueError, match="agree at the start"):
        bisect([b"a", b"b"], [b"a", b"b"])


def test_optimistic_rollup_challenge_window():
    rollup = OptimisticRollup({"alice": 10}, window=100, bond=7)
    honest_after, honest = execute_batch({"alice": 10}, BATCH)
    assert rollup.propose("op", BATCH, honest, height=1) == 0
    assert rollup.challenge(0, "carol", height=5) is None  # Nothing wrong.
    # A second, fraudulent batch on top: it credits mallory at step 1.
    second = [Transfer("carol", "dave", 1), Transfer("alice", "eve", 1)]
    _, trace = execute_batch(honest_after, second)
    forged = (*trace[:2], state_root({**honest_after, "mallory": 50}))
    assert rollup.propose("mallory", second, forged, height=2) == 1
    proof = rollup.challenge(1, "carol", height=50)
    assert proof is not None and proof.step == 1 and proof.rounds == 1
    assert proof.claimed == forged[2] and proof.correct == trace[2]
    assert rollup.payouts == {"carol": 7} and len(rollup.pending) == 1
    with pytest.raises(ValueError, match="window is over"):
        rollup.challenge(0, "carol", height=101)
    assert rollup.finalize(height=100) == 0 and rollup.finalize(height=101) == 1
    assert dict(rollup.balances) == honest_after and rollup.root == honest[-1]


def test_optimistic_rollup_validation():
    rollup = OptimisticRollup({"alice": 10}, window=10)
    _, trace = execute_batch({"alice": 10}, BATCH)
    with pytest.raises(ValueError, match="one root per transaction"):
        rollup.propose("op", BATCH, trace[:2], height=0)
    with pytest.raises(ValueError, match="previous root"):
        rollup.propose("op", BATCH[:1], trace[1:3], height=0)
