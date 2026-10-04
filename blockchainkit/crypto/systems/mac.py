"""Message authentication codes: the naive secret-prefix hash, and HMAC (1996)."""

import hashlib
import hmac

from blockchainkit.crypto.systems.hashing import sha256


def naive_mac(key: bytes, message: bytes) -> bytes:
    """Return SHA-256(key || message): a tempting MAC that is *broken*.

    Anyone holding a tag can forge the tag of ``message || glue || suffix``
    with :func:`~blockchainkit.crypto.systems.merkle_damgard.length_extension`.
    Shown for contrast with :func:`hmac_sha256`; never use it.
    """
    if not isinstance(key, bytes) or not isinstance(message, bytes):
        raise TypeError("key and message must be bytes")
    return sha256(key + message)


def hmac_sha256(key: bytes, message: bytes) -> bytes:
    """Return HMAC-SHA256(key, message) (Bellare, Canetti and Krawczyk, 1996).

    HMAC hashes twice with two derived keys,
    ``H((k XOR opad) || H((k XOR ipad) || m))``. The outer hash hides the
    inner chaining state, so length extension no longer works.

    >>> from blockchainkit.crypto import hmac_sha256
    >>> hmac_sha256(b"key", b"The quick brown fox jumps over the lazy dog").hex()[:16]
    'f7bc83f430538424'
    """
    if not isinstance(key, bytes) or not isinstance(message, bytes):
        raise TypeError("key and message must be bytes")
    return hmac.new(key, message, hashlib.sha256).digest()
