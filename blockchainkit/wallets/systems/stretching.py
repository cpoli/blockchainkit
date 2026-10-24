r"""PBKDF2 key stretching (Kaliski, RFC 2898, 2000).

A key derived from a password is only as hard to guess as the password.
Stretching cannot add entropy, but it can make every guess expensive:
PBKDF2 iterates a keyed hash c times, so an attacker trying N passwords pays
about N * c hash calls instead of N, while the honest user pays c once. A
random salt, mixed into the first iteration, stops one precomputed table
from serving every user. Block i of the output is

.. math::

   T_i = U_1 \oplus U_2 \oplus \cdots \oplus U_c, \quad
   U_1 = \mathrm{PRF}(P, S \,\|\, \mathrm{INT}(i)), \quad
   U_j = \mathrm{PRF}(P, U_{j-1}),

with HMAC as the pseudorandom function PRF. BIP39 uses PBKDF2 with
HMAC-SHA512 and 2048 iterations to turn a mnemonic into a seed.
"""

import hashlib
import hmac

from blockchainkit._validation import integer
from blockchainkit.wallets.core.base import CrackResult

PBKDF2_HASHES = ("sha1", "sha256", "sha512")
"""tuple of str: The hash functions :func:`pbkdf2` accepts."""


def pbkdf2(
    password: bytes, salt: bytes, iterations: int, length: int, hash_name: str = "sha256"
) -> bytes:
    """Derive ``length`` bytes from a password with PBKDF2-HMAC (RFC 8018, section 5.2).

    Parameters
    ----------
    password, salt : bytes
        The secret and a per-user random value.
    iterations : int
        c, the number of HMAC calls per output block.
    length : int
        Output bytes.
    hash_name : str
        ``"sha1"``, ``"sha256"`` or ``"sha512"``.

    Examples
    --------
    >>> from blockchainkit.wallets import pbkdf2
    >>> pbkdf2(b"password", b"salt", 1, 20, "sha1").hex()  # RFC 6070
    '0c60c80f961f0e71f3a9b524af6012062fe037a6'
    """
    if not isinstance(password, bytes) or not isinstance(salt, bytes):
        raise TypeError("password and salt must be bytes")
    integer(iterations, "iterations", 1)
    integer(length, "length", 1)
    if hash_name not in PBKDF2_HASHES:
        raise ValueError(f"hash_name must be one of {PBKDF2_HASHES}")
    keyed = hmac.new(password, digestmod=hash_name)
    blocks = []
    for i in range(1, -(-length // keyed.digest_size) + 1):
        mac = keyed.copy()
        mac.update(salt + i.to_bytes(4, "big"))
        u = mac.digest()
        block = int.from_bytes(u, "big")
        for _ in range(iterations - 1):
            mac = keyed.copy()
            mac.update(u)
            u = mac.digest()
            block ^= int.from_bytes(u, "big")
        blocks.append(block.to_bytes(keyed.digest_size, "big"))
    return b"".join(blocks)[:length]


def crack_pin(
    key: bytes, salt: bytes, iterations: int, digits: int, hash_name: str = "sha256"
) -> CrackResult:
    """Try every PIN of ``digits`` digits until one stretches to ``key``.

    The attacker's cost is ``guesses * iterations`` HMAC calls (per output
    block), which is what stretching buys.

    Examples
    --------
    >>> from blockchainkit.wallets import crack_pin, pbkdf2
    >>> key = pbkdf2(b"042", b"salt", 10, 32)
    >>> result = crack_pin(key, b"salt", 10, 3)
    >>> result.secret, result.guesses, result.hash_calls
    ('042', 43, 430)
    """
    if not isinstance(key, bytes) or not key:
        raise ValueError("key must be non-empty bytes")
    integer(digits, "digits", 1)
    if digits > 6:
        raise ValueError("digits is at most 6")
    if hash_name not in PBKDF2_HASHES:
        raise ValueError(f"hash_name must be one of {PBKDF2_HASHES}")
    blocks = -(-len(key) // hashlib.new(hash_name).digest_size)
    for guess in range(10**digits):
        pin = f"{guess:0{digits}d}"
        if pbkdf2(pin.encode(), salt, iterations, len(key), hash_name) == key:
            calls = (guess + 1) * iterations * blocks
            return CrackResult(pin, guess + 1, calls)
    return CrackResult(None, 10**digits, 10**digits * iterations * blocks)
