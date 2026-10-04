"""SHA-256 written out as a Merkle-Damgard iteration, and its length-extension flaw.

Merkle and Damgard (1989) showed how to hash messages of any length with a
fixed-size compression function: pad the message to whole blocks, ending with
its length, then chain ``state = compress(state, block)`` from a fixed initial
value. The digest *is* the final state. So anyone who knows ``H(m)`` and
``len(m)`` can keep compressing from it and compute ``H(m || pad || suffix)``
without knowing ``m``: the length-extension attack. HMAC exists to stop it.

This is a readable implementation for study. Use :func:`hashlib.sha256` (or
:func:`blockchainkit.crypto.systems.hashing.sha256`) for real hashing.
"""

from blockchainkit._validation import integer

SHA256_IV = (
    0x6A09E667,
    0xBB67AE85,
    0x3C6EF372,
    0xA54FF53A,
    0x510E527F,
    0x9B05688C,
    0x1F83D9AB,
    0x5BE0CD19,
)
"""tuple of int: The initial chaining value (FIPS 180-4, section 5.3.3)."""

# Round constants: the first 32 bits of the fractional parts of the cube
# roots of the first 64 primes (FIPS 180-4, section 4.2.2).
_K = (
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
    0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3, 0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
    0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
    0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13, 0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
    0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
    0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208, 0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
)  # fmt: skip
_MASK = 0xFFFFFFFF


def _rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & _MASK


def sha256_compress(state: tuple[int, ...], block: bytes) -> tuple[int, ...]:
    """Apply SHA-256's compression function to one 64-byte block.

    Parameters
    ----------
    state : tuple of int
        Eight 32-bit words: :data:`SHA256_IV` or the previous output.
    block : bytes
        Exactly 64 bytes.

    Returns
    -------
    tuple of int
        The next chaining state.
    """
    if not isinstance(block, bytes) or len(block) != 64:
        raise ValueError("a SHA-256 block is 64 bytes")
    if len(state) != 8:
        raise ValueError("a SHA-256 state is eight 32-bit words")
    w = [int.from_bytes(block[4 * i : 4 * i + 4], "big") for i in range(16)]
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & _MASK)
    a, b, c, d, e, f, g, h = state
    for i in range(64):
        t1 = h + (_rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)) + ((e & f) ^ (~e & g)) + _K[i] + w[i]
        t2 = (_rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))
        a, b, c, d, e, f, g, h = (t1 + t2) & _MASK, a, b, c, (d + t1) & _MASK, e, f, g
    return tuple((x + y) & _MASK for x, y in zip(state, (a, b, c, d, e, f, g, h), strict=True))


def sha256_padding(message_length: int) -> bytes:
    """Return the Merkle-Damgard strengthening for a message of that many bytes.

    A 0x80 byte, zeros up to 56 bytes modulo 64, then the bit length as a
    64-bit big-endian integer. Encoding the length is what makes the
    construction collision-resistant whenever the compression function is.
    """
    integer(message_length, "message_length")
    zeros = (55 - message_length) % 64
    return b"\x80" + bytes(zeros) + (8 * message_length).to_bytes(8, "big")


def _iterate(state: tuple[int, ...], data: bytes) -> tuple[int, ...]:
    for start in range(0, len(data), 64):
        state = sha256_compress(state, data[start : start + 64])
    return state


def _digest(state: tuple[int, ...]) -> bytes:
    return b"".join(word.to_bytes(4, "big") for word in state)


def merkle_damgard_sha256(data: bytes) -> bytes:
    """Hash by padding, then chaining the compression function from the IV.

    >>> import hashlib
    >>> from blockchainkit.crypto import merkle_damgard_sha256
    >>> merkle_damgard_sha256(b"abc") == hashlib.sha256(b"abc").digest()
    True
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    return _digest(_iterate(SHA256_IV, data + sha256_padding(len(data))))


def length_extension(digest: bytes, original_length: int, suffix: bytes) -> tuple[bytes, bytes]:
    """Extend ``H(original)`` to ``H(original || glue || suffix)`` without knowing ``original``.

    Parameters
    ----------
    digest : bytes
        SHA-256 of the unknown original message.
    original_length : int
        Its length in bytes (for a secret-prefix MAC, key plus message).
    suffix : bytes
        Data the attacker wants to append.

    Returns
    -------
    tuple of bytes
        ``(glue, forged)``: the original message's padding, which becomes
        part of the forged message, and ``SHA-256(original || glue || suffix)``.
    """
    if not isinstance(digest, bytes) or len(digest) != 32:
        raise ValueError("a SHA-256 digest is 32 bytes")
    if not isinstance(suffix, bytes):
        raise TypeError("suffix must be bytes")
    glue = sha256_padding(original_length)
    state = tuple(int.from_bytes(digest[4 * i : 4 * i + 4], "big") for i in range(8))
    total = original_length + len(glue) + len(suffix)
    return glue, _digest(_iterate(state, suffix + sha256_padding(total)))
