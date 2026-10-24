r"""Base58Check addresses (Nakamoto, 2009).

A Bitcoin address is a version byte and the 20-byte ``HASH160`` of a public
key, followed by a 4-byte checksum, the first bytes of
``SHA256(SHA256(version || payload))``, and written in base 58. The alphabet
leaves out 0, O, I and l, which look alike, and every leading zero byte
becomes a leading ``1``. A mistyped address fails the checksum unless the
typo happens to match it, with probability

.. math::

   2^{-32} \approx 2.3 \times 10^{-10},

so a wallet refuses to pay it. The checksum detects errors but cannot say
where they are. :mod:`blockchainkit.structures` names accounts by a bare
SHA-256 hex digest, where every typo is another valid address.
"""

from blockchainkit._validation import integer
from blockchainkit.crypto.systems.curves import encode_point
from blockchainkit.crypto.systems.hashing import hash256
from blockchainkit.wallets.utils.keys import PublicKey, compress
from blockchainkit.wallets.utils.ripemd160 import hash160

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
"""str: Bitcoin's base-58 digits: the alphanumerics without 0, O, I and l."""

P2PKH_VERSION = 0x00
"""int: Version byte of a pay-to-public-key-hash address (starts with 1)."""

P2SH_VERSION = 0x05
"""int: Version byte of a pay-to-script-hash address (starts with 3)."""


def base58_encode(data: bytes) -> str:
    """Write bytes in base 58, one ``1`` per leading zero byte.

    Examples
    --------
    >>> from blockchainkit.wallets import base58_encode
    >>> base58_encode(b"hello world")
    'StV1DL6CwTryKyV'
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    value = int.from_bytes(data, "big")
    digits = ""
    while value:
        value, remainder = divmod(value, 58)
        digits = ALPHABET[remainder] + digits
    return "1" * (len(data) - len(data.lstrip(b"\x00"))) + digits


def base58_decode(text: str) -> bytes:
    """Read base 58 back into bytes.

    Raises
    ------
    ValueError
        A character is not a base-58 digit.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    value = 0
    for character in text:
        index = ALPHABET.find(character)
        if index < 0:
            raise ValueError(f"{character!r} is not a base-58 digit")
        value = 58 * value + index
    body = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(text) - len(text.lstrip("1"))) + body


def base58check_encode(version: int, payload: bytes) -> str:
    """Base58Check: the version byte, the payload, and a 4-byte double-SHA-256 checksum."""
    integer(version, "version")
    if version > 255:
        raise ValueError("version is one byte")
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    data = bytes([version]) + payload
    return base58_encode(data + hash256(data)[:4])


def base58check_decode(text: str) -> tuple[int, bytes]:
    """Check and remove the checksum; return the version byte and the payload.

    Raises
    ------
    ValueError
        The string is not base 58, is too short, or fails its checksum.
    """
    data = base58_decode(text)
    if len(data) < 5:
        raise ValueError("too short for a version byte and a checksum")
    body, checksum = data[:-4], data[-4:]
    if hash256(body)[:4] != checksum:
        raise ValueError("checksum mismatch: the address was mistyped")
    return body[0], body[1:]


def p2pkh_address(public: PublicKey, compressed: bool = True) -> str:
    """The Bitcoin address of a public key: Base58Check of version 0 and its ``HASH160``.

    Wallets before 2012 hashed the 65-byte uncompressed key, so the same
    key has two addresses.

    Examples
    --------
    >>> from blockchainkit.crypto import SECP256K1
    >>> from blockchainkit.wallets import p2pkh_address
    >>> p2pkh_address(SECP256K1.generator)  # the key of private key 1
    '1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH'
    """
    encoded = compress(public) if compressed else encode_point(public)
    return base58check_encode(P2PKH_VERSION, hash160(encoded))


def is_valid_address(text: str) -> bool:
    """True if ``text`` is a Base58Check string with a 20-byte payload and a known version."""
    try:
        version, payload = base58check_decode(text)
    except (TypeError, ValueError):
        return False
    return version in (P2PKH_VERSION, P2SH_VERSION) and len(payload) == 20
