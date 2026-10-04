"""SHA-256 hashing and bit-level digest comparison from the standard library."""

import hashlib


def sha256(data: bytes) -> bytes:
    """Return the 32-byte SHA-256 digest of bytes.

    >>> from blockchainkit.crypto import sha256
    >>> sha256(b"abc").hex()
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes; encode text explicitly")
    return hashlib.sha256(data).digest()


def hash256(data: bytes) -> bytes:
    """Return SHA-256(SHA-256(data)), as used in Bitcoin hashing."""
    return sha256(sha256(data))


def hamming_distance(left: bytes, right: bytes) -> int:
    """Count differing bits between equally long byte strings.

    >>> from blockchainkit.crypto import hamming_distance
    >>> hamming_distance(bytes([0]), bytes([7]))
    3
    """
    if len(left) != len(right):
        raise ValueError("inputs must have equal length")
    return sum((a ^ b).bit_count() for a, b in zip(left, right, strict=True))
