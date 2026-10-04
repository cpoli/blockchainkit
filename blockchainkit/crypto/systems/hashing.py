"""SHA-256 hashing, bit-level digest comparison, and birthday collisions."""

import hashlib

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import CollisionResult


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


def truncated_hash(data: bytes, bits: int) -> int:
    """Return the top ``bits`` bits of SHA-256(data) as an integer.

    Truncation makes collisions findable, to measure the birthday bound.

    >>> from blockchainkit.crypto import truncated_hash
    >>> truncated_hash(b"abc", 8) == sha256(b"abc")[0]
    True
    """
    integer(bits, "bits", 1)
    if bits > 256:
        raise ValueError("bits cannot exceed 256")
    return int.from_bytes(sha256(data), "big") >> (256 - bits)


def find_collision(bits: int, *, prefix: bytes = b"", max_trials: int = 1 << 22) -> CollisionResult:
    """Find two inputs whose ``bits``-bit truncated hashes agree.

    Hashes ``prefix + counter`` for counter = 0, 1, 2, ... and remembers every
    truncated digest. By the birthday paradox a repeat is expected after
    about ``sqrt(pi/2 * 2**bits)`` trials, far fewer than the ``2**bits``
    needed to hit one *given* digest (Yuval, 1979).

    Parameters
    ----------
    bits : int
        Output size to attack, between 1 and 48.
    prefix : bytes
        Shared prefix of every candidate input.
    max_trials : int
        Search bound.

    Raises
    ------
    TimeoutError
        No collision within ``max_trials``.

    Examples
    --------
    >>> from blockchainkit.crypto import find_collision
    >>> result = find_collision(16)
    >>> result.first != result.second, result.trials < 2**10
    (True, True)
    """
    integer(bits, "bits", 1)
    if bits > 48:
        raise ValueError("bits must be at most 48 to keep the search bounded")
    integer(max_trials, "max_trials", 1)
    if not isinstance(prefix, bytes):
        raise TypeError("prefix must be bytes")
    seen: dict[int, bytes] = {}
    for counter in range(max_trials):
        candidate = prefix + counter.to_bytes(8, "big")
        digest = truncated_hash(candidate, bits)
        if digest in seen:
            return CollisionResult(seen[digest], candidate, digest, counter + 1)
        seen[digest] = candidate
    raise TimeoutError(f"no {bits}-bit collision in {max_trials} trials")
