"""Contracts: designing, breaking and verifying smart contracts.

A world-state model of accounts and contracts calling each other, the
contracts and standards that shaped the field, the bugs behind its largest
losses, and the methods that check contracts before they hold money.
"""

from blockchainkit.contracts.core.base import (
    CallRecord,
    ContractError,
    Event,
    Expr,
    FuzzCall,
    FuzzResult,
    Receipt,
    RicardianContract,
    SymbolicPath,
    SymbolicResult,
    TripleResult,
)
from blockchainkit.contracts.systems.capabilities import (
    AirdropPhisher,
    Mint,
    OriginWallet,
    Purse,
    SenderWallet,
)
from blockchainkit.contracts.systems.design_by_contract import ensures, requires
from blockchainkit.contracts.systems.factory import Factory, Forwarder
from blockchainkit.contracts.systems.fuzzing import fuzz, shrink
from blockchainkit.contracts.systems.governance import (
    FlashLender,
    Governance,
    GovernanceAttacker,
    VotesToken,
)
from blockchainkit.contracts.systems.hoare import check_triple, run_program, weakest_precondition
from blockchainkit.contracts.systems.payments import (
    CheckedKingOfTheEther,
    ContractWallet,
    GovernMental,
    KingOfTheEther,
    PullKingOfTheEther,
    Usurper,
)
from blockchainkit.contracts.systems.proxies import (
    BoxV1,
    BoxV2,
    BoxV2Reordered,
    EIP1967Proxy,
    NaiveProxy,
)
from blockchainkit.contracts.systems.randomness import (
    BlockhashLottery,
    CommitRevealLottery,
    LotteryPredictor,
    commitment,
)
from blockchainkit.contracts.systems.ricardian import (
    RicardianToken,
    ricardian_contract,
    ricardian_digest,
    verify_ricardian,
)
from blockchainkit.contracts.systems.symbolic import (
    boundary_values,
    solve,
    symbolic_bytecode,
    symbolic_execute,
)
from blockchainkit.contracts.systems.tokens import ERC20, ERC721, NFTVault
from blockchainkit.contracts.systems.wallets import (
    PatchedWalletLibrary,
    Wallet,
    WalletLibrary,
    approve_action,
    threshold_met,
    wallet_message,
)
from blockchainkit.contracts.systems.world import (
    Contract,
    World,
    code_hash,
    create2_address,
    create_address,
)
from blockchainkit.contracts.utils.expressions import (
    evaluate,
    expression,
    parse_expression,
    parse_program,
    substitute,
    to_source,
)

__all__ = [
    "CallRecord",
    "ContractError",
    "Event",
    "Expr",
    "FuzzCall",
    "FuzzResult",
    "Receipt",
    "RicardianContract",
    "SymbolicPath",
    "SymbolicResult",
    "TripleResult",
    "AirdropPhisher",
    "Mint",
    "OriginWallet",
    "Purse",
    "SenderWallet",
    "ensures",
    "requires",
    "Factory",
    "Forwarder",
    "fuzz",
    "shrink",
    "FlashLender",
    "Governance",
    "GovernanceAttacker",
    "VotesToken",
    "check_triple",
    "run_program",
    "weakest_precondition",
    "CheckedKingOfTheEther",
    "ContractWallet",
    "GovernMental",
    "KingOfTheEther",
    "PullKingOfTheEther",
    "Usurper",
    "BoxV1",
    "BoxV2",
    "BoxV2Reordered",
    "EIP1967Proxy",
    "NaiveProxy",
    "BlockhashLottery",
    "CommitRevealLottery",
    "LotteryPredictor",
    "commitment",
    "RicardianToken",
    "ricardian_contract",
    "ricardian_digest",
    "verify_ricardian",
    "boundary_values",
    "solve",
    "symbolic_bytecode",
    "symbolic_execute",
    "ERC20",
    "ERC721",
    "NFTVault",
    "PatchedWalletLibrary",
    "Wallet",
    "WalletLibrary",
    "approve_action",
    "threshold_met",
    "wallet_message",
    "Contract",
    "World",
    "code_hash",
    "create2_address",
    "create_address",
    "evaluate",
    "expression",
    "parse_expression",
    "parse_program",
    "substitute",
    "to_source",
]
