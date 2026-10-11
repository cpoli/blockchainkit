"""Consensus-relevant constants shared across blockchainkit.

Every hash domain tag, encoding bound, and default identifier lives here, so
a change to one of them is visible as a change to the protocol. Changing any
value changes hashes, signatures, or validation: update
``docs/source/protocol.rst``, the tests, the examples, and ``CHANGELOG.md``
together.

>>> from blockchainkit import constants
>>> constants.UINT64_LIMIT == 2**64
True
"""

UINT64_LIMIT = 2**64
"""int: Exclusive upper bound of the unsigned 64-bit fields (nonces, amounts, heights)."""

WORD_MODULUS = 2**256
"""int: The virtual machine's word size; arithmetic wraps modulo this value."""

DEFAULT_CHAIN_ID = "blockchainkit-demo"
"""str: Network identifier signed into every transaction to prevent cross-chain replay."""

COMMIT_DOMAIN = b"blockchainkit:commit:v1\0"
"""bytes: Domain tag prefixed to hash commitments."""

SCHNORR_DOMAIN = "blockchainkit:schnorr:v1"
"""str: Domain tag prefixed, with the curve parameters, to Schnorr challenges."""

MERKLE_LEAF_PREFIX = b"\x00"
"""bytes: Prefix for hashing a Merkle leaf payload."""

MERKLE_NODE_PREFIX = b"\x01"
"""bytes: Prefix for hashing two child digests into a Merkle node."""

MERKLE_ROOT_PREFIX = b"\x02"
"""bytes: Prefix for binding the leaf count to the top Merkle digest."""

PUZZLE_DOMAIN = b"blockchainkit:puzzle:v1"
"""bytes: Domain tag for the keystream that encrypts a Merkle puzzle."""

PUZZLE_MAGIC = b"MERKLE78"
"""bytes: Known plaintext prefix that tells a solver a puzzle has opened."""

LAMPORT_DOMAIN = b"blockchainkit:lamport:v1"
"""bytes: Domain tag for deriving Lamport private preimages from a seed."""

PEDERSEN_DOMAIN = b"blockchainkit:pedersen:v1"
"""bytes: Domain tag for deriving the second Pedersen generator."""

MUSIG_DOMAIN = b"blockchainkit:musig:v1"
"""bytes: Domain tag for MuSig key-aggregation coefficients."""

MMR_ROOT_PREFIX = b"\x03"
"""bytes: Prefix for bagging Merkle-mountain-range peaks into one root."""

BLOOM_DOMAIN = b"blockchainkit:bloom:v1"
"""bytes: Domain tag for deriving Bloom-filter bit positions."""

UTXO_DOMAIN = "blockchainkit:utxo:v1"
"""str: Domain tag signed into every UTXO transaction."""

SORTITION_DOMAIN = b"blockchainkit:sortition:v1"
"""bytes: Domain tag for the hash that stands in for a VRF in cryptographic sortition."""

COMPACT_BLOCK_DOMAIN = b"blockchainkit:compact-block:v1"
"""bytes: Domain tag for the salted short transaction IDs of compact blocks."""

CREATE_DOMAIN = b"blockchainkit:create:v1"
"""bytes: Domain tag for contract addresses derived from the deployer and its nonce."""

CREATE2_DOMAIN = b"blockchainkit:create2:v1"
"""bytes: Domain tag for contract addresses derived from the deployer, a salt and the code."""

BLOCKHASH_DOMAIN = b"blockchainkit:blockhash:v1"
"""bytes: Domain tag for the block hashes of the contract world model."""

RICARDIAN_DOMAIN = b"blockchainkit:ricardian:v1"
"""bytes: Domain tag for the identifier of a Ricardian contract."""

CONTRACT_COMMIT_DOMAIN = b"blockchainkit:contract-commit:v1"
"""bytes: Domain tag for the commitments of the commit-reveal lottery."""

WALLET_DOMAIN = b"blockchainkit:wallet:v1"
"""bytes: Domain tag for the messages that multisig wallet owners sign."""

EIP1967_IMPLEMENTATION_LABEL = b"eip1967.proxy.implementation"
"""bytes: Label hashed to the storage slot of a proxy's implementation address (EIP-1967)."""

EIP1967_ADMIN_LABEL = b"eip1967.proxy.admin"
"""bytes: Label hashed to the storage slot of a proxy's admin address (EIP-1967)."""

CHANNEL_DOMAIN = b"blockchainkit:channel:v1"
"""bytes: Domain tag for the off-chain states, commitments and penalties channel parties sign."""

PLASMA_DOMAIN = b"blockchainkit:plasma:v1"
"""bytes: Domain tag for the coin transfers of the Plasma child chain."""

ROLLUP_DOMAIN = b"blockchainkit:rollup:v1"
"""bytes: Domain tag for the account leaves of a rollup's state root."""

BRIDGE_DOMAIN = b"blockchainkit:bridge:v1"
"""bytes: Domain tag for the withdrawals and messages that bridge validators sign."""

WATCHTOWER_DOMAIN = b"blockchainkit:watchtower:v1"
"""bytes: Domain tag for watchtower blob encryption and appointment receipts."""

TRANSCRIPT_DOMAIN = b"blockchainkit:transcript:v1"
"""bytes: Domain tag for the Fiat-Shamir transcripts of the proof systems."""

IPA_GENERATOR_DOMAIN = b"blockchainkit:ipa-generators:v1"
"""bytes: Domain tag for deriving the independent generators of inner-product arguments."""

MIMC_DOMAIN = b"blockchainkit:mimc:v1"
"""bytes: Domain tag for deriving the round constants of the MiMC hash."""

SUM_LEAF_DOMAIN = b"blockchainkit:sum-leaf:v1"
"""bytes: Domain tag for hashing a customer's balance into a Merkle-sum-tree leaf."""

SUM_NODE_DOMAIN = b"blockchainkit:sum-node:v1"
"""bytes: Domain tag for hashing two children and both their sums into a Merkle-sum-tree node."""

SOLVENCY_DOMAIN = b"blockchainkit:solvency:v1"
"""bytes: Domain tag for the Fiat-Shamir challenges of the proofs of solvency."""

LOOKALIKE_DOMAIN = b"blockchainkit:lookalike:v1"
"""bytes: Domain tag for the candidate addresses ground out by an address poisoner."""
