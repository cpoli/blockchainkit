"""Scam contracts: honeypots, deceptive verified sources, ICOs, rug pulls, and phishing."""

import pytest

from blockchainkit.contracts import ERC20, ContractError, EIP1967Proxy, World
from blockchainkit.crypto import sha256
from blockchainkit.economics import ConstantProductPool
from blockchainkit.fraud import (
    UNLIMITED,
    DividendDistributor,
    Drainer,
    ForTest,
    GiftBox,
    GuessNumber,
    HiddenMintToken,
    KingOfTheHill,
    Log,
    MultiplicatorX3,
    PrivateBank,
    Relay,
    SeizableToken,
    SellBlockToken,
    TokenSale,
    TrapLog,
    UpgradeableToken,
    allowance_exposure,
    effective_code,
    explorer_view,
    open_approvals,
    sell_test,
    verify_source,
)


@pytest.fixture
def world():
    world = World()
    world.fund("creator", 10_000)
    world.fund("victim", 10_000)
    return world


def _bait(world, code, *args):
    trap = world.deploy("creator", code, *args)
    world.transact("creator", trap, value=1_000)
    return trap


# Honeypots: EVM semantics -----------------------------------------------------


def test_balance_disorder_keeps_the_deposit(world):
    trap = _bait(world, MultiplicatorX3)
    assert world.transact("victim", trap, "multiplicate", "victim", value=1_500).success
    assert world.balance("victim") == 8_500 and world.balance(trap) == 2_500
    empty = world.deploy("creator", MultiplicatorX3)
    assert not world.transact("victim", empty, "multiplicate", "victim", value=10).success
    assert world.transact("victim", trap, "withdraw").error == "only the owner"
    assert world.transact("creator", trap, "withdraw").success and world.balance(trap) == 0


def test_hidden_state_update_closes_the_box_unseen(world):
    box = world.deploy("creator", GiftBox, 1_000)
    relay = world.deploy("creator", Relay)
    receipts = [
        world.transact("creator", relay, "forward", box, "set_pass", sha256(b"pw"), value=1_000),
        world.transact("creator", relay, "forward", box, "pass_has_been_set", sha256(b"pw")),
    ]
    assert [(r.function, r.value) for r in explorer_view(receipts, box)] == [("set_pass", 1_000)]
    assert world.read(box, "closed") == 1
    world.transact("victim", box, "set_pass", sha256(b"mine"), value=1_000)
    world.transact("victim", box, "get_gift", b"mine")
    assert world.balance("victim") == 9_000 and world.balance(box) == 2_000
    assert world.transact("victim", relay, "forward", box, "get_gift", b"pw").error == (
        "only the owner"
    )
    assert world.transact("creator", box, "withdraw").success and world.balance(box) == 0


def test_an_open_gift_box_pays_the_password_holder(world):
    box = world.deploy("creator", GiftBox, 1_000)
    world.transact("victim", box, "set_pass", sha256(b"mine"), value=999)  # Too little.
    assert world.read(box, "hash_pass") == 0
    world.transact("victim", box, "set_pass", sha256(b"mine"), value=1_000)
    world.transact("creator", box, "pass_has_been_set", sha256(b"mine"))  # Not the setter.
    assert world.read(box, "closed") == 0
    world.transact("victim", box, "get_gift", b"mine")
    assert world.balance("victim") == 10_000


def test_straw_man_logger_reverts_every_cash_out(world):
    log = world.deploy("creator", TrapLog)
    bank = world.deploy("creator", PrivateBank, log)
    world.transact("victim", bank, "deposit", value=50)  # Below the minimum: ignored.
    assert world.view(bank, "balance_of", "victim") == 0
    world.transact("victim", bank, "deposit", value=1_000)
    assert world.view(bank, "balance_of", "victim") == 1_000
    assert not world.transact("victim", bank, "cash_out", 1_000).success
    assert world.balance("victim") == 8_950 and world.code(log) is TrapLog
    world.transact("creator", bank, "deposit", value=100)
    assert world.transact("creator", bank, "cash_out", 100).success
    assert world.transact("victim", bank, "cash_out", 5_000).success  # Over balance: no-op.


def test_the_logger_the_source_shows_would_let_the_victim_out(world):
    bank = world.deploy("creator", PrivateBank, world.deploy("creator", Log))
    world.transact("victim", bank, "deposit", value=1_000)
    assert world.transact("victim", bank, "cash_out", 1_000).success
    assert world.balance("victim") == 10_000


# Honeypots: Solidity quirks, by their effect ------------------------------------


def test_inheritance_disorder(world):
    hill = _bait(world, KingOfTheHill)
    world.transact("victim", hill, value=500)  # Not above the jackpot.
    assert world.view(hill, "owner") == "creator"
    world.transact("victim", hill, value=2_000)
    assert world.view(hill, "owner") == "victim"
    assert world.transact("victim", hill, "take_all").error == "only the owner"
    assert world.transact("creator", hill, "take_all").success
    assert world.balance("victim") == 7_500


def test_uninitialised_struct_overwrites_the_secret(world):
    game = _bait(world, GuessNumber, 7, 100)
    secret = world.read(game, "number")
    assert world.transact("victim", game, "guess", secret, value=100).success
    assert world.balance("victim") == 9_900 and world.read(game, "number") == "victim"
    assert world.transact("victim", game, "guess", 11, value=100).error == "bad bet"
    with pytest.raises(ContractError):
        world.deploy("creator", GuessNumber, 11)


def test_type_deduction_overflow_caps_the_payout(world):
    trap = _bait(world, ForTest, 1_000)
    world.transact("victim", trap, "test", value=2_000)
    assert world.balance("victim") == 10_000 - 2_000 + 254
    world.transact("victim", trap, "test", value=500)  # Below the threshold: kept.
    assert world.balance("victim") == 8_254 - 500
    small = _bait(world, ForTest, 10)
    world.transact("victim", small, "test", value=20)  # 2 * 20 < 128: the loop ends first.
    assert world.balance("victim") == 7_754 - 20 + 78


def test_skipped_empty_string_pays_the_owner(world):
    fund = world.deploy("creator", DividendDistributor)
    world.transact("victim", fund, "invest", value=1_000)
    assert world.view(fund, "investment_of", "victim") == 1_000
    receipt = world.transact("victim", fund, "divest", 1_000)
    assert receipt.success and receipt.events[0].fields["target"] == "creator"
    assert world.balance("victim") == 9_000 and world.balance("creator") == 11_000
    assert not world.transact("victim", fund, "divest", 1).success
    assert not world.transact("victim", fund, "invest").success


# Verified source --------------------------------------------------------------


def test_a_verified_proxy_can_change_what_it_runs():
    world = World()
    implementation = world.deploy("dev", UpgradeableToken)
    proxy = world.deploy("dev", EIP1967Proxy, implementation)
    assert effective_code(world, proxy) is UpgradeableToken
    world.transact("dev", proxy, "initialize", 1_000)
    assert not world.transact("dev", proxy, "initialize", 1_000).success
    world.transact("dev", proxy, "transfer", "buyer", 400)
    assert not world.transact("dev", proxy, "seize", "buyer", 400).success
    world.transact("dev", proxy, "upgrade_to", world.deploy("dev", SeizableToken))
    assert (
        verify_source(world, proxy, EIP1967Proxy) and effective_code(world, proxy) is SeizableToken
    )
    assert world.transact("buyer", proxy, "seize", "dev", 1).error == "only the owner"
    assert world.transact("dev", proxy, "seize", "buyer", 400).success
    assert world.view(proxy, "balance_of", "buyer") == 0
    assert world.view(proxy, "balance_of", "dev") == 1_000
    assert not world.transact("dev", proxy, "seize", "buyer", 1).success
    assert not world.transact("buyer", proxy, "transfer", "dev", 1).success
    assert effective_code(world, implementation) is UpgradeableToken
    assert effective_code(world, "nobody") is None


def test_a_proxy_without_implementation_runs_nothing():
    world = World()
    assert effective_code(world, world.deploy("dev", EIP1967Proxy, "")) is None


def test_upgradeable_token_validates_supply():
    world = World()
    proxy = world.deploy("dev", EIP1967Proxy, world.deploy("dev", UpgradeableToken))
    assert world.transact("dev", proxy, "initialize", 0).error == "supply must be positive"


# Token sales ------------------------------------------------------------------


def _sale(tap):
    world = World()
    for k in range(4):
        world.fund(f"b{k}", 1_000)
    sale = world.deploy("team", TokenSale, tap)
    for k in range(4):
        world.transact(f"b{k}", sale, "buy", value=1_000)
    world.advance(seconds=100)
    return world, sale


def test_an_ico_without_a_tap_can_be_emptied_at_once():
    world, sale = _sale(0)
    assert world.view(sale, "available") == 4_000 and world.view(sale, "tokens_of", "b0") == 1_000
    assert world.transact("team", sale, "withdraw", 4_000).success
    assert world.transact("b0", sale, "vote_refund").error == "this sale has no refund vote"
    assert world.transact("b0", sale, "withdraw", 1).error == "only the team"


def test_a_daico_tap_and_refund_vote_protect_contributors():
    world, sale = _sale(1)
    assert world.view(sale, "available") == 100
    assert world.transact("team", sale, "withdraw", 101).error == "above the tap"
    assert world.transact("team", sale, "withdraw", 100).success
    assert world.transact("team", sale, "vote_refund").error == "cannot vote"
    assert world.transact("b0", sale, "refund").error == "no refund was voted"
    world.transact("b0", sale, "vote_refund")
    assert world.transact("b0", sale, "vote_refund").error == "cannot vote"
    world.transact("b1", sale, "vote_refund")
    assert world.read(sale, "refunding") == 0  # Exactly half is not a majority.
    world.transact("b2", sale, "vote_refund")
    assert world.view(sale, "available") == 0
    assert world.transact("b3", sale, "vote_refund").success  # Already refunding.
    world.fund("b3", 1)
    assert world.transact("b3", sale, "buy", value=1).error == "the sale is refunding"
    for k in range(4):
        assert world.transact(f"b{k}", sale, "refund").success
    assert [world.balance(f"b{k}") for k in range(4)] == [975, 975, 975, 976]
    assert world.transact("b0", sale, "refund").error == "nothing to refund"


def test_token_sale_validation():
    world, sale = _sale(1)
    world.advance(seconds=10**6)
    assert world.view(sale, "available") == 4_000  # Capped by the balance.
    assert not world.transact("b0", sale, "buy").success
    with pytest.raises(ContractError):
        world.deploy("team", TokenSale, -1)


# Rug pulls --------------------------------------------------------------------


def _market(code):
    world = World()
    usd = world.deploy("whale", ERC20, 10**7, name="USD")
    token = world.deploy("dev", code, 10**6, name="SQUID")
    for account, amount in (("dev", 10_000), ("victim", 1_000)):
        world.transact("whale", usd, "transfer", account, amount)
    pool = world.deploy("dev", ConstantProductPool, token, usd)
    if code is SellBlockToken:
        world.transact("dev", token, "set_pool", pool)
    for asset in (token, usd):
        world.transact("dev", asset, "approve", pool, 10**6)
    world.transact("dev", pool, "add_liquidity", 100_000, 10_000)
    return world, token, usd, pool


def test_a_sell_block_lets_victims_buy_but_not_sell():
    world, token, usd, pool = _market(SellBlockToken)
    assert not sell_test(world, pool, token, usd, "victim", 100)
    assert world.view(usd, "balance_of", "victim") == 1_000  # The test ran on a fork.
    world.transact("victim", usd, "approve", pool, 1_000)
    bought = world.transact("victim", pool, "swap", usd, 1_000).result
    world.transact("victim", token, "approve", pool, bought)
    assert world.transact("victim", pool, "swap", token, bought).error == (
        "anti-dump: selling is not enabled"
    )
    assert world.transact("victim", token, "set_pool", "x").error == "only the owner"
    assert world.transact("dev", pool, "swap", token, 1_000).success


def test_a_fair_token_passes_the_sell_test_and_an_empty_pool_fails_it():
    world, token, usd, pool = _market(ERC20)
    assert sell_test(world, pool, token, usd, "victim", 100)
    assert not sell_test(world, pool, token, usd, "victim", 10**9)  # Cannot even buy.


def test_a_hidden_mint_and_dump_drains_the_pool():
    world, token, usd, pool = _market(HiddenMintToken)
    world.transact("victim", usd, "approve", pool, 1_000)
    world.transact("victim", pool, "swap", usd, 1_000)
    assert world.transact("victim", token, "sync_rewards", 1).error == "only the reward manager"
    assert not world.transact("dev", token, "sync_rewards", 0).success
    world.transact("dev", token, "sync_rewards", 10**8)
    assert world.view(token, "total_supply") == 10**6 + 10**8
    world.transact("dev", token, "approve", pool, 10**8)
    world.transact("dev", pool, "swap", token, 10**8)
    assert world.view(pool, "reserves")[1] < 200


# Approval phishing ------------------------------------------------------------


def test_an_unlimited_approval_drains_the_wallet_until_revoked():
    world = World()
    token = world.deploy("issuer", ERC20, 1_000)
    other = world.deploy("issuer", ERC20, 1_000)
    world.transact("issuer", token, "transfer", "victim", 500)
    world.transact("issuer", other, "transfer", "victim", 300)
    drainer = world.deploy("attacker", Drainer)
    receipts = [
        world.transact("victim", token, "approve", drainer, UNLIMITED),
        world.transact("victim", token, "approve", "dex", 100),
        world.transact("victim", other, "approve", drainer, 50),
        world.transact("issuer", token, "approve", drainer, 5),
    ]
    approvals = open_approvals(receipts, "victim")
    assert approvals == {(token, drainer): UNLIMITED, (token, "dex"): 100, (other, drainer): 50}
    assert allowance_exposure(world, "victim", approvals) == 550
    assert world.transact("victim", drainer, "sweep", token, "victim").error == "only the attacker"
    assert world.transact("attacker", drainer, "sweep", token, "victim").result == 500
    assert world.view(token, "balance_of", "attacker") == 500
    assert world.transact("attacker", drainer, "sweep", token, "victim").result == 0
    receipts.append(world.transact("victim", other, "approve", drainer, 0))
    assert (other, drainer) not in open_approvals(receipts, "victim")
    assert world.transact("attacker", drainer, "sweep", other, "victim").result == 0
