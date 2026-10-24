"""Compressed secp256k1 public keys (SEC 1, section 2.3.3).

A point (x, y) on secp256k1 is fixed by x and the parity of y, since y and
p - y are the two square roots of x**3 + 7. The compressed encoding is one
byte, 0x02 for even y or 0x03 for odd, then x in 32 bytes: 33 bytes instead
of the 65 of :func:`~blockchainkit.crypto.systems.curves.encode_point`.
Bitcoin wallets have used it since 2012, and BIP32 requires it.
"""

from blockchainkit.crypto.systems.curves import SECP256K1

PublicKey = tuple[int, int]


def compress(public: PublicKey) -> bytes:
    """Encode a secp256k1 point in 33 bytes: its y parity, then x.

    Examples
    --------
    >>> from blockchainkit.crypto import SECP256K1
    >>> from blockchainkit.wallets.utils import compress
    >>> compress(SECP256K1.generator).hex()[:10]
    '0279be667e'
    """
    if public is None or not SECP256K1.contains(public):
        raise ValueError("expected a finite point on secp256k1")
    x, y = public
    return bytes([2 + (y & 1)]) + x.to_bytes(32, "big")


def decompress(data: bytes) -> PublicKey:
    """Recover the point from its 33-byte compressed encoding.

    secp256k1's prime is 3 modulo 4, so a square root of ``a`` is
    ``a ** ((p + 1) / 4)``.

    Raises
    ------
    ValueError
        The bytes are not 33 long, start with neither 0x02 nor 0x03, or name
        an x with no point above it.
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if len(data) != 33 or data[0] not in (2, 3):
        raise ValueError("a compressed key is 0x02 or 0x03 and 32 bytes of x")
    p = SECP256K1.p
    x = int.from_bytes(data[1:], "big")
    if x >= p:
        raise ValueError("x is not a field element")
    square = (pow(x, 3, p) + SECP256K1.b) % p
    y = pow(square, (p + 1) // 4, p)
    if y * y % p != square:
        raise ValueError("no point on secp256k1 has this x")
    if y & 1 != data[0] & 1:
        y = p - y
    return x, y
