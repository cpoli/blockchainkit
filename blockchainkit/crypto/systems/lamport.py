"""Lamport one-time signatures (1979): signatures from a hash function alone.

The private key is 256 pairs of random preimages; the public key is their
hashes. To sign, hash the message and, for each digest bit, reveal the
preimage for that bit's value. Verification hashes each revealed preimage.
Each signature reveals half the private key, so a key must sign only once.
Security rests only on the hash being one-way, so the scheme survives
quantum computers, and its descendants (XMSS, SPHINCS+) are standardized.
"""

import hmac

from blockchainkit.constants import LAMPORT_DOMAIN
from blockchainkit.crypto.core.base import LamportKeyPair
from blockchainkit.crypto.systems.hashing import sha256


def _bits(message: bytes) -> list[int]:
    digest = int.from_bytes(sha256(message), "big")
    return [(digest >> (255 - i)) & 1 for i in range(256)]


def lamport_keypair(seed: bytes) -> LamportKeyPair:
    """Derive a one-time key pair deterministically from a secret seed.

    Each private preimage is SHA-256(domain || seed || index || bit). A real
    seed must be at least 32 random bytes and never reused.

    >>> from blockchainkit.crypto import lamport_keypair
    >>> len(lamport_keypair(b"seed").public)
    256
    """
    if not isinstance(seed, bytes):
        raise TypeError("seed must be bytes")
    pairs = []
    for i in range(256):
        prefix = LAMPORT_DOMAIN + seed + i.to_bytes(2, "big")
        pairs.append((sha256(prefix + b"\x00"), sha256(prefix + b"\x01")))
    public = tuple((sha256(zero), sha256(one)) for zero, one in pairs)
    return LamportKeyPair(tuple(pairs), public)


def lamport_sign(message: bytes, key: LamportKeyPair) -> tuple[bytes, ...]:
    """Reveal, for each bit of SHA-256(message), the matching private preimage."""
    if not isinstance(message, bytes):
        raise TypeError("message must be bytes")
    return tuple(pair[bit] for pair, bit in zip(key.private, _bits(message), strict=True))


def lamport_verify(
    message: bytes, signature: tuple[bytes, ...], public: tuple[tuple[bytes, bytes], ...]
) -> bool:
    """Check that each revealed preimage hashes to the public value for its bit.

    >>> from blockchainkit.crypto import lamport_keypair, lamport_sign, lamport_verify
    >>> key = lamport_keypair(b"seed")
    >>> lamport_verify(b"hello", lamport_sign(b"hello", key), key.public)
    True
    """
    if not isinstance(message, bytes) or len(signature) != 256 or len(public) != 256:
        return False
    return all(
        isinstance(revealed, bytes) and hmac.compare_digest(sha256(revealed), pair[bit])
        for revealed, pair, bit in zip(signature, public, _bits(message), strict=True)
    )
