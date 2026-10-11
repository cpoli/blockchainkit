"""Multi-hop routing and probing, and the contracts: state channels, BTC Relay, and bridges."""

import pytest

from blockchainkit.channels import (
    BTCRelay,
    ChannelNetwork,
    ForgedVerifier,
    GuardianVerifier,
    PreimageManager,
    StateChannel,
    ValidatorBridge,
    WormholeBridge,
    collateral_time,
    htlc_expiries,
    mine_header,
    probe_balance,
    sign_state,
    sign_withdrawal,
    sprites_expiries,
    withdrawal_message,
)
from blockchainkit.contracts import World
from blockchainkit.crypto import public_key, sha256
from blockchainkit.network import Graph
from blockchainkit.structures import MerkleTree

# Routing ----------------------------------------------------------------------

LINE = Graph(4, [(0, 1), (1, 2), (2, 3)])


def line_network(**policy):
    balances = {(u, v): 1_000 for a, b in LINE.edges for u, v in ((a, b), (b, a))}
    return ChannelNetwork(LINE, balances, **policy)


def test_route_amounts_and_expiries_grow_backwards():
    network = line_network(base_fee=1, fee_rate=10_000, cltv_delta=40, final_cltv=9)
    route = network.route((0, 1, 2, 3), 100, height=500)
    assert route.amounts == (104, 102, 100)  # Each hop adds 1 + 1% of what it forwards.
    assert route.expiries == (589, 549, 509) and route.fee == 4
    assert network.find_route(0, 3, 100, height=500) == route
    with pytest.raises(ValueError, match="no channel"):
        network.route((0, 2), 1)
    with pytest.raises(ValueError, match="sender and a recipient"):
        network.route((0,), 1)


def test_payments_move_balances_atomically():
    network = line_network(base_fee=0, fee_rate=0)
    attempt = network.pay(0, 3, 300)
    assert attempt.success and attempt.failed_at is None
    assert network.balance(0, 1) == 700 and network.balance(3, 2) == 1_300
    failed = network.send(network.route((0, 1, 2, 3), 800))
    assert not failed.success and failed.failed_at == (0, 1)
    assert failed.error == "temporary_channel_failure" and network.balance(1, 2) == 700
    with pytest.raises(ValueError, match="no route"):
        network.find_route(0, 3, 2_001)  # More than any channel's capacity.
    with pytest.raises(ValueError, match="no route"):
        network.find_route(0, 0, 1)


def test_channel_network_validation_and_random_split():
    with pytest.raises(ValueError, match="missing"):
        ChannelNetwork(Graph(2, [(0, 1)]), {(0, 1): 5})
    with pytest.raises(ValueError, match="not a channel"):
        ChannelNetwork(Graph(2, [(0, 1)]), {(0, 1): 5, (1, 0): 5, (0, 2): 1})
    network = ChannelNetwork.random(LINE, capacity=1_000, seed=4, cltv_delta=10)
    assert all(network.capacity(u, v) == 1_000 for u, v in LINE.edges)
    assert network.cltv_delta == 10 and network.fee(1_000_000) == 1_001


def test_probing_finds_the_balance_in_logarithmic_probes():
    graph = Graph(3, [(0, 1), (1, 2)])
    for balance in (0, 1, 617, 999, 1_000):
        network = ChannelNetwork(
            graph, {(0, 1): 10_000, (1, 0): 0, (1, 2): balance, (2, 1): 1_000 - balance}
        )
        result = probe_balance(network, 0, 1, 2)
        assert result.low == result.high == balance and result.probes <= 10
        assert network.balance(1, 2) == balance  # Probing moved nothing.


def test_probing_stops_when_the_probers_channel_runs_dry():
    graph = Graph(3, [(0, 1), (1, 2)])
    network = ChannelNetwork(graph, {(0, 1): 300, (1, 0): 0, (1, 2): 800, (2, 1): 200})
    result = probe_balance(network, 0, 1, 2)
    assert result.low < 800 <= result.high


# Sprites and state channels ---------------------------------------------------


def open_channel(world, period=10):
    world.fund("alice", 100)
    keys = [public_key(7), public_key(5)]
    return world.deploy("alice", StateChannel, keys, ["alice", "bob"], [100, 0], period, value=100)


def signed(channel, version, balances, final=False):
    return [sign_state(k, channel, version, balances, final=final) for k in (7, 5)]


def test_dispute_settles_on_the_highest_version():
    world = World()
    channel = open_channel(world)
    assert world.transact("alice", channel, "settle").error == "no state was submitted"
    assert world.transact(
        "alice", channel, "submit", 2, [90, 10], signed(channel, 2, [90, 10])
    ).success
    late = world.transact("bob", channel, "submit", 5, [40, 60], signed(channel, 5, [40, 60]))
    assert late.success
    stale = world.transact("alice", channel, "submit", 2, [90, 10], signed(channel, 2, [90, 10]))
    assert stale.error == "a newer version was already submitted"
    assert world.transact("alice", channel, "settle").error == "the dispute period is not over"
    world.advance(10)
    after = world.transact("bob", channel, "submit", 6, [0, 100], signed(channel, 6, [0, 100]))
    assert after.error == "the dispute period is over"
    assert world.transact("bob", channel, "settle").success
    assert (world.balance("alice"), world.balance("bob")) == (40, 60)
    assert world.transact("bob", channel, "settle").error == "the channel is closed"


def test_cooperative_close_and_signature_checks():
    world = World()
    channel = open_channel(world)
    one_signature = [sign_state(7, channel, 1, [50, 50]), sign_state(7, channel, 1, [50, 50])]
    bad = world.transact("alice", channel, "submit", 1, [50, 50], one_signature)
    assert bad.error == "both parties must sign"
    not_final = world.transact("alice", channel, "close", 1, [50, 50], signed(channel, 1, [50, 50]))
    assert not_final.error == "both parties must sign"
    inflated = world.transact("alice", channel, "submit", 1, [90, 90], signed(channel, 1, [90, 90]))
    assert inflated.error == "balances must sum to the deposit"
    negative = world.transact(
        "alice", channel, "submit", 1, [110, -10], signed(channel, 1, [110, -10])
    )
    assert negative.error == "two non-negative balances"
    final = signed(channel, 3, [100, 0], final=True)
    assert world.transact("bob", channel, "close", 3, [100, 0], final).success
    assert world.balance("alice") == 100 and world.balance("bob") == 0
    with pytest.raises(Exception, match="deposit must equal"):
        world.deploy("x", StateChannel, [public_key(7), public_key(5)], ["a", "b"], [1, 1], 5)


def test_preimage_manager_records_the_first_publication():
    world = World()
    manager = world.deploy("deployer", PreimageManager)
    payment_hash = sha256(b"preimage")
    assert not world.view(manager, "published_by", payment_hash, 100)
    world.advance(4)
    world.transact("carol", manager, "publish", b"preimage")
    world.advance(4)
    world.transact("bob", manager, "publish", b"preimage")  # Does not move the record.
    assert world.view(manager, "published_by", payment_hash, 5)
    assert not world.view(manager, "published_by", payment_hash, 4)


def test_sprites_lock_collateral_for_constant_time():
    assert htlc_expiries(3, delta=10, final=100) == (130, 120, 110)
    assert sprites_expiries(3, delta=10, final=100) == (110, 110, 110)
    lightning = collateral_time([102, 101, 100], htlc_expiries(3, delta=10), height=0)
    sprites = collateral_time([102, 101, 100], sprites_expiries(3, delta=10), height=0)
    assert lightning == 102 * 30 + 101 * 20 + 100 * 10 and sprites == 303 * 10


# BTC Relay --------------------------------------------------------------------


def relay_world():
    genesis = mine_header(None, [b"genesis"])
    world = World()
    relay = world.deploy("deployer", BTCRelay, genesis, 8)
    return world, relay, genesis


def test_relay_follows_the_heaviest_chain_and_verifies_payments():
    world, relay, genesis = relay_world()
    payloads = [b"coinbase", b"alice pays bob 1 BTC"]
    block = mine_header(genesis, payloads)
    child = mine_header(block, [b"coinbase 2"])
    for header in (block, child):
        assert world.transact("relayer", relay, "store_header", header).success
    proof = MerkleTree(payloads).proof(1)
    assert world.view(relay, "best_height") == 2
    assert world.view(relay, "verify_transaction", payloads[1], block.hash, proof, 2)
    assert not world.view(relay, "verify_transaction", payloads[1], block.hash, proof, 3)
    assert not world.view(relay, "verify_transaction", b"forged", block.hash, proof, 1)
    assert world.view(relay, "confirmations", b"\x00" * 32) == 0
    # A shorter fork is stored but is not the main chain.
    fork = mine_header(genesis, [b"fork"], timestamp=1)
    assert world.transact("relayer", relay, "store_header", fork).success
    assert world.view(relay, "confirmations", fork.hash) == 0
    assert world.view(relay, "confirmations", genesis.hash) == 3


def test_relay_rejects_bad_headers():
    world, relay, genesis = relay_world()
    block = mine_header(genesis, [b"x"])
    world.transact("relayer", relay, "store_header", block)
    orphan = mine_header(mine_header(None, [b"elsewhere"]), [b"y"])
    cheap = mine_header(genesis, [b"z"], difficulty=2)
    unmined = mine_header(genesis, [b"w"]).__class__(
        previous_hash=genesis.hash, merkle_root=bytes(32), height=1, difficulty=30
    )
    wrong_height = mine_header(genesis, [b"v"]).__class__(
        previous_hash=genesis.hash, merkle_root=bytes(32), height=5, difficulty=8
    )
    cases = {
        orphan: "unknown parent",
        block: "header already stored",
        wrong_height: "wrong height",
        cheap: "difficulty too low",
        unmined: "proof of work missing",
    }
    for header, error in cases.items():
        assert world.transact("relayer", relay, "store_header", header).error == error
    with pytest.raises(TimeoutError):
        mine_header(None, [b"hard"], difficulty=64, max_attempts=1)


# Bridges ----------------------------------------------------------------------


def test_ronin_falls_to_five_of_nine_keys():
    world = World()
    world.fund("users", 1_000)
    bridge = world.deploy("ronin", ValidatorBridge, [public_key(k) for k in range(1, 10)], 5)
    world.transact("users", bridge, "deposit", value=1_000)
    sky_mavis = [sign_withdrawal(k, bridge, "attacker", 1_000, 0) for k in (1, 2, 3, 4)]
    repeated = sky_mavis + sky_mavis[:1]
    assert world.transact("a", bridge, "withdraw", "attacker", 1_000, 0, repeated).error == (
        "not enough validator signatures"
    )
    outsider = sky_mavis + [sign_withdrawal(42, bridge, "attacker", 1_000, 0)]
    assert not world.transact("a", bridge, "withdraw", "attacker", 1_000, 0, outsider).success
    axie_dao = sky_mavis + [sign_withdrawal(9, bridge, "attacker", 1_000, 0)]
    assert world.transact("a", bridge, "withdraw", "attacker", 1_000, 0, axie_dao).success
    assert world.balance("attacker") == 1_000 and world.balance(bridge) == 0
    replay = world.transact("a", bridge, "withdraw", "attacker", 1_000, 0, axie_dao)
    assert replay.error == "withdrawal already processed"
    with pytest.raises(Exception, match="threshold"):
        world.deploy("x", ValidatorBridge, [public_key(1)], 2)


def wormhole(check_verifier):
    world = World()
    world.fund("users", 500)
    guardians = [public_key(k) for k in range(1, 20)]
    verifier = world.deploy("wormhole", GuardianVerifier, guardians, 13)
    bridge = world.deploy("wormhole", WormholeBridge, verifier, check_verifier)
    world.transact("users", bridge, "deposit", value=500)
    return world, verifier, bridge


@pytest.mark.parametrize("check_verifier", [False, True])
def test_wormhole_trusts_a_caller_supplied_verifier(check_verifier):
    world, _, bridge = wormhole(check_verifier)
    forged = world.deploy("attacker", ForgedVerifier)
    minted = world.transact("attacker", bridge, "complete_transfer", "attacker", 500, 0, forged)
    assert minted.success is not check_verifier
    if check_verifier:
        assert minted.error == "not the genuine verifier"
    else:
        assert world.transact("attacker", bridge, "redeem", 500).success
        assert world.balance("attacker") == 500


def test_wormhole_with_genuine_guardian_signatures():
    world, verifier, bridge = wormhole(True)
    message = withdrawal_message(bridge, "bob", 200, 1)
    few = [sign_withdrawal(k, bridge, "bob", 200, 1) for k in range(1, 13)]
    assert world.transact("relayer", verifier, "verify_signatures", message, few).error == (
        "not enough guardian signatures"
    )
    unverified = world.transact("relayer", bridge, "complete_transfer", "bob", 200, 1, verifier)
    assert unverified.error == "message not verified"
    enough = [sign_withdrawal(k, bridge, "bob", 200, 1) for k in range(1, 14)]
    assert world.transact("relayer", verifier, "verify_signatures", message, enough).success
    assert world.transact("relayer", bridge, "complete_transfer", "bob", 200, 1, verifier).success
    again = world.transact("relayer", bridge, "complete_transfer", "bob", 200, 1, verifier)
    assert again.error == "transfer already completed"
    assert world.view(bridge, "wrapped_balance", "bob") == 200
    assert world.transact("bob", bridge, "redeem", 201).error == "not enough wrapped ether"
    assert world.transact("bob", bridge, "redeem", 200).success and world.balance("bob") == 200
    with pytest.raises(Exception, match="threshold"):
        world.deploy("x", GuardianVerifier, [public_key(1)], 0)
