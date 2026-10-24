"""Shared control of keys: P2SH multisig, ECDSA and threshold ECDSA, social recovery, ERC-4337."""

from itertools import combinations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blockchainkit.constants import MAX_SCRIPT_ELEMENT_SIZE
from blockchainkit.contracts import World
from blockchainkit.crypto import SECP256K1, hash256, public_key, sign
from blockchainkit.vm import p2pkh_locking
from blockchainkit.wallets import (
    GUARDIAN_DELAY,
    EcdsaSignature,
    EntryPoint,
    SmartAccount,
    SocialRecoveryWallet,
    UserOperation,
    bundle,
    ecdsa_sign,
    ecdsa_signature,
    ecdsa_verify,
    lagrange_coefficient,
    multisig_redeem_script,
    multisig_unlocking,
    p2sh_address,
    p2sh_locking,
    p2sh_unlocking,
    parse_script,
    recovery_risk,
    serialize_script,
    sign_user_operation,
    simulate_validation,
    threshold_keygen,
    threshold_sign,
    user_operation_hash,
    verify_key_share,
    verify_p2sh,
)

# Script serialization and P2SH ------------------------------------------------

KEYS = (3, 5, 7, 9)


def _redeem(m, n):
    return multisig_redeem_script(m, [public_key(k) for k in KEYS[:n]])


def test_script_serialization_round_trips():
    script = (b"", b"\x01", b"x" * 75, b"y" * 76, b"z" * 300, "OP_DUP", "OP_CHECKSIG")
    data = serialize_script(script)
    assert data[0] == 0 and data[1 + 2 + 76] == 0x4C and data[1 + 2 + 76 + 78] == 0x4D
    assert parse_script(data) == ("OP_FALSE", *script[1:])
    assert serialize_script(p2pkh_locking(public_key(3)))[0] == 0x76


@given(st.lists(st.binary(min_size=1, max_size=300), max_size=5))
def test_any_pushes_round_trip(pushes):
    assert parse_script(serialize_script(pushes)) == tuple(pushes)


def test_script_serialization_errors():
    with pytest.raises(ValueError, match="unknown opcode"):
        serialize_script(["OP_CHECKMULTISIG"])
    with pytest.raises(TypeError):
        serialize_script([1])
    with pytest.raises(ValueError, match="65,535"):
        serialize_script([bytes(70_000)])
    with pytest.raises(TypeError):
        parse_script("00")
    for bad in (b"\xff", b"\x05ab", b"\x4c", b"\x4c\x05ab", b"\x4d\x01", b"\x4d\x05\x00ab"):
        with pytest.raises(ValueError):
            parse_script(bad)


@pytest.mark.parametrize(("m", "n"), [(1, 1), (1, 3), (2, 3), (3, 3)])
def test_every_quorum_spends_and_no_smaller_set_does(m, n):
    redeem = _redeem(m, n)
    locking = p2sh_locking(redeem)
    for signers in combinations(range(n), m):
        signatures = {i: sign(b"tx", KEYS[i], nonce=100 + i) for i in signers}
        spend = p2sh_unlocking(redeem, multisig_unlocking(m, n, signatures))
        assert verify_p2sh(spend, locking, message=b"tx").valid
        assert not verify_p2sh(spend, locking, message=b"other tx").valid
    if m > 1:
        # A signature from the wrong key in a branch fails its OP_CHECKSIG.
        wrong = {i: sign(b"tx", 11, nonce=1) for i in range(m)}
        spend = p2sh_unlocking(redeem, multisig_unlocking(m, n, wrong))
        assert not verify_p2sh(spend, locking, message=b"tx").valid


def test_p2sh_two_stages():
    redeem = _redeem(2, 3)
    signatures = {0: sign(b"tx", 3, nonce=1), 1: sign(b"tx", 5, nonce=2)}
    pushes = multisig_unlocking(2, 3, signatures)
    other = _redeem(1, 3)
    # Stage one: the revealed script must hash to the locked one.
    wrong_script = verify_p2sh(p2sh_unlocking(other, pushes), p2sh_locking(redeem), message=b"tx")
    assert not wrong_script.valid and "EQUAL" not in (wrong_script.error or "OP_EQUAL")
    # Only pushes are allowed, and something must be pushed.
    assert "only pushes" in verify_p2sh(["OP_TRUE"], p2sh_locking(redeem)).error
    assert not verify_p2sh([], p2sh_locking(redeem)).valid
    assert p2sh_address(redeem).startswith("3")


def test_the_redeem_script_size_limit():
    assert len(serialize_script(_redeem(2, 3))) <= MAX_SCRIPT_ELEMENT_SIZE
    redeem = _redeem(2, 4)
    assert len(serialize_script(redeem)) > MAX_SCRIPT_ELEMENT_SIZE
    signatures = {0: sign(b"tx", 3, nonce=1), 1: sign(b"tx", 5, nonce=2)}
    spend = p2sh_unlocking(redeem, multisig_unlocking(2, 4, signatures))
    result = verify_p2sh(spend, p2sh_locking(redeem), message=b"tx")
    assert not result.valid and "520" in result.error


def test_an_unparsable_redeem_script_fails():
    garbage = b"\xff\xff"
    locking = ("OP_HASH256", hash256(garbage), "OP_EQUAL")
    result = verify_p2sh([garbage], locking)
    assert not result.valid and "unknown opcode" in result.error


def test_multisig_validation():
    with pytest.raises(ValueError, match="exceeds"):
        multisig_redeem_script(3, [public_key(3), public_key(5)])
    with pytest.raises(ValueError, match="distinct"):
        multisig_redeem_script(1, [public_key(3), public_key(3)])
    signature = sign(b"tx", 3, nonce=1)
    with pytest.raises(ValueError, match="exactly"):
        multisig_unlocking(2, 3, {0: signature})
    with pytest.raises(ValueError, match="exactly"):
        multisig_unlocking(1, 3, {3: signature})


# ECDSA and threshold ECDSA ----------------------------------------------------


def test_ecdsa_known_vector():
    # RFC 6979 nonce on secp256k1 for key 1 and "Satoshi Nakamoto", as in Trezor's tests.
    signature = ecdsa_sign(b"Satoshi Nakamoto", 1)
    assert signature == EcdsaSignature(
        0x934B1EA10A4B3C1757E2B0C017D0B6143CE3C9A7E6A4A49860D7A6AB210EE3D8,
        0x2442CE9D2B916064108014783E923EC36B49743E2FFA1C4496F01A512AAFD9E5,
    )
    assert ecdsa_verify(b"Satoshi Nakamoto", signature, SECP256K1.generator)


@given(st.integers(1, SECP256K1.order - 1), st.binary(max_size=20))
@settings(max_examples=15)
def test_ecdsa_signatures_verify_with_low_s(private, message):
    signature = ecdsa_sign(message, private)
    assert signature.s <= SECP256K1.order // 2
    assert ecdsa_verify(message, signature, public_key(private))
    assert not ecdsa_verify(message + b"!", signature, public_key(private))


def test_ecdsa_rejects_malformed_inputs():
    signature = ecdsa_sign(b"m", 7, nonce=11)
    q = public_key(7)
    n = SECP256K1.order
    assert not ecdsa_verify(b"m", EcdsaSignature(0, signature.s), q)
    assert not ecdsa_verify(b"m", EcdsaSignature(signature.r, n), q)
    assert not ecdsa_verify(b"m", signature, (1, 1))
    assert not ecdsa_verify(b"m", signature, None)
    assert not ecdsa_verify("m", signature, q)
    assert not ecdsa_verify(b"m", "not a signature", q)
    for bad in ({"private": n}, {"private": 7, "nonce": n}):
        with pytest.raises(ValueError):
            ecdsa_sign(b"m", **bad)
    r = SECP256K1.generator[0] % n
    with pytest.raises(ValueError, match="degenerate"):
        ecdsa_signature(n - r, 1, 1)  # z = -r x makes s = 0.


@pytest.mark.parametrize(("t", "n"), [(1, 1), (2, 3), (3, 5)])
def test_any_threshold_of_parties_signs(t, n):
    keys = threshold_keygen(t, n, seed=t * 10 + n)
    assert all(verify_key_share(keys, i) for i in range(1, n + 1))
    for signers in list(combinations(range(1, n + 1), t))[:4]:
        signing = threshold_sign(b"pay bob 5", keys, signers, seed=sum(signers))
        assert ecdsa_verify(b"pay bob 5", signing.signature, keys.public)
        assert signing.conversions == 2 * t * (t - 1)
    more = threshold_sign(b"m", keys, range(1, n + 1), seed=1)
    assert ecdsa_verify(b"m", more.signature, keys.public)


def test_the_joint_key_is_the_interpolated_secret():
    keys = threshold_keygen(2, 3, seed=5)
    shares = dict(keys.shares)
    secret = sum(lagrange_coefficient(i, (1, 3)) * shares[i] for i in (1, 3)) % SECP256K1.order
    assert public_key(secret) == keys.public


def test_threshold_validation_and_tampered_shares():
    keys = threshold_keygen(2, 3, seed=5)
    with pytest.raises(ValueError, match="at least 2"):
        threshold_sign(b"m", keys, [1])
    with pytest.raises(ValueError, match="distinct"):
        threshold_sign(b"m", keys, [1, 1])
    with pytest.raises(ValueError, match="distinct"):
        threshold_sign(b"m", keys, [1, 4])
    with pytest.raises(ValueError, match="no party"):
        verify_key_share(keys, 9)
    tampered = type(keys)(keys.public, 2, ((1, 1), *keys.shares[1:]), keys.commitments)
    assert not verify_key_share(tampered, 1)
    with pytest.raises(ValueError):
        threshold_keygen(3, 2)


# Social recovery --------------------------------------------------------------


def test_recovery_risk_against_brute_force():
    import itertools

    risk = recovery_risk(3, 2, lost=0.2, corrupt=0.1)
    lockout = theft = 0.0
    for states in itertools.product("lch", repeat=3):
        p = 1.0
        for s in states:
            p *= {"l": 0.2, "c": 0.1, "h": 0.7}[s]
        lockout += p * (states.count("h") < 2)
        theft += p * (states.count("c") >= 2)
    assert risk.lockout == pytest.approx(lockout) and risk.theft == pytest.approx(theft)
    with pytest.raises(ValueError, match="at most 1"):
        recovery_risk(3, 2, 0.6, 0.6)


def _wallet():
    world = World()
    world.fund("alice", 100)
    wallet = world.deploy("alice", SocialRecoveryWallet, "alice", ["g1", "g2", "g3"], 2)
    world.transact("alice", wallet, value=50)
    return world, wallet


def test_owner_spends_and_guardians_recover():
    world, wallet = _wallet()
    assert world.transact("alice", wallet, "execute", "bob", 10).success
    assert world.balance("bob") == 10
    assert world.transact("mallory", wallet, "execute", "mallory", 10).error == "only the owner"
    assert world.transact("g1", wallet, "support_recovery", "alice2").result is False
    assert world.transact("g1", wallet, "support_recovery", "alice2").result is False  # Again.
    assert world.transact("g2", wallet, "support_recovery", "alice2").result is True
    assert world.view(wallet, "owner") == "alice2"
    assert world.transact("alice2", wallet, "execute", "bob", 5).success
    assert world.transact("g1", wallet, "support_recovery", "alice2").result is False  # New epoch.
    assert world.transact("bob", wallet, "support_recovery", "bob").error == "only a guardian"


def test_a_thief_cannot_replace_the_guardians_in_time():
    world, wallet = _wallet()
    assert world.transact("alice", wallet, "propose_guardians", ["thief"], 1).success
    assert world.transact("alice", wallet, "apply_guardians").error == "the delay has not passed"
    world.transact("g1", wallet, "support_recovery", "alice2")
    world.transact("g3", wallet, "support_recovery", "alice2")
    world.advance(GUARDIAN_DELAY)
    assert (
        world.transact("alice2", wallet, "apply_guardians").error == "no guardian change is pending"
    )
    assert world.transact("alice", wallet, "apply_guardians").error == "only the owner"


def test_the_owner_changes_guardians_after_the_delay():
    world, wallet = _wallet()
    world.transact("alice", wallet, "propose_guardians", ["h1", "h2"], 2)
    world.advance(GUARDIAN_DELAY)
    assert world.transact("alice", wallet, "apply_guardians").success
    assert world.transact("g1", wallet, "support_recovery", "x").error == "only a guardian"
    world.transact("h1", wallet, "support_recovery", "alice3")
    assert world.transact("h2", wallet, "support_recovery", "alice3").result is True
    assert (
        world.transact("mallory", wallet, "propose_guardians", ["m"], 1).error == "only the owner"
    )


def test_guardian_validation():
    world = World()
    with pytest.raises(Exception, match="distinct"):
        world.deploy("alice", SocialRecoveryWallet, "alice", ["g", "g"], 1)
    with pytest.raises(Exception, match="between 1 and n"):
        world.deploy("alice", SocialRecoveryWallet, "alice", ["g"], 2)


# ERC-4337 ---------------------------------------------------------------------


def _accounts(deposit=0):
    world = World()
    entry = world.deploy("deployer", EntryPoint)
    account = world.deploy("deployer", SmartAccount, entry, public_key(7))
    world.fund("alice", 1_000)
    world.transact("alice", account, value=100)
    if deposit:
        world.transact("alice", entry, "deposit_to", account, value=deposit)
    return world, entry, account


def _op(account, nonce, function, *args, fee=2, key=7, entry=None):
    return sign_user_operation(UserOperation(account, nonce, function, args, fee), key, entry)


def test_an_operation_pays_its_fee_and_runs():
    world, entry, account = _accounts()
    op = _op(account, 0, "execute", "bob", 10, entry=entry)
    receipt = world.transact("bundler", entry, "handle_ops", [op], "bundler")
    assert receipt.success and receipt.result == (True,)
    assert world.balance("bob") == 10 and world.balance("bundler") == 2
    assert world.balance(account) == 88 and world.view(entry, "balance_of", account) == 0
    assert world.view(account, "nonce") == 1
    assert [e.name for e in receipt.events].count("UserOperationEvent") == 1


def test_fees_come_from_an_existing_deposit():
    world, entry, account = _accounts(deposit=5)
    op = _op(account, 0, "execute", "bob", 10, entry=entry)
    world.transact("bundler", entry, "handle_ops", [op], "bundler")
    assert world.view(entry, "balance_of", account) == 3 and world.balance(account) == 90
    world.transact("alice", entry, value=4)  # A plain payment credits the sender.
    assert world.view(entry, "balance_of", "alice") == 4


def test_key_rotation_and_batches():
    world, entry, account = _accounts()
    rotate = _op(account, 0, "rotate_owner", public_key(9), entry=entry)
    assert world.transact("bundler", entry, "handle_ops", [rotate], "bundler").success
    stale = _op(account, 1, "execute", "bob", 1, entry=entry)
    assert not simulate_validation(world, entry, stale)
    batch = _op(account, 1, "execute_batch", [("bob", 1), ("carol", 2)], key=9, entry=entry)
    failing = _op(account, 2, "execute", "bob", 10_000, key=9, entry=entry)
    receipt = world.transact("bundler", entry, "handle_ops", [batch, failing], "bundler")
    assert receipt.result == (True, False)  # The failed execution still paid its fee.
    assert world.balance("carol") == 2 and world.balance("bundler") == 6


def test_validation_failures_revert_the_bundle():
    world, entry, account = _accounts()
    good = _op(account, 0, "execute", "bob", 1, entry=entry)
    replay = world.transact("bundler", entry, "handle_ops", [good, good], "bundler")
    assert not replay.success and "bad nonce" in replay.error
    unsigned = UserOperation(account, 0, "execute", ("bob", 1), 1)
    assert "bad signature" in world.transact("b", entry, "handle_ops", [unsigned], "b").error
    other_chain = UserOperation(account, 0, "execute", ("bob", 1), 1)
    digest = user_operation_hash(other_chain, entry, chain_id="another-chain")
    signed = UserOperation(account, 0, "execute", ("bob", 1), 1, sign(digest, 7, nonce=5))
    assert not simulate_validation(world, entry, signed)
    poor = _op(account, 0, "execute", "bob", 1, fee=10_000, entry=entry)
    assert not simulate_validation(world, entry, poor)
    assert bundle(world, entry, [good, signed, poor]) == (good,)


def test_only_the_entry_point_drives_the_account():
    world, entry, account = _accounts()
    assert world.transact("alice", account, "execute", "alice", 50).error == "only the EntryPoint"
    op = _op(account, 0, "execute", "bob", 1, entry=entry)
    digest = user_operation_hash(op, entry)
    receipt = world.transact("alice", account, "validate_user_operation", op, digest, 0)
    assert receipt.error == "only the EntryPoint"


class _Stingy(SmartAccount):
    """An account that validates but never pays its fee."""

    def validate_user_operation(self, operation, digest, missing):
        self._only_entry_point()
        self.write("nonce", operation.nonce + 1)


def test_an_account_that_does_not_pay_is_rejected():
    world = World()
    entry = world.deploy("deployer", EntryPoint)
    account = world.deploy("deployer", _Stingy, entry, public_key(7))
    op = _op(account, 0, "execute", "bob", 0, entry=entry)
    receipt = world.transact("bundler", entry, "handle_ops", [op], "bundler")
    assert receipt.error == "the account did not pay its fee"
