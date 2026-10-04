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
