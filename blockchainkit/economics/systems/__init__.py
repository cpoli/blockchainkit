"""Auctions, rewards, fee markets, market makers, lending, and transaction ordering."""

from blockchainkit.economics.systems.amm import ConstantProductPool, amount_out, impermanent_loss
from blockchainkit.economics.systems.auctions import (
    equilibrium_bid,
    expected_revenue,
    first_price_auction,
    optimal_reserve,
    second_price_auction,
    simulate_revenue,
    virtual_value,
)
from blockchainkit.economics.systems.coordination import coordination_probability, play_coordination
from blockchainkit.economics.systems.fee_market import next_base_fee, simulate_fee_market
from blockchainkit.economics.systems.fee_only import (
    mining_gap,
    simulate_block_rewards,
    undercutting_payoffs,
)
from blockchainkit.economics.systems.lending import (
    OracleAttacker,
    OracleLender,
    PriceFeed,
    Stablecoin,
    VaultEngine,
)
from blockchainkit.economics.systems.lmsr import lmsr_cost, lmsr_max_loss, lmsr_prices, lmsr_trade
from blockchainkit.economics.systems.mining_games import (
    honest_mining_is_equilibrium,
    optimal_mining_revenue,
)
from blockchainkit.economics.systems.oracles import schelling_round
from blockchainkit.economics.systems.ordering import (
    priority_gas_auction,
    sandwich_attack,
    sandwich_profit,
)
from blockchainkit.economics.systems.pbs import simulate_pbs
from blockchainkit.economics.systems.rewards import (
    block_reward,
    block_subsidy,
    double_spend_incentive,
    issued_supply,
)

__all__ = [
    "ConstantProductPool",
    "amount_out",
    "impermanent_loss",
    "equilibrium_bid",
    "expected_revenue",
    "first_price_auction",
    "optimal_reserve",
    "second_price_auction",
    "simulate_revenue",
    "virtual_value",
    "coordination_probability",
    "play_coordination",
    "next_base_fee",
    "simulate_fee_market",
    "mining_gap",
    "simulate_block_rewards",
    "undercutting_payoffs",
    "OracleAttacker",
    "OracleLender",
    "PriceFeed",
    "Stablecoin",
    "VaultEngine",
    "lmsr_cost",
    "lmsr_max_loss",
    "lmsr_prices",
    "lmsr_trade",
    "honest_mining_is_equilibrium",
    "optimal_mining_revenue",
    "schelling_round",
    "priority_gas_auction",
    "sandwich_attack",
    "sandwich_profit",
    "simulate_pbs",
    "block_reward",
    "block_subsidy",
    "double_spend_incentive",
    "issued_supply",
]
