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
