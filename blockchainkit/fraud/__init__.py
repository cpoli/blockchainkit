"""Fraud: how people are defrauded on and around blockchains, and how to tell.

Ponzi schemes old and new, figures that fail Benford's law, proofs of
reserves and liabilities, custodians that lose or lend their customers'
coins, scam contracts whose source deceives the reader who checks it
(honeypots, hidden mints and sell blocks), price manipulation and
pump-and-dumps, wash trading, approval phishing, and address poisoning.
"""

from blockchainkit.fraud.core.base import (
    AuditResult,
    BenfordTest,
    BitRangeProof,
    Flow,
    LookalikeAddress,
    MarketRun,
    PonziFeatures,
    PonziRun,
    PumpRun,
    SolvencyProof,
    SumProof,
    SumProofStep,
    Trade,
    TradeHistory,
    WashReport,
)
from blockchainkit.fraud.systems.benford import (
    DIGITS,
    benford_probability,
    benford_test,
    chi_square_survival,
    first_digit,
)
from blockchainkit.fraud.systems.custody import TRACKING, Custodian, reissue_missing
from blockchainkit.fraud.systems.honeypots import (
    DividendDistributor,
    ForTest,
    GiftBox,
    GuessNumber,
    Honeypot,
    KingOfTheHill,
    Log,
    MultiplicatorX3,
    PrivateBank,
    Relay,
    TrapLog,
    explorer_view,
)
from blockchainkit.fraud.systems.manipulation import (
    detect_pumps,
    return_by_activity,
    simulate_bot_market,
    simulate_pump_and_dump,
)
from blockchainkit.fraud.systems.phishing import (
    UNLIMITED,
    Drainer,
    allowance_exposure,
    open_approvals,
)
from blockchainkit.fraud.systems.poisoning import (
    candidate_address,
    grind_lookalike,
    looks_alike,
    matched_characters,
    poisoning_suspects,
)
from blockchainkit.fraud.systems.ponzi import (
    ChainPonzi,
    breakeven_growth,
    ponzi_features,
    referral_commissions,
    simulate_lending_ponzi,
    simulate_ponzi,
    value_flows,
)
from blockchainkit.fraud.systems.provisions import (
    DEFAULT_BITS,
    SolvencyProver,
    prove_either,
    prove_range,
    verify_either,
    verify_liability,
    verify_range,
    verify_solvency,
)
from blockchainkit.fraud.systems.reserves import (
    audit,
    detection_probability,
    liability_tree,
    reserve_ratio,
)
from blockchainkit.fraud.systems.rug_pulls import HiddenMintToken, SellBlockToken, sell_test
from blockchainkit.fraud.systems.token_sales import TokenSale
from blockchainkit.fraud.systems.verification import (
    SeizableToken,
    UpgradeableToken,
    effective_code,
    verify_source,
)
from blockchainkit.fraud.systems.wash_trading import find_wash_trades, simulate_nft_market
from blockchainkit.fraud.utils.merkle_sum import MerkleSumTree, sum_leaf, sum_node, verify_sum_proof

__all__ = [
    "AuditResult",
    "BenfordTest",
    "Flow",
    "LookalikeAddress",
    "MarketRun",
    "PonziFeatures",
    "PonziRun",
    "PumpRun",
    "BitRangeProof",
    "SolvencyProof",
    "SumProof",
    "SumProofStep",
    "Trade",
    "TradeHistory",
    "WashReport",
    "breakeven_growth",
    "simulate_ponzi",
    "simulate_lending_ponzi",
    "referral_commissions",
    "ChainPonzi",
    "value_flows",
    "ponzi_features",
    "DIGITS",
    "benford_probability",
    "first_digit",
    "chi_square_survival",
    "benford_test",
    "liability_tree",
    "detection_probability",
    "audit",
    "reserve_ratio",
    "DEFAULT_BITS",
    "prove_either",
    "verify_either",
    "prove_range",
    "verify_range",
    "SolvencyProver",
    "verify_liability",
    "verify_solvency",
    "TRACKING",
    "reissue_missing",
    "Custodian",
    "verify_source",
    "effective_code",
    "UpgradeableToken",
    "SeizableToken",
    "explorer_view",
    "Relay",
    "MultiplicatorX3",
    "GiftBox",
    "Log",
    "TrapLog",
    "PrivateBank",
    "KingOfTheHill",
    "GuessNumber",
    "Honeypot",
    "ForTest",
    "DividendDistributor",
    "simulate_bot_market",
    "return_by_activity",
    "simulate_pump_and_dump",
    "detect_pumps",
    "TokenSale",
    "HiddenMintToken",
    "SellBlockToken",
    "sell_test",
    "find_wash_trades",
    "simulate_nft_market",
    "UNLIMITED",
    "Drainer",
    "open_approvals",
    "allowance_exposure",
    "candidate_address",
    "matched_characters",
    "looks_alike",
    "grind_lookalike",
    "poisoning_suspects",
    "MerkleSumTree",
    "sum_leaf",
    "sum_node",
    "verify_sum_proof",
]
