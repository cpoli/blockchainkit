"""Hashing and length-delimited commitments using standard-library SHA-256."""

import hashlib
import hmac


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


def commit(message: bytes, salt: bytes) -> bytes:
    """Commit to a message with a secret salt of at least 16 bytes.

    Parameters
    ----------
    message : bytes
        Bytes to commit to.
    salt : bytes
        Random secret salt; fixed salts are only appropriate for experiments.

    Returns
    -------
    bytes
        Domain-separated digest. Length framing prevents ambiguous openings.

    Notes
    -----
    Hiding depends on salt entropy; binding relies on collision resistance.
    """
    if not isinstance(message, bytes) or not isinstance(salt, bytes):
        raise TypeError("message and salt must be bytes")
    if len(salt) < 16:
        raise ValueError("use at least 16 salt bytes")
    return sha256(b"blockchainkit:commit:v1\0" + len(salt).to_bytes(8, "big") + salt + message)


def verify_commitment(digest: bytes, message: bytes, salt: bytes) -> bool:
    """Check an opening against a commitment using constant-time comparison."""
    return hmac.compare_digest(digest, commit(message, salt))


def hamming_distance(left: bytes, right: bytes) -> int:
    """Count differing bits between equally long byte strings.

    >>> from blockchainkit.crypto import hamming_distance
    >>> hamming_distance(bytes([0]), bytes([7]))
    3
    """
    if len(left) != len(right):
        raise ValueError("inputs must have equal length")
    return sum((a ^ b).bit_count() for a, b in zip(left, right, strict=True))
