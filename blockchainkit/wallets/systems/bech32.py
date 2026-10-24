r"""Bech32 addresses (Wuille and Maxwell, BIP173, 2017) and Bech32m (Wuille, BIP350, 2020).

A Bech32 string is a human-readable part such as ``bc``, the separator
``1``, and data in 32 lower-case characters chosen to avoid look-alikes,
ending in a 6-character checksum. The checksum is a BCH code over GF(32):
the data and checksum, read as a polynomial with 5-bit coefficients, must
leave a fixed remainder modulo a generator g(x) of degree 6,

.. math::

   \mathrm{polymod}(\mathrm{expand}(hrp) \,\|\, data \,\|\, checksum) = 1 .

g(x) was chosen by a search of 159,605 BCH codes for the best detection of
the errors people make: every error affecting at most 4 characters is
detected in strings of up to 89 characters, which Base58Check's 32-bit hash
cannot promise.

In 2019 a weakness was found: when a string ends in ``p``, inserting or
deleting ``q`` characters just before it leaves the checksum valid, because
``q`` is the value 0 and the constant 1 lets the polynomial absorb factors
of x. Segregated-witness version 0 survives, since its programs must be 20
or 32 bytes, but later versions allow other lengths. Bech32m changes only
the constant, to ``0x2bc830a3``, and is required from witness version 1
(Taproot) on.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.wallets.core.base import Bech32Decoding, WitnessProgram
from blockchainkit.wallets.utils.keys import PublicKey, compress
from blockchainkit.wallets.utils.ripemd160 import hash160

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
"""str: The 32 data characters; character i has the 5-bit value i."""

BECH32_CONSTANTS = {"bech32": 1, "bech32m": 0x2BC830A3}
"""dict: The value a valid checksum leaves, for each encoding."""

_GENERATOR = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)


def polymod(values: Sequence[int]) -> int:
    """The remainder of a sequence of 5-bit values modulo Bech32's generator polynomial.

    Each step shifts in one value; the five constants are g(x) times 1, 2,
    4, 8 and 16 in GF(32), added for each bit that overflows.
    """
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = (checksum & 0x1FFFFFF) << 5 ^ value
        for i in range(5):
            if top >> i & 1:
                checksum ^= _GENERATOR[i]
    return checksum


def _expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _encoding(encoding: str) -> int:
    if encoding not in BECH32_CONSTANTS:
        raise ValueError(f"encoding must be one of {sorted(BECH32_CONSTANTS)}")
    return BECH32_CONSTANTS[encoding]


def bech32_encode(hrp: str, data: Sequence[int], encoding: str = "bech32") -> str:
    """Write ``hrp``, ``1``, the 5-bit ``data`` and a 6-character checksum.

    Examples
    --------
    >>> from blockchainkit.wallets import bech32_encode
    >>> bech32_encode("a", [])
    'a12uel5l'
    >>> bech32_encode("a", [], "bech32m")
    'a1lqfn3a'
    """
    constant = _encoding(encoding)
    if not isinstance(hrp, str) or not 1 <= len(hrp) <= 83:
        raise ValueError("the human-readable part has 1 to 83 characters")
    if any(not 33 <= ord(c) <= 126 for c in hrp) or hrp.lower() != hrp:
        raise ValueError("the human-readable part is lower-case printable ASCII")
    values = list(data)
    for value in values:
        integer(value, "data value")
        if value > 31:
            raise ValueError("data values are 5 bits")
    if len(hrp) + 7 + len(values) > 90:
        raise ValueError("a Bech32 string has at most 90 characters")
    mod = polymod([*_expand(hrp), *values, 0, 0, 0, 0, 0, 0]) ^ constant
    checksum = [mod >> 5 * (5 - i) & 31 for i in range(6)]
    return hrp + "1" + "".join(CHARSET[v] for v in values + checksum)


def bech32_decode(text: str) -> Bech32Decoding:
    """Check a Bech32 or Bech32m string and split it into its parts.

    Raises
    ------
    ValueError
        Mixed case, a bad character or length, no separator, or a checksum
        that matches neither encoding.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if text.lower() != text and text.upper() != text:
        raise ValueError("mixed case")
    if len(text) > 90 or any(not 33 <= ord(c) <= 126 for c in text):
        raise ValueError("at most 90 printable ASCII characters")
    text = text.lower()
    split = text.rfind("1")
    if split < 1 or split + 7 > len(text):
        raise ValueError("needs a human-readable part, 1, and at least 6 data characters")
    hrp, part = text[:split], text[split + 1 :]
    if any(c not in CHARSET for c in part):
        raise ValueError("a data character is not in the Bech32 alphabet")
    values = [CHARSET.index(c) for c in part]
    remainder = polymod(_expand(hrp) + values)
    for encoding, constant in BECH32_CONSTANTS.items():
        if remainder == constant:
            return Bech32Decoding(hrp, tuple(values[:-6]), encoding)
    raise ValueError("checksum mismatch: the string was mistyped")


def convert_bits(
    data: Sequence[int], source: int, target: int, pad: bool = True
) -> tuple[int, ...]:
    """Regroup a sequence of ``source``-bit values into ``target``-bit values.

    With ``pad``, the last group is filled with zero bits; without, leftover
    bits must be fewer than ``target`` and zero.
    """
    accumulator, bits, out = 0, 0, []
    for value in data:
        if not 0 <= value < 1 << source:
            raise ValueError(f"values must be {source}-bit")
        accumulator = accumulator << source | value
        bits += source
        while bits >= target:
            bits -= target
            out.append(accumulator >> bits & (1 << target) - 1)
    if pad and bits:
        out.append(accumulator << (target - bits) & (1 << target) - 1)
    elif not pad and (bits >= source or accumulator << (target - bits) & (1 << target) - 1):
        raise ValueError("leftover padding bits")
    return tuple(out)


def segwit_encode(hrp: str, version: int, program: bytes) -> str:
    """A segregated-witness address: Bech32 for version 0, Bech32m from version 1.

    Examples
    --------
    >>> from blockchainkit.wallets import segwit_encode
    >>> segwit_encode("bc", 0, bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6"))
    'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'
    """
    _check_program(version, program)
    encoding = "bech32" if version == 0 else "bech32m"
    return bech32_encode(hrp, [version, *convert_bits(program, 8, 5)], encoding)


def segwit_decode(hrp: str, address: str) -> WitnessProgram:
    """Decode and check a segregated-witness address for network ``hrp``.

    Raises
    ------
    ValueError
        The checksum fails, the network differs, the program has a bad
        length, or the encoding does not match the version.
    """
    decoded = bech32_decode(address)
    if decoded.hrp != hrp:
        raise ValueError(f"address is for {decoded.hrp!r}, not {hrp!r}")
    if not decoded.data:
        raise ValueError("no witness version")
    version = decoded.data[0]
    program = bytes(convert_bits(decoded.data[1:], 5, 8, pad=False))
    _check_program(version, program)
    expected = "bech32" if version == 0 else "bech32m"
    if decoded.encoding != expected:
        raise ValueError(f"witness version {version} must use {expected}")
    return WitnessProgram(version, program)


def _check_program(version: int, program: bytes) -> None:
    integer(version, "version")
    if version > 16:
        raise ValueError("witness versions run from 0 to 16")
    if not isinstance(program, bytes) or not 2 <= len(program) <= 40:
        raise ValueError("a witness program has 2 to 40 bytes")
    if version == 0 and len(program) not in (20, 32):
        raise ValueError("a version-0 program is 20 or 32 bytes")


def p2wpkh_address(public: PublicKey, hrp: str = "bc") -> str:
    """The native segregated-witness address of a key: version 0 and its ``HASH160``.

    Examples
    --------
    >>> from blockchainkit.crypto import SECP256K1
    >>> from blockchainkit.wallets import p2wpkh_address
    >>> p2wpkh_address(SECP256K1.generator)
    'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'
    """
    return segwit_encode(hrp, 0, hash160(compress(public)))
