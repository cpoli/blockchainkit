"""Spilman, duplex, Lightning and eltoo channels, atomic swaps, and watchtowers."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blockchainkit.channels import (
    AtomicSwap,
    DuplexChannel,
    EltooChannel,
    LightningChannel,
    SpilmanChannel,
    SwapOutcome,
    Watchtower,
    first_confirmed,
    invalidation_locktimes,
    make_appointment,
    tower_liable,
    verify_receipt,
)
from blockchainkit.channels.utils.scripts import check_key, derived_key
from blockchainkit.crypto import sha256
from blockchainkit.crypto.systems.curves import SECP256K1
from blockchainkit.crypto.systems.signatures import sign

# Keys -------------------------------------------------------------------------


def test_key_validation():
    with pytest.raises(TypeError):
        check_key(True, "key")
    with pytest.raises(ValueError):
        check_key(SECP256K1.order, "key")
    assert derived_key(7, "a") != derived_key(7, "b")


# Spilman ----------------------------------------------------------------------


def spilman(**overrides):
    params = {"payer_key": 7, "payee_key": 5, "capacity": 100, "expiry": 50} | overrides
    return SpilmanChannel("alice", "bob", **params)


def test_spilman_pays_and_closes():
    channel = spilman()
    assert [channel.pay(10) for _ in range(3)] == [10, 20, 30]
    settlement = channel.close(height=20)
    assert settlement.kind == "cooperative" and settlement.state == 3
    assert dict(settlement.payouts) == {"alice": 70, "bob": 30}
    with pytest.raises(ValueError, match="closed"):
        channel.pay(1)


def test_spilman_refund_only_after_expiry():
    channel = spilman()
    channel.pay(40)
    with pytest.raises(ValueError, match="locked until"):
        channel.refund(height=49)
    settlement = channel.refund(height=50)  # The payee waited too long.
    assert settlement.kind == "refund" and dict(settlement.payouts) == {"alice": 100, "bob": 0}
    with pytest.raises(ValueError, match="closed"):
        channel.close(height=51)


def test_spilman_validation():
    with pytest.raises(ValueError, match="differ"):
        SpilmanChannel("a", "a", payer_key=1, payee_key=2, capacity=1, expiry=1)
    with pytest.raises(ValueError):
        spilman(capacity=0)
    channel = spilman(capacity=10)
    with pytest.raises(ValueError, match="nothing"):
        channel.close(height=1)
    with pytest.raises(ValueError, match="capacity"):
        channel.pay(11)
    with pytest.raises(ValueError):
        channel.pay(0)


# Atomic swaps -----------------------------------------------------------------


def swap(timeout_a=48, timeout_b=24):
    return AtomicSwap(
        7, 5, b"secret", amount_a=10, amount_b=3, timeout_a=timeout_a, timeout_b=timeout_b
    )


def test_swap_completes():
    deal = swap()
    assert not deal.claim_a(height=1)  # Bob does not know the secret yet.
    assert not deal.claim_b(height=1)  # Bob has not locked yet.
    deal.lock_bob()
    with pytest.raises(ValueError, match="already"):
        deal.lock_bob()
    assert deal.claim_b(height=5) and deal.revealed == b"secret"
    assert deal.claim_a(height=6)
    outcome = deal.outcome()
    assert outcome == SwapOutcome((0, 3), (10, 0), True)
    assert outcome.completed and outcome.atomic and not outcome.refunded
    assert not deal.claim_b(height=7)  # Already spent.


def test_swap_refunds_when_alice_disappears():
    deal = swap()
    deal.lock_bob()
    assert not deal.refund_b(height=23) and deal.refund_b(height=24)
    assert not deal.refund_a(height=47) and deal.refund_a(height=48)
    outcome = deal.outcome()
    assert outcome.refunded and outcome.atomic and not outcome.secret_revealed


def test_swap_with_reversed_timeouts_lets_alice_take_both():
    deal = swap(timeout_a=20, timeout_b=24)
    deal.lock_bob()
    assert deal.refund_a(height=20)  # Alice takes back her coins first...
    assert deal.claim_b(height=23)  # ...then claims Bob's before his refund unlocks.
    assert not deal.claim_a(height=23)  # Too late: chain A's output is gone.
    outcome = deal.outcome()
    assert outcome.alice == (10, 3) and not outcome.atomic


def test_swap_validation():
    with pytest.raises(TypeError):
        AtomicSwap(7, 5, "secret", amount_a=1, amount_b=1, timeout_a=2, timeout_b=1)
    with pytest.raises(ValueError):
        AtomicSwap(7, 5, b"s", amount_a=0, amount_b=1, timeout_a=2, timeout_b=1)
    assert swap().outcome() == SwapOutcome((0, 0), (0, 0), False)
    assert not SwapOutcome((0, 0), (0, 0), False).atomic


# Duplex channels --------------------------------------------------------------


def test_invalidation_tree_counts_down():
    assert invalidation_locktimes(0, depth=1, steps=4, delta=5, base=2) == (17,)
    assert invalidation_locktimes(3, depth=1, steps=4, delta=5, base=2) == (2,)
    with pytest.raises(ValueError, match="only 4"):
        invalidation_locktimes(4, depth=1, steps=4, delta=5)
    with pytest.raises(ValueError, match="no branch"):
        first_confirmed([], depth=1, steps=2, delta=1)


@given(st.lists(st.integers(0, 26), min_size=1, max_size=6))
def test_the_newest_branch_always_confirms_first(states):
    assert first_confirmed(states, depth=3, steps=3, delta=7) == max(states)


def test_duplex_channel_resets_and_closes():
    channel = DuplexChannel(("alice", "bob"), (10, 10), depth=2, steps=2, delta=6)
    channel.pay("alice", 10)
    channel.pay("bob", 15)
    assert channel.balances() == {"alice": 15, "bob": 5} and channel.resets == 1
    assert channel.locktimes() == (6, 0)
    settlement = channel.close(height=100)
    assert settlement.height == 106 and settlement.state == 1
    with pytest.raises(ValueError, match="insufficient"):
        channel.pay("bob", 6)
    with pytest.raises(ValueError, match="not a party"):
        channel.pay("carol", 1)
    channel.pay("bob", 5)
    channel.pay("alice", 20)  # Reset 2.
    channel.pay("bob", 20)  # Reset 3, the tree's last state.
    assert channel.resets == 3 and channel.locktimes() == (0, 0)
    with pytest.raises(ValueError, match="exhausted"):
        channel.pay("alice", 5)
    with pytest.raises(ValueError, match="distinct"):
        DuplexChannel(("a", "a"), (1, 1), depth=1, steps=2, delta=1)


# Lightning --------------------------------------------------------------------


def lightning(delay=6):
    return LightningChannel(("alice", "bob"), (7, 5), (100, 0), delay=delay, max_states=8)


def test_lightning_cooperative_close():
    channel = lightning()
    assert channel.pay("alice", 30) == 1 and channel.pay("bob", 10) == 2
    assert channel.balances == {"alice": 80, "bob": 20}
    settlement = channel.close_cooperatively(height=5)
    assert settlement.kind == "cooperative" and dict(settlement.payouts) == channel.balances


def test_lightning_unilateral_close_waits_for_the_delay():
    channel = lightning()
    channel.pay("alice", 30)
    commitment = channel.publish("bob", height=10)
    assert commitment.holder == "bob" and commitment.to_local == 30
    with pytest.raises(ValueError, match="locked"):
        channel.sweep(height=15)
    with pytest.raises(ValueError, match="not been revoked"):
        channel.penalize(height=12)
    settlement = channel.sweep(height=16)
    assert dict(settlement.payouts) == {"alice": 70, "bob": 30}
    with pytest.raises(ValueError, match="already been claimed"):
        channel.sweep(height=17)
    with pytest.raises(ValueError, match="already spent"):
        channel.publish("alice", height=18)
    with pytest.raises(ValueError, match="already been published"):
        channel.close_cooperatively(height=18)
    with pytest.raises(ValueError, match="closing"):
        channel.pay("alice", 1)


def test_lightning_penalizes_a_revoked_commitment():
    channel = lightning()
    for _ in range(3):
        channel.pay("alice", 10)
    channel.publish("alice", state=1, height=50)
    settlement = channel.penalize(height=55)
    assert settlement.kind == "penalty" and settlement.state == 1
    assert dict(settlement.payouts) == {"alice": 0, "bob": 100}


def test_shachain_secrets_derive_backwards():
    channel = lightning()
    for _ in range(4):
        channel.pay("alice", 1)
    latest = channel.derive_secret("alice", 3)
    assert channel.derive_secret("alice", 0) == sha256(sha256(sha256(latest)))
    assert channel.derive_secret("alice", 4) is None  # The current state is not revoked.
    assert lightning().derive_secret("alice", 0) is None  # Nothing revealed yet.


def test_lightning_rejects_a_wrong_justice_signature_and_bad_input():
    channel = lightning()
    channel.pay("alice", 10)
    channel.publish("alice", state=0, height=1)
    forged = sign(b"something else", 3, nonce=4)
    with pytest.raises(ValueError, match="does not match"):
        channel.penalize(height=2, justice=forged)
    with pytest.raises(ValueError, match="no commitment has been published"):
        lightning().sweep(height=1)
    with pytest.raises(ValueError, match="holds no commitment"):
        lightning().commitment("alice", 5)
    with pytest.raises(ValueError, match="not a party"):
        lightning().pay("carol", 1)
    with pytest.raises(ValueError, match="insufficient"):
        lightning().pay("bob", 1)
    with pytest.raises(ValueError, match="distinct"):
        LightningChannel(("a", "a"), (7, 5), (1, 1))
    with pytest.raises(ValueError, match="funded"):
        LightningChannel(("a", "b"), (7, 5), (0, 0))


def test_lightning_hash_chain_runs_out():
    channel = LightningChannel(("alice", "bob"), (7, 5), (10, 0), max_states=2)
    channel.pay("alice", 1)
    with pytest.raises(ValueError, match="exhausted"):
        channel.pay("alice", 1)


# eltoo ------------------------------------------------------------------------


def test_eltoo_replaces_old_states_without_penalty():
    channel = EltooChannel(("alice", "bob"), (7, 5), (100, 0), delay=6)
    for _ in range(3):
        channel.pay("alice", 10)
    channel.publish(state=0, height=10)
    channel.publish(state=2, height=11)  # Any newer state can replace it.
    with pytest.raises(ValueError, match="cannot replace"):
        channel.publish(state=1, height=12)  # An older one cannot.
    channel.publish(height=13)
    with pytest.raises(ValueError, match="locked"):
        channel.settle(height=18)
    settlement = channel.settle(height=19)
    assert settlement.state == 3 and dict(settlement.payouts) == {"alice": 70, "bob": 30}
    with pytest.raises(ValueError, match="settled"):
        channel.settle(height=20)
    with pytest.raises(ValueError, match="settled"):
        channel.publish(height=20)


def test_eltoo_validation():
    channel = EltooChannel(("alice", "bob"), (7, 5), (10, 10), delay=2)
    with pytest.raises(ValueError, match="no update"):
        channel.settle(height=1)
    with pytest.raises(ValueError, match="no state 4"):
        channel.publish(state=4, height=1)
    with pytest.raises(ValueError, match="not a party"):
        channel.pay("carol", 1)
    with pytest.raises(ValueError, match="insufficient"):
        channel.pay("bob", 11)
    channel.publish(height=1)
    with pytest.raises(ValueError, match="closing"):
        channel.pay("alice", 1)
    with pytest.raises(ValueError, match="distinct"):
        EltooChannel(("a", "a"), (7, 5), (1, 1))


# Watchtowers ------------------------------------------------------------------


def breached(tower_online=True, expires=100):
    channel = lightning()
    channel.pay("alice", 40)
    tower = Watchtower(99, collateral=50, online=tower_online)
    receipt = tower.appoint(*make_appointment(channel, "bob", 0), expires=expires)
    return channel, tower, receipt


def test_tower_penalizes_on_the_customers_behalf():
    channel, tower, receipt = breached()
    assert verify_receipt(receipt)
    assert tower.watch(channel, height=1) is None  # Nothing on chain yet.
    channel.publish("alice", state=0, height=10)
    settlement = tower.watch(channel, height=11)
    assert settlement is not None and dict(settlement.payouts) == {"alice": 0, "bob": 100}
    assert tower.watch(channel, height=12) is None  # Already settled.
    assert not tower_liable(receipt, channel)


def test_offline_tower_is_liable_under_pisa():
    channel, tower, receipt = breached(tower_online=False)
    assert not tower_liable(receipt, channel)  # Nothing published yet.
    channel.publish("alice", state=0, height=10)
    assert tower.watch(channel, height=11) is None
    channel.sweep(height=16)
    assert tower_liable(receipt, channel)


def test_tower_ignores_unwatched_and_expired_commitments():
    channel, tower, receipt = breached(expires=5)
    channel.publish("alice", state=1, height=10)  # The current state: no hint matches.
    assert tower.watch(channel, height=10) is None
    channel, tower, receipt = breached(expires=5)
    channel.publish("alice", state=0, height=10)
    assert tower.watch(channel, height=10) is None  # The appointment has expired.
    channel.sweep(height=16)
    assert not tower_liable(receipt, channel)  # Published after the receipt expired.
    forged = receipt.__class__(receipt.tower, receipt.hint, 10**6, receipt.signature)
    assert not verify_receipt(forged) and not tower_liable(forged, channel)
    with pytest.raises(ValueError, match="16 bytes"):
        tower.appoint(b"short", b"", expires=1)


@settings(max_examples=10, deadline=None)
@given(st.integers(0, 3))
def test_any_revoked_state_can_be_penalized(state):
    channel = lightning()
    for _ in range(4):
        channel.pay("alice", 5)
    channel.publish("alice", state=state, height=0)
    assert channel.penalize(height=1).payouts["bob"] == 100
