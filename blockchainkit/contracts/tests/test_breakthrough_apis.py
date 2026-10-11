"""APIs behind the contracts history: each breakthrough's mechanism, attack and fix."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk
from blockchainkit.contracts import (
    ERC20,
    ERC721,
    AirdropPhisher,
    BlockhashLottery,
    BoxV1,
    BoxV2,
    BoxV2Reordered,
    CheckedKingOfTheEther,
    CommitRevealLottery,
    Contract,
    ContractWallet,
    EIP1967Proxy,
    Factory,
    FlashLender,
    Governance,
    GovernanceAttacker,
    GovernMental,
    KingOfTheEther,
    LotteryPredictor,
    Mint,
    NaiveProxy,
    NFTVault,
    OriginWallet,
    PatchedWalletLibrary,
    PullKingOfTheEther,
    RicardianToken,
    SenderWallet,
    Usurper,
    VotesToken,
    Wallet,
    WalletLibrary,
    World,
    approve_action,
    commitment,
    create2_address,
    ensures,
    requires,
    ricardian_contract,
    ricardian_digest,
    threshold_met,
    verify_ricardian,
)
from blockchainkit.contracts.systems.payments import GOVERNMENTAL_TIMEOUT
from blockchainkit.contracts.systems.proxies import IMPLEMENTATION_SLOT
from blockchainkit.contracts.systems.world import GAS_COSTS
from blockchainkit.crypto import public_key

# Design by contract ---------------------------------------------------------


class Account(Contract):
    layout = ("balance",)

    def constructor(self, balance):
        self.write("balance", balance)

    @requires(lambda self, amount: 0 < amount <= self.read("balance"), "bad amount")
    @ensures(lambda self, old, result, amount: self.read("balance") == old("balance") - amount)
    def withdraw(self, amount):
        # A bug: large withdrawals are charged one unit too little.
        self.write("balance", self.read("balance") - amount + (amount > 50))
        return amount


def test_pre_and_postconditions_revert_where_the_fault_is():
    world = World()
    account = world.deploy("alice", Account, 100)
    assert world.transact("alice", account, "withdraw", 10).result == 10
    assert world.transact("alice", account, "withdraw", 0).error == "bad amount"
    assert world.transact("alice", account, "withdraw", 91).error == "bad amount"
    assert world.transact("alice", account, "withdraw", 60).error == "postcondition failed"
    assert world.read(account, "balance") == 90


def test_contract_checks_cost_no_gas():
    world = World()
    account = world.deploy("alice", Account, 100)
    used = world.transact("alice", account, "withdraw", 10).gas_used
    assert used == GAS_COSTS["transaction"] + GAS_COSTS["read"] + GAS_COSTS["write"]


# Ricardian contracts --------------------------------------------------------


def test_ricardian_contracts_bind_prose_parameters_and_issuer():
    terms = "The issuer pays {coupon}% a year on {supply} bonds."
    bond = ricardian_contract(terms, {"coupon": 5, "supply": 1000}, issuer_key=7)
    assert bond.rendered == "The issuer pays 5% a year on 1000 bonds."
    assert verify_ricardian(bond) and bond.issuer == public_key(7)
    edited = ricardian_digest(terms.replace("pays", "may pay"), bond.parameters)
    assert edited != bond.digest
    forged = type(bond)(
        bond.text, {"coupon": 9, "supply": 1000}, bond.issuer, bond.signature, bond.digest
    )
    assert not verify_ricardian(forged)
    other = ricardian_contract(terms, bond.parameters, issuer_key=11)
    assert not verify_ricardian(
        type(bond)(
            *[getattr(bond, f) for f in ("text", "parameters", "issuer")],
            other.signature,
            bond.digest,
        )
    )
    with pytest.raises(KeyError):
        ricardian_digest("{missing}", {})
    with pytest.raises(TypeError):
        ricardian_digest(b"bytes", {})
    with pytest.raises(TypeError):
        ricardian_digest("x", {"rate": 1.5})


def test_ricardian_token_payments_cite_the_terms():
    bond = ricardian_contract("Bond of {supply} units.", {"supply": 500}, issuer_key=7)
    world = World()
    token = world.deploy("issuer", RicardianToken, bond.identifier, 500)
    assert world.view(token, "terms") == bond.identifier
    assert world.transact("issuer", token, "transfer_under", bond.identifier, "bob", 5).success
    stale = world.transact("issuer", token, "transfer_under", "00" * 32, "bob", 5)
    assert stale.error == "payment cites different terms"
    assert world.view(token, "balance_of", "bob") == 5


# Capabilities ---------------------------------------------------------------


def test_purses_carry_exactly_their_authority():
    mint = Mint("carol-bucks")
    alice, bob = mint.make_purse(100), mint.make_purse(0)
    payment = alice.sprout()
    payment.deposit(10, alice)
    bob.deposit(10, payment)  # Bob can take what he was handed...
    with pytest.raises(ValueError, match="insufficient"):
        bob.deposit(1, payment)  # ...and nothing more.
    assert (alice.balance, bob.balance, payment.balance) == (90, 10, 0)
    assert bob.currency == "carol-bucks"
    counterfeit = Mint("carol-bucks").make_purse(1_000)
    with pytest.raises(ValueError, match="not a purse"):
        bob.deposit(10, counterfeit)
    with pytest.raises(ValueError, match="not a purse"):
        bob.deposit(10, "alice")
    with pytest.raises(TypeError):
        mint.make_purse(1.0)


def test_tx_origin_makes_a_confused_deputy():
    for wallet_code, stolen in ((OriginWallet, 100), (SenderWallet, 0)):
        world = World()
        world.fund("alice", 100)
        wallet = world.deploy("alice", wallet_code)
        world.transact("alice", wallet, value=100)
        phisher = world.deploy("mallory", AirdropPhisher)
        world.transact("alice", phisher, "claim_airdrop", wallet)
        assert world.balance("mallory") == stolen
        assert world.transact("alice", wallet, "withdraw", "alice", 100 - stolen).success


# Tokens ---------------------------------------------------------------------


def test_erc20_basics_and_the_invariant():
    world = World()
    token = world.deploy("alice", ERC20, 1_000)
    assert world.transact("alice", token, "transfer", "bob", 300).result is True
    assert world.transact("bob", token, "transfer", "carol", 301).error == "insufficient balance"
    assert world.transact("bob", token, "transfer", "carol", -1).error.startswith("amount")
    assert world.view(token, "total_supply") == 1_000
    receipt = world.transact("bob", token, "transfer", "carol", 1)
    assert [event.name for event in receipt.events] == ["Transfer"]
    assert receipt.events[0].fields["amount"] == 1


def test_the_approve_race_and_relative_allowances():
    world = World()
    token = world.deploy("alice", ERC20, 1_000)
    world.transact("alice", token, "approve", "bob", 100)
    # Bob sees Alice's approve(bob, 50) pending and gets his spend in first.
    world.transact("bob", token, "transfer_from", "alice", "bob", 100)
    world.transact("alice", token, "approve", "bob", 50)
    world.transact("bob", token, "transfer_from", "alice", "bob", 50)
    assert world.view(token, "balance_of", "bob") == 150
    world.transact("alice", token, "approve", "carol", 100)
    world.transact("carol", token, "transfer_from", "alice", "carol", 100)
    refused = world.transact("alice", token, "decrease_allowance", "carol", 50)
    assert refused.error == "allowance below zero"
    assert world.transact("alice", token, "increase_allowance", "carol", 7).success
    assert world.transact("alice", token, "decrease_allowance", "carol", 2).success
    assert world.view(token, "allowance", "alice", "carol") == 5
    over = world.transact("carol", token, "transfer_from", "alice", "carol", 6)
    assert over.error == "allowance exceeded"


@given(
    st.lists(
        st.tuples(st.sampled_from("abc"), st.sampled_from("abc"), st.integers(0, 60)), max_size=12
    )
)
def test_erc20_conserves_supply(transfers):
    world = World()
    token = world.deploy("a", ERC20, 100)
    for sender, to, amount in transfers:
        world.transact(sender, token, "transfer", to, amount)
    assert sum(world.view(token, "balance_of", who) for who in "abc") == 100


def test_erc721_ownership_and_safe_transfers():
    world = World()
    nft = world.deploy("artist", ERC721)
    for token_id in (1, 2, 3):
        assert world.transact("artist", nft, "mint", "alice", token_id).success
    assert world.transact("mallory", nft, "mint", "mallory", 9).error == "only the minter mints"
    assert world.transact("artist", nft, "mint", "bob", 1).error == "token already exists"
    assert world.view(nft, "balance_of", "alice") == 3
    with pytest.raises(bk.contracts.ContractError, match="no such token"):
        world.view(nft, "owner_of", 9)
    token_contract = world.deploy("x", ERC20, 1)
    vault = world.deploy("alice", NFTVault)
    assert world.transact("alice", nft, "transfer_from", "alice", token_contract, 1).success
    assert world.view(nft, "owner_of", 1) == token_contract  # Stuck for good.
    refused = world.transact("alice", nft, "safe_transfer_from", "alice", token_contract, 2)
    assert "on_erc721_received" in refused.error
    assert world.transact("alice", nft, "safe_transfer_from", "alice", vault, 2).success
    assert world.transact("alice", nft, "safe_transfer_from", "alice", "bob", 3).success
    assert world.transact("mallory", vault, "send_token", nft, "mallory", 2).error
    assert world.transact("alice", vault, "send_token", nft, "carol", 2).success
    assert world.view(nft, "owner_of", 2) == "carol"
    assert world.transact("carol", nft, "approve", "dave", 2).success
    assert world.transact("bob", nft, "approve", "dave", 2).error == "only the owner approves"
    assert world.transact("eve", nft, "transfer_from", "carol", "eve", 2).error == "not authorized"
    assert world.transact("dave", nft, "transfer_from", "bob", "dave", 2).error == "not the owner"
    assert world.transact("dave", nft, "transfer_from", "carol", "dave", 2).success


def test_a_recipient_that_answers_wrongly_is_refused():
    class Confused(Contract):
        layout = ()

        def on_erc721_received(self, operator, owner, token_id):
            return "yes"

    world = World()
    nft = world.deploy("artist", ERC721)
    world.transact("artist", nft, "mint", "alice", 1)
    confused = world.deploy("x", Confused)
    receipt = world.transact("alice", nft, "safe_transfer_from", "alice", confused, 1)
    assert receipt.error == "recipient rejected the token"


# Payments -------------------------------------------------------------------


def _throne(code):
    world = World()
    for account in ("owner", "alice", "bob"):
        world.fund(account, 10_000)
    throne = world.deploy("owner", code, 100)
    wallet = world.deploy("alice", ContractWallet)
    world.fund(wallet, 1_000)
    claim = world.transact("alice", wallet, "forward", throne, "claim_throne", 100)
    return world, throne, wallet, claim


def test_king_of_the_ether_unchecked_send_loses_the_compensation():
    world, throne, wallet, claim = _throne(KingOfTheEther)
    assert claim.success and world.view(throne, "king") == wallet
    receipt = world.transact("bob", throne, "claim_throne", value=150)
    assert receipt.success and world.view(throne, "king") == "bob"
    assert world.balance(wallet) == 900  # Its 148.5 never arrived...
    assert world.balance(throne) == 1 + 150  # ...and stayed with the commission.
    assert world.view(throne, "price") == 225 and world.balance("owner") == 10_000 + 99
    assert world.transact("bob", throne, "claim_throne", value=1).error == "pay at least the price"
    failed = [call for call in receipt.calls if not call.ok]
    assert failed[0].error == "out of gas"
    assert world.transact("bob", wallet, "forward", throne, "claim_throne", 1).error


def test_checked_sends_let_one_king_block_the_throne():
    world, throne, wallet, _ = _throne(CheckedKingOfTheEther)
    blocked = world.transact("bob", throne, "claim_throne", value=150)
    assert blocked.error == "payment to the deposed king failed"
    usurper = world.deploy("bob", Usurper)
    world2 = World()
    world2.fund("mallory", 1_000)
    world2.fund("carol", 1_000)
    throne2 = world2.deploy("owner", CheckedKingOfTheEther, 10)
    usurper = world2.deploy("mallory", Usurper)
    assert world2.transact("mallory", usurper, "claim", throne2, value=10).success
    assert world2.transact("carol", throne2, "claim_throne", value=500).error
    assert world2.transact("carol", usurper, value=1).error == "no refunds"


def test_pull_payments_let_every_king_withdraw():
    world, throne, wallet, _ = _throne(PullKingOfTheEther)
    assert world.transact("bob", throne, "claim_throne", value=150).success
    assert world.view(throne, "owed", wallet) == 148
    assert world.transact("alice", wallet, "forward", throne, "withdraw", 0).success
    assert world.balance(wallet) == 900 + 148
    assert world.transact("alice", wallet, "forward", throne, "withdraw", 0).error


def test_governmental_payout_runs_out_of_block_gas():
    results = {}
    for lazy in (False, True):
        world = World(block_gas_limit=4_712_388)
        game = world.deploy("operator", GovernMental, lazy)
        assert world.transact("p", game, "invest").error == "invest something"
        assert world.transact("p", game, "payout").error == "too early"
        world.advance(seconds=GOVERNMENTAL_TIMEOUT)
        assert world.transact("p", game, "payout").error == "no investors"
        for index in range(1_000):
            world.fund(f"p{index}", 1)
            world.transact(f"p{index}", game, "invest", value=1)
        assert world.view(game, "creditors") == 1_000
        assert world.transact("anyone", game, "payout").error == "too early"
        world.advance(seconds=GOVERNMENTAL_TIMEOUT)
        results[lazy] = world.transact("anyone", game, "payout")
        assert world.balance("p999") == (1_000 if lazy else 0)
    assert results[False].error == "out of gas"
    assert results[True].success and results[True].gas_used < 100_000
    small = World()
    game = small.deploy("operator", GovernMental)
    for player in ("a", "b"):
        small.fund(player, 3)
        small.transact(player, game, "invest", value=3)
    small.advance(seconds=GOVERNMENTAL_TIMEOUT)
    assert small.transact("anyone", game, "payout").success  # A short list still clears.
    assert small.balance("b") == 6 and small.view(game, "creditors") == 0


# Randomness -----------------------------------------------------------------


def test_block_hash_lotteries_are_predictable():
    world = World(seed=3)
    world.fund("house", 1_000)
    world.fund("eve", 10)
    lottery = world.deploy("house", BlockhashLottery, 1, value=500)
    predictor = world.deploy("eve", LotteryPredictor)
    world.advance()
    assert world.transact("eve", predictor, "attack", lottery, 1, value=1).result is True
    assert world.balance("eve") == 510
    world.fund("fred", 10)
    drawn = world.blockhash(world.block_number - 1) % 10
    assert world.transact("fred", lottery, "play", (drawn + 1) % 10, value=1).result is False
    assert world.transact("fred", lottery, "play", drawn, value=2).error == "pay exactly the stake"


def test_commit_reveal_lottery():
    world = World()
    secrets = {"a": (11, 1), "b": (22, 2), "c": (33, 3)}
    for player in secrets:
        world.fund(player, 10)
    lottery = world.deploy("house", CommitRevealLottery, 10, 3, 3)
    assert world.transact("a", lottery, "settle").error == "reveal phase not over"
    for player, (secret, salt) in secrets.items():
        digest = commitment(player, secret, salt)
        assert world.transact(player, lottery, "commit", digest, value=10).success
    assert world.transact("a", lottery, "commit", 5, value=10).error
    assert world.transact("a", lottery, "reveal", 11, 1).error == "not the reveal phase"
    world.advance(4)
    world.fund("d", 10)
    assert world.transact("d", lottery, "commit", 5, value=10).error == "commit phase is over"
    assert world.transact("a", lottery, "reveal", 12, 1).error == "wrong secret"
    for player, (secret, salt) in secrets.items():
        assert world.transact(player, lottery, "reveal", secret, salt).success
    assert world.transact("a", lottery, "reveal", 11, 1).error == "wrong secret"
    world.advance(3)
    winner = world.transact("anyone", lottery, "settle").result
    assert winner == "abc"[(11 ^ 22 ^ 33) % 3] and world.balance(winner) == 30
    empty = world.deploy("house", CommitRevealLottery, 10, 0, 0)
    world.advance()
    assert world.transact("x", empty, "settle").error == "no players"
    assert world.transact("x", empty, "commit", 1, value=0).error


# Parity wallets -------------------------------------------------------------

KEYS = {"alice": 11, "bob": 13}
OWNERS = [public_key(key) for key in KEYS.values()]
ATTACKER = 99


def _wallet(library_code):
    world = World()
    library = world.deploy("parity", library_code)
    wallet = world.deploy("alice", Wallet, library, OWNERS, 2)
    world.fund("alice", 1_000)
    world.transact("alice", wallet, value=1_000)
    return world, library, wallet


def _approvals(keys, wallet, nonce, action, *params):
    return [approve_action(key, wallet, nonce, action, *params) for key in keys]


def test_multisig_needs_enough_owner_signatures():
    world, _, wallet = _wallet(WalletLibrary)
    one = _approvals([11], wallet, 0, "execute", "carol", 10)
    assert world.transact("x", wallet, "execute", "carol", 10, one).error
    both = _approvals([11, 13], wallet, 0, "execute", "carol", 10)
    assert world.transact("x", wallet, "execute", "carol", 10, both).success
    assert world.balance("carol") == 10 and world.view(wallet, "nonce") == 1
    replay = world.transact("x", wallet, "execute", "carol", 10, both)
    assert replay.error == "not enough owner signatures"
    duplicated = _approvals([11, 11], wallet, 1, "execute", "carol", 10)
    assert world.transact("x", wallet, "execute", "carol", 10, duplicated).error
    outsider = _approvals([11, 17], wallet, 1, "execute", "carol", 10)
    assert world.transact("x", wallet, "execute", "carol", 10, outsider).error
    assert not threshold_met(5, 0) and threshold_met(2, 2)
    with pytest.raises(bk.contracts.ContractError, match="threshold"):
        world.deploy("alice", Wallet, world.deploy("p", WalletLibrary), OWNERS, 3)


def test_parity_july_2017_reinitialization():
    world, _, wallet = _wallet(WalletLibrary)
    takeover = world.transact("attacker", wallet, "init_wallet", [public_key(ATTACKER)], 1)
    assert takeover.success
    assert [call.kind for call in takeover.calls] == ["call", "delegatecall"]
    nonce = world.view(wallet, "nonce")
    drain = _approvals([ATTACKER], wallet, nonce, "execute", "attacker", 1_000)
    assert world.transact("attacker", wallet, "execute", "attacker", 1_000, drain).success
    assert world.balance("attacker") == 1_000


def test_parity_november_2017_library_freeze():
    world, library, wallet = _wallet(PatchedWalletLibrary)
    blocked = world.transact("attacker", wallet, "init_wallet", [public_key(ATTACKER)], 1)
    assert blocked.error == "already initialized"
    assert world.transact("devops199", library, "init_wallet", [public_key(ATTACKER)], 1).success
    kill = _approvals([ATTACKER], library, 0, "kill", "devops199")
    assert world.transact("devops199", library, "kill", "devops199", kill).success
    assert world.code(library) is None
    approvals = _approvals(KEYS.values(), wallet, 0, "execute", "alice", 1_000)
    receipt = world.transact("alice", wallet, "execute", "alice", 1_000, approvals)
    assert receipt.success and receipt.result is None  # It "worked", and did nothing.
    assert world.balance(wallet) == 1_000 and world.balance("alice") == 0


# Proxies and CREATE2 --------------------------------------------------------


def test_a_naive_proxy_collides_with_its_implementation():
    world = World()
    box = world.deploy("dev", BoxV1)
    proxy = world.deploy("dev", NaiveProxy, box)
    assert world.view(proxy, "owner") == box  # The implementation pointer, misread.
    assert world.transact("alice", proxy, "initialize").success
    assert world.read(proxy, "implementation") == "alice"  # Overwritten.
    receipt = world.transact("alice", proxy, "store", 42)
    assert receipt.success and receipt.result is None  # Delegated to an account with no code.
    assert world.view(proxy, "retrieve") is None
    assert world.transact("alice", proxy, "upgrade_to", box).error == "only the admin upgrades"
    assert world.transact("dev", proxy, "upgrade_to", box).success  # The admin can repair it.
    assert world.view(proxy, "owner") == box


def test_eip1967_proxy_upgrades_preserve_state_unless_reordered():
    world = World()
    proxy = world.deploy("dev", EIP1967Proxy, world.deploy("dev", BoxV1))
    assert world.view(proxy, "owner") == 0
    assert world.transact("alice", proxy, "initialize").success
    assert world.transact("alice", proxy, "initialize").error == "already initialized"
    assert world.transact("bob", proxy, "store", 1).error == "only the owner"
    assert world.transact("alice", proxy, "store", 42).success
    assert world.storage(proxy)[IMPLEMENTATION_SLOT] != "alice"
    v2 = world.deploy("dev", BoxV2)
    assert world.transact("alice", proxy, "upgrade_to", v2).error == "only the admin upgrades"
    assert world.transact("dev", proxy, "upgrade_to", v2).success
    assert (world.view(proxy, "retrieve"), world.view(proxy, "owner")) == (42, "alice")
    assert world.transact("alice", proxy, "store", 7).success
    assert world.view(proxy, "changes") == 1
    world.transact("dev", proxy, "upgrade_to", world.deploy("dev", BoxV2Reordered))
    assert (world.view(proxy, "retrieve"), world.view(proxy, "owner")) == ("alice", 7)


def test_create2_counterfactual_wallets():
    world = World()
    factory = world.deploy("dev", Factory)
    address = world.view(factory, "predict", 7, "alice")
    assert address == create2_address(factory, 7, bk.contracts.Forwarder, "alice")
    world.fund("bob", 100)
    world.transact("bob", address, value=60)  # Paid before anything exists there.
    assert world.code(address) is None and world.balance(address) == 60
    assert world.transact("relayer", factory, "deploy", 7, "alice").result == address
    assert world.transact("anyone", address, "sweep").result == 60
    assert world.balance("alice") == 60
    assert "already in use" in world.transact("relayer", factory, "deploy", 7, "alice").error
    assert world.view(factory, "predict", 8, "alice") != address
    world.transact("bob", address, value=5)  # Once deployed, it still accepts payments.
    assert world.balance(address) == 5
    assert world.view(factory, "predict", 7, "bob") != address


# Governance -----------------------------------------------------------------


def _governance(snapshot):
    world = World()
    token = world.deploy("dao", VotesToken, 1_000_000)
    governance = world.deploy("dao", Governance, token, snapshot)
    world.fund("dao", 10_000)
    world.transact("dao", governance, value=10_000)
    lender = world.deploy("bank", FlashLender, token)
    world.transact("dao", token, "transfer", lender, 900_000)
    attacker = world.deploy("attacker", GovernanceAttacker)
    world.advance()
    pid = world.transact("attacker", governance, "propose", attacker, 10_000).result
    world.advance(blocks=7_200, seconds=86_400)
    return world, token, governance, lender, attacker, pid


def test_beanstalk_flash_loan_governance_attack():
    world, token, governance, lender, attacker, pid = _governance(snapshot=False)
    receipt = world.transact("attacker", attacker, "attack", lender, governance, pid, 900_000)
    assert receipt.success and world.balance("attacker") == 10_000
    assert world.view(token, "balance_of", lender) == 900_000  # Repaid in full.
    assert max(call.depth for call in receipt.calls) >= 3


def test_snapshot_voting_defeats_the_flash_loan():
    world, token, governance, lender, attacker, pid = _governance(snapshot=True)
    receipt = world.transact("attacker", attacker, "attack", lender, governance, pid, 900_000)
    assert receipt.error == "below the two-thirds majority" and world.balance("attacker") == 0
    # Balances at the end of each block: the transfer to the lender was in block 1.
    assert world.view(token, "balance_at", "dao", 0) == 0
    assert world.view(token, "balance_at", "dao", 1) == 100_000
    assert world.view(token, "balance_at", lender, 1) == 900_000
    assert world.transact("dao", governance, "vote", pid).result == 100_000
    assert world.transact("dao", governance, "vote", pid).error == "already voted"
    assert world.transact("dao", governance, "vote", 9).error == "no such proposal"
    assert world.transact("dao", governance, "emergency_commit", 9).error == "no such proposal"


def test_governance_rules():
    world, token, governance, lender, attacker, pid = _governance(snapshot=False)
    assert world.transact("bank", lender, "flash_loan", 10).error  # "bank" is no borrower.
    assert world.transact("mallory", attacker, "attack", lender, governance, pid, 1).error
    assert world.transact("mallory", attacker, "on_flash_loan", token, 1).error == "only the lender"
    early = world.transact("dao", governance, "propose", "dao", 1).result
    world.transact("dao", governance, "vote", early)
    assert world.transact("dao", governance, "emergency_commit", early).error == "too early"
    world.transact("dao", token, "transfer", "whale", 100_000)
    world.transact("bank", lender, "flash_loan", 0)

    # A lender that is not repaid reverts the loan.
    class Defaulter(Contract):
        layout = ()

        def borrow(self, lender, amount):
            self.call(lender, "flash_loan", amount)

        def on_flash_loan(self, token, amount):
            pass

    defaulter = world.deploy("x", Defaulter)
    assert world.transact("x", defaulter, "borrow", lender, 5).error == "flash loan not repaid"
    world.advance(seconds=86_400)
    world.transact("whale", governance, "vote", pid)
    commit = world.transact("dao", governance, "emergency_commit", pid)
    assert commit.error == "below the two-thirds majority"
    holder = world.deploy("x", GovernanceAttacker)
    world.transact("bank", token, "transfer", holder, 0)
    assert world.view(token, "balance_at", "nobody", 5) == 0


def test_executed_proposals_cannot_run_twice():
    world, token, governance, lender, attacker, pid = _governance(snapshot=False)
    world.transact("attacker", attacker, "attack", lender, governance, pid, 900_000)
    assert world.transact("dao", governance, "emergency_commit", pid).error == "already executed"
