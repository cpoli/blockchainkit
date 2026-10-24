"""RIPEMD-160 (Dobbertin, Bosselaers and Preneel, 1996), and Bitcoin's HASH160.

Bitcoin names a key or a script by ``RIPEMD160(SHA256(data))``, a 20-byte
digest. ``hashlib`` offers RIPEMD-160 only when the OpenSSL it was built
with does, which OpenSSL 3 and Pyodide do not by default, so it is written
out here from the specification. Two parallel lines of 80 steps each mix
the 16 message words in different orders, and their results are combined.
"""

from blockchainkit.crypto.systems.hashing import sha256

_MASK = 0xFFFFFFFF

_INITIAL = (0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0)

_LEFT_WORDS = (
    *range(16),
    *(7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8),
    *(3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12),
    *(1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2),
    *(4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13),
)
_RIGHT_WORDS = (
    *(5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12),
    *(6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2),
    *(15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13),
    *(8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14),
    *(12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11),
)
_LEFT_SHIFTS = (
    *(11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8),
    *(7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12),
    *(11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5),
    *(11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12),
    *(9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6),
)
_RIGHT_SHIFTS = (
    *(8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6),
    *(9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11),
    *(9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5),
    *(15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8),
    *(8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11),
)
_LEFT_CONSTANTS = (0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E)
_RIGHT_CONSTANTS = (0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0x00000000)


def _rotate(x: int, n: int) -> int:
    return ((x << n) | (x >> (32 - n))) & _MASK


def _mix(round_: int, x: int, y: int, z: int) -> int:
    if round_ == 0:
        return x ^ y ^ z
    if round_ == 1:
        return (x & y) | (~x & z)
    if round_ == 2:
        return (x | ~y) ^ z
    if round_ == 3:
        return (x & z) | (y & ~z)
    return x ^ (y | ~z)


def _compress(state: list[int], block: bytes) -> None:
    words = [int.from_bytes(block[4 * i : 4 * i + 4], "little") for i in range(16)]
    a, b, c, d, e = state
    a2, b2, c2, d2, e2 = state
    for j in range(80):
        r = j // 16
        t = a + _mix(r, b, c, d) + words[_LEFT_WORDS[j]] + _LEFT_CONSTANTS[r]
        t = (_rotate(t & _MASK, _LEFT_SHIFTS[j]) + e) & _MASK
        a, e, d, c, b = e, d, _rotate(c, 10), b, t
        t = a2 + _mix(4 - r, b2, c2, d2) + words[_RIGHT_WORDS[j]] + _RIGHT_CONSTANTS[r]
        t = (_rotate(t & _MASK, _RIGHT_SHIFTS[j]) + e2) & _MASK
        a2, e2, d2, c2, b2 = e2, d2, _rotate(c2, 10), b2, t
    state[:] = [
        (state[1] + c + d2) & _MASK,
        (state[2] + d + e2) & _MASK,
        (state[3] + e + a2) & _MASK,
        (state[4] + a + b2) & _MASK,
        (state[0] + b + c2) & _MASK,
    ]


def ripemd160(data: bytes) -> bytes:
    """Return the 20-byte RIPEMD-160 digest of ``data``.

    Examples
    --------
    >>> from blockchainkit.wallets.utils import ripemd160
    >>> ripemd160(b"abc").hex()
    '8eb208f7e05d987a9b044a8e98c6b087f15a0bfc'
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    padded = data + b"\x80" + b"\x00" * ((55 - len(data)) % 64)
    padded += (8 * len(data) % 2**64).to_bytes(8, "little")
    state = list(_INITIAL)
    for start in range(0, len(padded), 64):
        _compress(state, padded[start : start + 64])
    return b"".join(word.to_bytes(4, "little") for word in state)


def hash160(data: bytes) -> bytes:
    """Bitcoin's ``HASH160``: RIPEMD-160 of SHA-256, the 20 bytes inside an address.

    Examples
    --------
    >>> from blockchainkit.wallets.utils import hash160
    >>> len(hash160(b"key"))
    20
    """
    return ripemd160(sha256(data))
