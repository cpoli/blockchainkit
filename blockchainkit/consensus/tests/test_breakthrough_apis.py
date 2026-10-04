"""APIs behind the consensus history: agreement protocols, attack models,
difficulty, fork choice, stake games, sortition, and finality."""

import pytest

import blockchainkit as bk

k = bk.consensus
s = bk.structures


# Nakamoto's double-spend probability (whitepaper, section 11) --------------


@pytest.mark.parametrize(
    "q,z,expected",
    [
        (0.1, 0, 1.0),
        (0.1, 1, 0.2045873),
        (0.1, 2, 0.0509779),
        (0.1, 5, 0.0009137),
        (0.1, 10, 0.0000012),
        (0.3, 5, 0.1773523),
        (0.3, 10, 0.0416605),
    ],
)
def test_attacker_success_matches_the_whitepaper_table(q, z, expected):
    assert k.attacker_success_probability(q, z) == pytest.approx(expected, abs=5e-8)


def test_attacker_success_is_certain_at_half_and_validated():
    assert k.attacker_success_probability(0.5, 10) == 1.0
    assert k.attacker_success_probability(0.0, 3) == 0.0
    with pytest.raises(ValueError):
        k.attacker_success_probability(1.5, 1)
    with pytest.raises(TypeError):
        k.attacker_success_probability(True, 1)


# Byzantine generals (oral messages) ---------------------------------------


def test_oral_messages_succeeds_with_more_than_three_m_generals():
    for traitors in ({0}, {2}, {3}):
        result = k.oral_messages(4, traitors, "attack", rounds=1)
        assert result.agreement
        if 0 not in traitors:
            assert result.validity


def test_three_generals_cannot_tolerate_one_traitor():
    result = k.oral_messages(3, {2}, "attack", rounds=1)
    assert not result.validity  # The loyal lieutenant is talked out of following.
    assert result.decisions[1] == "retreat"


def test_oral_messages_with_two_rounds_tolerates_two_traitors_among_seven():
    for traitors in ({0, 3}, {2, 5}, {1, 6}):
        result = k.oral_messages(7, traitors, "attack", rounds=2)
        assert result.agreement and (0 in traitors or result.validity)


def test_oral_messages_validation():
    with pytest.raises(ValueError):
        k.oral_messages(2, set(), "attack", rounds=1)
    with pytest.raises(ValueError):
        k.oral_messages(4, {9}, "attack", rounds=1)
    with pytest.raises(ValueError):
        k.oral_messages(4, set(), "charge", rounds=1)


# Ben-Or randomized consensus and the FLP lesson ---------------------------


def test_ben_or_decides_with_a_random_coin_against_an_adversary():
    run = k.ben_or([0, 0, 1, 1], faults=1, seed=7, max_rounds=200)
    assert run.decided and len(set(run.decisions.values())) == 1


def test_a_deterministic_coin_lets_the_adversary_stall_forever():
    run = k.ben_or([0, 0, 1, 1], faults=1, coin=lambda process, round_: process % 2, max_rounds=200)
    assert not run.decided and run.rounds == 200


def test_ben_or_decides_at_once_on_unanimous_input_and_validates():
    run = k.ben_or([1, 1, 1, 1, 1], faults=2, seed=0)
    assert run.decided and run.rounds == 1 and set(run.decisions.values()) == {1}
    with pytest.raises(ValueError):
        k.ben_or([0, 1], faults=1)
    with pytest.raises(ValueError):
        k.ben_or([0, 2, 1], faults=1)


# Partial synchrony ---------------------------------------------------------


def test_doubling_timeouts_make_progress_after_gst():
    run = k.view_changes(gst=100, delta=7, base_timeout=1)
    assert run.decided_view >= 1 and run.decision_time >= 100
    assert run.timeouts[run.decided_view] >= 7
    assert run.timeouts == tuple(2**v for v in range(len(run.timeouts)))


def test_fixed_timeouts_below_delta_never_progress():
    with pytest.raises(TimeoutError):
        k.view_changes(gst=0, delta=7, base_timeout=1, growth=1, max_views=50)
    with pytest.raises(ValueError):
        k.view_changes(gst=0, delta=0, base_timeout=1)


# Dwork-Naor pricing function ------------------------------------------------


def test_square_root_pricing_is_expensive_to_compute_cheap_to_check():
    p = 1_000_003  # p = 3 mod 4.
    assert p % 4 == 3
    result = k.modular_square_root(pow(123_456, 2, p), p)
    assert pow(result.root, 2, p) == pow(123_456, 2, p)
    assert result.multiplications > 20  # Versus one multiplication to verify.
    with pytest.raises(ValueError, match="residue"):
        k.modular_square_root(5, 7)  # 5 is not a square modulo 7.
    with pytest.raises(ValueError):
        k.modular_square_root(2, 13)  # 13 = 1 mod 4.


# PBFT ---------------------------------------------------------------------


def test_pbft_is_safe_with_f_faults_even_under_an_equivocating_leader():
    result = k.pbft_round(4, faulty={0}, value="A", equivocate=True)
    committed = {v for v in result.commits.values() if v is not None}
    assert len(committed) <= 1 and k.quorum_size(4) == 3


def test_pbft_commits_everywhere_with_an_honest_leader():
    result = k.pbft_round(7, faulty={5, 6}, value="A")
    assert set(result.commits.values()) == {"A"} and len(result.commits) == 5


def test_pbft_breaks_with_more_than_f_faults():
    result = k.pbft_round(4, faulty={0, 1}, value="A", equivocate=True)
    committed = {v for v in result.commits.values() if v is not None}
    assert committed == {"A", "B"}  # Two honest replicas commit different values.


def test_pbft_validation():
    with pytest.raises(ValueError):
        k.pbft_round(3, faulty=set(), value="A")
    with pytest.raises(ValueError):
        k.pbft_round(4, faulty={4}, value="A")


# Difficulty retargeting -----------------------------------------------------


def test_retarget_scales_and_clamps():
    assert k.retarget(1000, actual_time=600, expected_time=1200) == 500
    assert k.retarget(1000, actual_time=100_000, expected_time=100) == 4000
    assert k.retarget(1000, actual_time=1, expected_time=1000) == 250
    with pytest.raises(ValueError):
        k.retarget(0, 1, 1)


def test_retargeting_restores_the_block_interval_after_a_hashrate_jump():
    hashrates = [1.0] * 2000 + [4.0] * 6000
    run = k.simulate_difficulty(hashrates, interval=600, window=500, seed=3)
    late = run.block_times[-1000:]
    assert abs(sum(late) / len(late) - 600) < 60
    assert len(run.targets) == len(hashrates)


# GHOST ---------------------------------------------------------------------


def _forked_chain():
    genesis = bk.consensus.mine(s.Block(difficulty=2)).block
    chain = s.Blockchain(genesis)

    def child(parent, t):
        block = bk.consensus.mine(
            s.Block(parent.hash, height=parent.height + 1, timestamp=t, difficulty=2)
        ).block
        chain.add(block)
        return block

    # Branch A: a single longer chain. Branch B: shorter but bushier.
    a1 = child(genesis, 1)
    a2 = child(a1, 2)
    a3 = child(a2, 3)
    b1 = child(genesis, 4)
    b2 = [child(b1, 10 + i) for i in range(3)]
    return chain, a3, b1, b2


def test_ghost_follows_the_heaviest_subtree_not_the_longest_chain():
    chain, a3, b1, b2 = _forked_chain()
    assert chain.tip == a3  # Longest chain.
    ghost = k.ghost_tip(chain)
    assert ghost in b2  # GHOST picks the bushier subtree.
    a1 = chain.blocks[chain.blocks[a3.previous_hash].previous_hash]
    assert k.subtree_work(chain, b1.hash) == 4 * 4 > k.subtree_work(chain, a1.hash) == 3 * 4


# Selfish mining -------------------------------------------------------------


@pytest.mark.parametrize("alpha,gamma", [(0.2, 0.0), (0.3, 0.5), (0.35, 0.0), (0.4, 1.0)])
def test_selfish_mining_simulation_matches_the_closed_form(alpha, gamma):
    simulated = k.simulate_selfish_mining(alpha, gamma, blocks=200_000, seed=1).revenue
    assert simulated == pytest.approx(k.selfish_mining_revenue(alpha, gamma), abs=0.01)


def test_selfish_mining_threshold():
    assert k.selfish_mining_threshold(0.0) == pytest.approx(1 / 3)
    assert k.selfish_mining_threshold(1.0) == 0.0
    for gamma in (0.0, 0.5):
        t = k.selfish_mining_threshold(gamma)
        assert k.selfish_mining_revenue(t + 0.02, gamma) > t + 0.02
        assert k.selfish_mining_revenue(max(t - 0.02, 0.01), gamma) < max(t - 0.02, 0.01)
    with pytest.raises(ValueError):
        k.selfish_mining_revenue(0.6, 0.5)


# Nothing at stake ----------------------------------------------------------


def test_voting_on_every_fork_dominates_without_slashing():
    payoffs = k.fork_voting_payoffs(0.6, reward=1.0, penalty=0.0)
    assert payoffs["both"] > payoffs["A"] > payoffs["B"]
    slashed = k.fork_voting_payoffs(0.6, reward=1.0, penalty=2.0)
    assert slashed["A"] > slashed["both"]


# Cryptographic sortition ---------------------------------------------------


def test_sortition_is_proportional_to_stake_and_split_proof():
    total, expected = 10_000, 20
    whole = [
        k.sortition(b"key", 1000, total, expected, round_seed=r.to_bytes(4, "big"))
        for r in range(400)
    ]
    mean = sum(whole) / len(whole)
    assert mean == pytest.approx(expected * 1000 / total, rel=0.15)
    split = [
        sum(
            k.sortition(bytes([i]), 100, total, expected, round_seed=r.to_bytes(4, "big"))
            for i in range(10)
        )
        for r in range(400)
    ]
    assert sum(split) / len(split) == pytest.approx(mean, rel=0.2)  # Splitting stake gains nothing.
    with pytest.raises(ValueError):
        k.sortition(b"key", 10, 5, 1, round_seed=b"r")


# Casper FFG ---------------------------------------------------------------


def test_casper_justifies_and_finalizes_with_two_thirds():
    ffg = k.FinalityGadget({"a": 30, "b": 30, "c": 30, "d": 10})
    for v in ("a", "b", "c"):
        ffg.vote(v, source=0, target=1)
    assert 1 in ffg.justified and 0 in ffg.finalized and 1 not in ffg.finalized
    for v in ("a", "b", "c"):
        ffg.vote(v, source=1, target=2)
    assert 1 in ffg.finalized


def test_casper_detects_double_and_surround_votes():
    ffg = k.FinalityGadget({"a": 50, "b": 50})
    ffg.vote("a", source=0, target=2)
    ffg.vote("a", source=0, target=2)  # Identical vote: not an offense.
    assert ffg.slashable == ()
    ffg.vote("a", source=0, target=2, checkpoint=b"other")  # Same target height, different block.
    ffg.vote("b", source=0, target=3)
    ffg.vote("b", source=1, target=2)  # Surrounded by (0, 3).
    offenses = {(o.validator, o.kind) for o in ffg.slashable}
    assert offenses == {("a", "double vote"), ("b", "surround vote")}
    with pytest.raises(ValueError):
        ffg.vote("z", source=0, target=1)
    with pytest.raises(ValueError):
        ffg.vote("a", source=2, target=1)


@pytest.mark.parametrize(
    "call,error",
    [
        (lambda: k.simulate_difficulty([1.0, 0.0]), ValueError),
        (lambda: k.selfish_mining_revenue(0.3, 1.5), ValueError),
        (lambda: k.selfish_mining_threshold(-0.1), ValueError),
        (lambda: k.sortition("key", 1, 10, 1, round_seed=b"r"), TypeError),
        (lambda: k.fork_voting_payoffs(1.5, 1.0, 0.0), ValueError),
        (lambda: k.fork_voting_payoffs(0.5, -1.0, 0.0), ValueError),
    ],
)
def test_consensus_models_reject_bad_arguments(call, error):
    with pytest.raises(error):
        call()


def test_sortition_selects_all_stake_when_everyone_is_expected():
    assert k.sortition(b"key", 5, 5, 5, round_seed=b"r") == 5


def test_a_minority_vote_does_not_justify():
    ffg = k.FinalityGadget({"a": 1, "b": 1, "c": 1})
    ffg.vote("a", source=0, target=1)
    assert ffg.justified == {0}
    ffg.vote("b", source=5, target=6)  # Unjustified source: recorded but not counted.
    assert ffg.justified == {0}


def test_justifying_a_skipped_checkpoint_finalizes_nothing_new():
    ffg = k.FinalityGadget({"a": 1, "b": 1, "c": 1})
    for v in "abc":
        ffg.vote(v, source=0, target=2)
    assert 2 in ffg.justified and ffg.finalized == {0}
