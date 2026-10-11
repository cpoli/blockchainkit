"""Contracts: the constant-product pool, Dai vaults, and oracle manipulation."""

from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from blockchainkit.contracts import ERC20, ContractError, FlashLender, World
from blockchainkit.economics import (
    ConstantProductPool,
    OracleAttacker,
    OracleLender,
    PriceFeed,
    Stablecoin,
    VaultEngine,
    amount_out,
    impermanent_loss,
)

# Swap math --------------------------------------------------------------------


@given(st.integers(1, 10**9), st.integers(1, 10**9), st.integers(0, 10**9), st.integers(0, 100))
def test_swaps_never_decrease_the_product(x, y, dx, fee):
    dy = amount_out(x, y, dx, fee_bps=fee)
    assert 0 <= dy < y
    assert (x + dx) * (y - dy) >= x * y


def test_amount_out_and_impermanent_loss():
    assert amount_out(1_000, 1_000, 1_000, fee_bps=0) == 500
    assert amount_out(1_000, 1_000, 1_000) == 499
    assert impermanent_loss(2.0) == pytest.approx(-0.05719, abs=1e-5)
    assert impermanent_loss(2.0) == pytest.approx(impermanent_loss(0.5))
    with pytest.raises(ValueError):
        amount_out(1, 1, 1, fee_bps=10_000)
    with pytest.raises(ValueError):
        amount_out(0, 1, 1)
    with pytest.raises(ValueError):
        impermanent_loss(0.0)


# The pool ---------------------------------------------------------------------


def _pool(fee_bps=30):
    world = World()
    tok = world.deploy("lp", ERC20, 10**6, name="TOK")
    usd = world.deploy("lp", ERC20, 10**6, name="USD")
    pool = world.deploy("lp", ConstantProductPool, tok, usd, fee_bps, name="pool")
    for token in (tok, usd):
        world.transact("lp", token, "approve", pool, 10**6)
        world.transact("lp", token, "transfer", "trader", 10_000)
        world.transact("trader", token, "approve", pool, 10_000)
    return world, tok, usd, pool


def test_liquidity_shares_and_proportional_withdrawal():
    world, tok, usd, pool = _pool()
    first = world.transact("lp", pool, "add_liquidity", 10_000, 40_000)
    assert first.result == 20_000  # sqrt(10,000 * 40,000)
    assert world.transact("trader", pool, "add_liquidity", 1_000, 4_000).result == 2_000
    assert world.view(pool, "price") == Fraction(4)
    out = world.transact("trader", pool, "remove_liquidity", 2_000).result
    assert out == (1_000, 4_000)
    assert world.view(pool, "shares_of", "trader") == 0
    assert world.view(pool, "reserves") == (10_000, 40_000)


def test_swaps_in_both_directions_follow_the_formula():
    world, tok, usd, pool = _pool()
    world.transact("lp", pool, "add_liquidity", 10_000, 40_000)
    bought = world.transact("trader", pool, "swap", usd, 4_000, 0)
    assert bought.result == amount_out(40_000, 10_000, 4_000)
    assert world.view(tok, "balance_of", "trader") == 10_000 + bought.result
    sold = world.transact("trader", pool, "swap", tok, 500, 0)
    assert sold.result == amount_out(10_000 - bought.result, 44_000, 500)
    assert bought.events[-1].name == "Swap"


def test_slippage_limit_and_guards():
    world, tok, usd, pool = _pool()
    assert world.transact("trader", pool, "swap", usd, 10, 0).error == "the pool is empty"
    with pytest.raises(ContractError, match="empty"):
        world.view(pool, "price")
    world.transact("lp", pool, "add_liquidity", 10_000, 10_000)
    quote = amount_out(10_000, 10_000, 1_000)
    assert (
        world.transact("trader", pool, "swap", usd, 1_000, quote + 1).error
        == "slippage limit exceeded"
    )
    assert world.transact("trader", pool, "swap", usd, 1_000, quote).success
    assert (
        world.transact("trader", pool, "swap", "0xother", 1, 0).error == "not a token of this pool"
    )
    assert world.transact("trader", pool, "swap", usd, 0, 0).error == "amount must be positive"
    assert world.transact("trader", pool, "add_liquidity", 0, 1).error == "deposit both tokens"
    assert (
        world.transact("trader", pool, "add_liquidity", 1.5, 1).error == "amounts must be integers"
    )
    assert world.transact("trader", pool, "add_liquidity", 1, 1).error == "deposit too small"
    assert world.transact("trader", pool, "remove_liquidity", 1).error == "not enough shares"


def test_identical_tokens_are_rejected():
    world = World()
    tok = world.deploy("lp", ERC20, 10)
    with pytest.raises(ContractError, match="differ"):
        world.deploy("lp", ConstantProductPool, tok, tok)


def test_previous_price_ignores_trades_in_the_current_block():
    world, tok, usd, pool = _pool()
    world.transact("lp", pool, "add_liquidity", 10_000, 10_000)
    with pytest.raises(ContractError, match="no price"):
        world.view(pool, "previous_price")  # Still the block of the first deposit.
    world.advance()
    world.transact("trader", pool, "swap", usd, 5_000, 0)
    assert world.view(pool, "price") > 2
    assert world.view(pool, "previous_price") == 1
    world.advance()
    assert world.view(pool, "previous_price") == world.view(pool, "price")


# Dai --------------------------------------------------------------------------


def _vault():
    world = World()
    feed = world.deploy("maker", PriceFeed, 300, name="feed")
    engine = world.deploy("maker", VaultEngine, feed, name="engine")
    dai = world.view(engine, "dai")
    world.fund("alice", 10)
    world.transact("alice", engine, "lock", value=10)
    return world, feed, engine, dai


def test_vaults_mint_against_150_percent_collateral():
    world, feed, engine, dai = _vault()
    assert (
        world.transact("alice", engine, "draw", 2_001).error == "vault would be undercollateralized"
    )
    assert world.transact("alice", engine, "draw", 2_000).success
    assert world.view(dai, "balance_of", "alice") == 2_000 and world.view(
        engine, "is_safe", "alice"
    )
    assert world.transact("alice", engine, "free", 1).error == "vault would be undercollateralized"
    assert world.transact("alice", engine, "wipe", 500).success
    assert world.view(engine, "debt_of", "alice") == 1_500
    assert world.transact("alice", engine, "free", 2).success and world.balance("alice") == 2
    assert world.view(engine, "collateral_of", "alice") == 8
    assert world.view(dai, "total_supply") == 1_500


def test_liquidation_after_a_price_drop():
    world, feed, engine, dai = _vault()
    world.transact("alice", engine, "draw", 2_000)
    world.transact("alice", dai, "transfer", "keeper", 2_000)
    assert world.transact("keeper", engine, "liquidate", "alice").error == "vault is safe"
    world.transact("maker", feed, "set_price", 250)
    receipt = world.transact("keeper", engine, "liquidate", "alice")
    assert receipt.result == 10  # 2,000 * 1.13 / 250 = 9.04, rounded up.
    assert world.balance("keeper") == 10 and world.view(dai, "total_supply") == 0
    assert world.view(engine, "debt_of", "alice") == 0


def test_liquidation_leaves_the_surplus_to_the_owner():
    world, feed, engine, dai = _vault()
    world.transact("alice", engine, "draw", 1_000)
    world.transact("alice", dai, "transfer", "keeper", 1_000)
    world.transact("maker", feed, "set_price", 140)
    assert world.transact("keeper", engine, "liquidate", "alice").result == 9  # ceil(8.07)
    assert world.view(engine, "collateral_of", "alice") == 1


def test_vault_guards():
    world, feed, engine, dai = _vault()
    assert world.transact("alice", engine, "draw", 0).error == "amount must be positive"
    assert world.transact("alice", engine, "wipe", 1).error == "amount exceeds the debt"
    assert world.transact("alice", engine, "free", 11).error == "amount exceeds the collateral"
    assert world.transact("bob", feed, "set_price", 1).error == "only the owner reports prices"
    assert world.transact("maker", feed, "set_price", 0).error == "price must be a positive integer"
    assert world.transact("bob", dai, "mint", "bob", 1).error == "only the minter"
    assert world.transact("bob", dai, "burn", "alice", 1).error == "only the minter"
    world.transact("alice", engine, "draw", 100)
    world.transact("alice", dai, "transfer", "bob", 100)
    assert world.transact("alice", engine, "wipe", 50).error == "insufficient balance"


def test_a_stablecoin_can_start_with_a_supply():
    world = World()
    coin = world.deploy("issuer", Stablecoin, 5)
    assert world.view(coin, "balance_of", "issuer") == 5


# Oracle manipulation ----------------------------------------------------------


def _lending_market(delayed):
    world = World()
    tok = world.deploy("dex", ERC20, 10**6, name="TOK")
    usd = world.deploy("bank", ERC20, 10**7, name="USD")
    world.transact("bank", usd, "transfer", "dex", 100_000)
    pool = world.deploy("dex", ConstantProductPool, tok, usd, name="pool")
    world.transact("dex", tok, "approve", pool, 10**6)
    world.transact("dex", usd, "approve", pool, 10**6)
    world.transact("dex", pool, "add_liquidity", 100_000, 100_000)
    lender = world.deploy("bank", OracleLender, tok, usd, pool, delayed, name="lender")
    world.transact("bank", usd, "transfer", lender, 1_000_000)
    flash = world.deploy("bank", FlashLender, usd, name="flash")
    world.transact("bank", usd, "transfer", flash, 1_000_000)
    world.advance()
    attacker = world.deploy("eve", OracleAttacker, name="attacker")
    return world, tok, usd, pool, lender, flash, attacker


def test_a_flash_loan_inflates_a_spot_price_oracle():
    world, tok, usd, pool, lender, flash, attacker = _lending_market(delayed=False)
    receipt = world.transact("eve", attacker, "attack", flash, pool, lender, 300_000)
    assert receipt.success
    profit = world.view(usd, "balance_of", "eve")
    assert profit > 400_000  # About U (y + U) / 1.5 y - U, less fees.
    assert world.view(usd, "balance_of", flash) == 1_000_000  # The loan was repaid.
    lent = 1_000_000 - world.view(usd, "balance_of", lender)
    collateral = world.view(tok, "balance_of", lender)
    fair_value = collateral * world.view(pool, "previous_price")
    assert lent > 2 * fair_value  # Even at the old price, the debt is not covered.


def test_a_price_from_before_the_block_defeats_it():
    world, tok, usd, pool, lender, flash, attacker = _lending_market(delayed=True)
    receipt = world.transact("eve", attacker, "attack", flash, pool, lender, 300_000)
    assert receipt.error == "undercollateralized"
    assert world.view(usd, "balance_of", lender) == 1_000_000
    assert world.view(lender, "collateral_token") == tok and world.view(lender, "debt_token") == usd


def test_honest_borrowing_and_attacker_guards():
    world, tok, usd, pool, lender, flash, attacker = _lending_market(delayed=True)
    world.transact("dex", tok, "transfer", "bob", 300)
    world.transact("bob", tok, "approve", lender, 300)
    assert world.transact("bob", lender, "borrow", 300, 200).success
    assert world.view(usd, "balance_of", "bob") == 200
    assert (
        world.transact("mallory", attacker, "attack", flash, pool, lender, 1).error
        == "only the owner"
    )
    assert world.transact("mallory", attacker, "on_flash_loan", usd, 1).error == "only the lender"
