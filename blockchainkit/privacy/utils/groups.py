"""Hashing into the teaching group, and a hash keystream for layered encryption.

Every construction of :mod:`blockchainkit.privacy` works in
:data:`~blockchainkit.crypto.systems.asymmetric.TEACHING_GROUP`, the order-q
subgroup modulo a 62-bit safe prime, written multiplicatively: a public key
is ``g**x mod p`` where elliptic-curve papers write ``xG``.
"""

from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.utils.encoding import canonical_json


def hash_to_scalar(domain: bytes, *values: object, group: DHGroup = TEACHING_GROUP) -> int:
    """Hash a domain tag, the group and ``values`` to an integer modulo q.

    The values are framed with canonical JSON, so ``(1, 23)`` and ``(12, 3)``
    hash differently.

    >>> from blockchainkit.privacy import hash_to_scalar
    >>> hash_to_scalar(b"demo", 1, 23) != hash_to_scalar(b"demo", 12, 3)
    True
    """
    framed = domain + canonical_json([group.p, group.q, group.g, *values])
    return int.from_bytes(sha256(framed), "big") % group.q


def hash_to_group(domain: bytes, *values: object, group: DHGroup = TEACHING_GROUP) -> int:
    """Hash ``values`` to an element of the order-q subgroup whose log nobody knows.

    Squaring modulo the safe prime ``p = 2q + 1`` maps any nonzero residue
    into the subgroup; a degenerate result is hashed again with a counter.
    """
    counter = 0
    while True:
        framed = domain + canonical_json([group.p, group.q, group.g, counter, *values])
        candidate = int.from_bytes(sha256(framed), "big") % group.p
        element = pow(candidate, (group.p - 1) // group.q, group.p)
        if element not in (0, 1):
            return element
        counter += 1  # Probability about 2/p: hash again.


def keystream_xor(key: int, data: bytes, domain: bytes) -> bytes:
    """Encrypt or decrypt ``data`` by XOR with the SHA-256 keystream of ``key``.

    The same call undoes itself. A teaching stand-in for a stream cipher:
    there is no authentication tag.

    >>> from blockchainkit.privacy import keystream_xor
    >>> sealed = keystream_xor(42, b"attack at dawn", b"demo")
    >>> keystream_xor(42, sealed, b"demo")
    b'attack at dawn'
    """
    blocks = (len(data) + 31) // 32
    stream = b"".join(sha256(domain + f"{key}:{i}".encode()) for i in range(blocks))
    return bytes(a ^ b for a, b in zip(data, stream, strict=False))
