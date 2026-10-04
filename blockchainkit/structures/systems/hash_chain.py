"""Lamport's hash chains (1981): one-time passwords from repeated hashing.

Hash a secret seed n times. The server stores only the last link. To log in,
the user reveals the link before it; the server hashes it once, compares,
and stores the revealed link as the new anchor. An eavesdropper who captures
a password learns a value the server will never accept again, and cannot
compute the next one without inverting the hash. This became S/KEY (1995).
"""

import hmac

from blockchainkit._validation import integer
from blockchainkit.crypto.systems.hashing import sha256


def hash_chain(seed: bytes, length: int) -> tuple[bytes, ...]:
    """Return ``(H(seed), H(H(seed)), ..., H^length(seed))``.

    >>> from blockchainkit.structures import hash_chain
    >>> len(hash_chain(b"seed", 3))
    3
    """
    if not isinstance(seed, bytes):
        raise TypeError("seed must be bytes")
    integer(length, "length", 1)
    links, current = [], seed
    for _ in range(length):
        current = sha256(current)
        links.append(current)
    return tuple(links)


def verify_one_time_password(password: bytes, anchor: bytes) -> bool:
    """Return whether ``H(password)`` equals the stored anchor (constant-time)."""
    return isinstance(password, bytes) and hmac.compare_digest(sha256(password), anchor)
