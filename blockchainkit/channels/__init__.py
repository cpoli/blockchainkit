"""Channels: layer-2 scaling and interoperability.

How a blockchain scales beyond what every node can verify, and how chains
connect: Reed-Solomon codes, payment channels from Spilman's to Lightning
and eltoo, multi-hop routing and its privacy, atomic swaps, light-client
relays and bridges, state channels and watchtowers, Plasma, sharding,
rollups, and data-availability sampling.
"""

from blockchainkit.channels.core.base import (
    AppointmentReceipt,
    AtomixResult,
    CoinTransfer,
    Commitment,
    EncodingFraudProof,
    ErasureCodedData,
    FraudProof,
    InclusionProof,
    PaymentAttempt,
    PlasmaExit,
    ProbeResult,
    Route,
    SamplingResult,
    Settlement,
    SwapOutcome,
    Transfer,
    ValidityProof,
)
from blockchainkit.channels.systems.bridges import (
    ForgedVerifier,
    GuardianVerifier,
    ValidatorBridge,
    WormholeBridge,
    sign_withdrawal,
    withdrawal_message,
)
from blockchainkit.channels.systems.data_availability import (
    commit_shares,
    detection_probability,
    encoding_fraud_proof,
    extend,
    prove_share,
    simulate_sampling,
    verify_encoding_fraud_proof,
    verify_share,
)
from blockchainkit.channels.systems.duplex import (
    DuplexChannel,
    first_confirmed,
    invalidation_locktimes,
)
from blockchainkit.channels.systems.eltoo import EltooChannel
from blockchainkit.channels.systems.lightning import LightningChannel
from blockchainkit.channels.systems.micropayment import SpilmanChannel
from blockchainkit.channels.systems.plasma import PlasmaChain, sign_transfer, transfer_message
from blockchainkit.channels.systems.probing import probe_balance
from blockchainkit.channels.systems.reed_solomon import (
    is_codeword,
    rs_decode,
    rs_encode,
    rs_recover,
)
from blockchainkit.channels.systems.relay import BTCRelay, mine_header
from blockchainkit.channels.systems.rollups import (
    OptimisticRollup,
    ZKRollup,
    apply_transfer,
    batch_digest,
    batch_gas,
    bisect,
    execute_batch,
    state_root,
)
from blockchainkit.channels.systems.routing import ChannelNetwork
from blockchainkit.channels.systems.sharding import (
    assign_shards,
    atomix_transfer,
    compromised_epochs,
    shard_failure_probability,
)
from blockchainkit.channels.systems.state_channels import (
    PreimageManager,
    StateChannel,
    collateral_time,
    htlc_expiries,
    sign_state,
    sprites_expiries,
    state_message,
)
from blockchainkit.channels.systems.swaps import AtomicSwap
from blockchainkit.channels.systems.watchtowers import (
    Watchtower,
    make_appointment,
    receipt_message,
    tower_liable,
    verify_receipt,
)

__all__ = [
    "AppointmentReceipt",
    "AtomixResult",
    "CoinTransfer",
    "Commitment",
    "EncodingFraudProof",
    "ErasureCodedData",
    "FraudProof",
    "InclusionProof",
    "PaymentAttempt",
    "PlasmaExit",
    "ProbeResult",
    "Route",
    "SamplingResult",
    "Settlement",
    "SwapOutcome",
    "Transfer",
    "ValidityProof",
    "ForgedVerifier",
    "GuardianVerifier",
    "ValidatorBridge",
    "WormholeBridge",
    "sign_withdrawal",
    "withdrawal_message",
    "commit_shares",
    "detection_probability",
    "encoding_fraud_proof",
    "extend",
    "prove_share",
    "simulate_sampling",
    "verify_encoding_fraud_proof",
    "verify_share",
    "DuplexChannel",
    "first_confirmed",
    "invalidation_locktimes",
    "EltooChannel",
    "LightningChannel",
    "SpilmanChannel",
    "PlasmaChain",
    "sign_transfer",
    "transfer_message",
    "probe_balance",
    "is_codeword",
    "rs_decode",
    "rs_encode",
    "rs_recover",
    "BTCRelay",
    "mine_header",
    "OptimisticRollup",
    "ZKRollup",
    "apply_transfer",
    "batch_digest",
    "batch_gas",
    "bisect",
    "execute_batch",
    "state_root",
    "ChannelNetwork",
    "assign_shards",
    "atomix_transfer",
    "compromised_epochs",
    "shard_failure_probability",
    "PreimageManager",
    "StateChannel",
    "collateral_time",
    "htlc_expiries",
    "sign_state",
    "sprites_expiries",
    "state_message",
    "AtomicSwap",
    "Watchtower",
    "make_appointment",
    "receipt_message",
    "tower_liable",
    "verify_receipt",
]
