r"""scrypt, a sequential memory-hard key derivation function (Percival, 2009).

PBKDF2 makes each guess slow, but a guess needs almost no memory, so an
attacker with custom chips runs millions of guesses side by side. scrypt
makes each guess need a large table as well. ROMix fills a table V of N
blocks, each the BlockMix of the last, then makes N reads at addresses that
depend on the data:

.. math::

   V_i = \mathrm{BlockMix}^{\,i}(B), \qquad
   X \leftarrow \mathrm{BlockMix}(X \oplus V_{\mathrm{Integerify}(X) \bmod N}).

An attacker can store fewer entries and recompute the missing ones, but
keeping only every k-th entry multiplies the second loop's work by about
(k + 1)/2: memory times time stays roughly constant. Percival proved that no
algorithm does much better, so the cost of an attack in chip area and time
grows with N squared. BlockMix is built from the Salsa20/8 core. This module
implements RFC 7914 exactly, and :func:`romix` adds the trade-off.
"""

from blockchainkit._validation import integer
from blockchainkit.wallets.core.base import RomixCost
from blockchainkit.wallets.systems.stretching import pbkdf2

_MASK = 0xFFFFFFFF
_QUARTER_ROUNDS = (
    (4, 0, 12, 7),
    (8, 4, 0, 9),
    (12, 8, 4, 13),
    (0, 12, 8, 18),
    (9, 5, 1, 7),
    (13, 9, 5, 9),
    (1, 13, 9, 13),
    (5, 1, 13, 18),
    (14, 10, 6, 7),
    (2, 14, 10, 9),
    (6, 2, 14, 13),
    (10, 6, 2, 18),
    (3, 15, 11, 7),
    (7, 3, 15, 9),
    (11, 7, 3, 13),
    (15, 11, 7, 18),
    (1, 0, 3, 7),
    (2, 1, 0, 9),
    (3, 2, 1, 13),
    (0, 3, 2, 18),
    (6, 5, 4, 7),
    (7, 6, 5, 9),
    (4, 7, 6, 13),
    (5, 4, 7, 18),
    (11, 10, 9, 7),
    (8, 11, 10, 9),
    (9, 8, 11, 13),
    (10, 9, 8, 18),
    (12, 15, 14, 7),
    (13, 12, 15, 9),
    (14, 13, 12, 13),
    (15, 14, 13, 18),
)
"""Each step ``x[a] ^= rotl(x[b] + x[c], shift)``: a column round, then a row round."""


def salsa20_8(block: bytes) -> bytes:
    """The Salsa20/8 core: 8 rounds on sixteen 32-bit words, added back to the input.

    Examples
    --------
    >>> from blockchainkit.wallets import salsa20_8
    >>> salsa20_8(bytes(64)) == bytes(64)
    True
    """
    if not isinstance(block, bytes) or len(block) != 64:
        raise ValueError("block must be 64 bytes")
    words = [int.from_bytes(block[4 * i : 4 * i + 4], "little") for i in range(16)]
    x = list(words)
    for _ in range(4):
        for a, b, c, shift in _QUARTER_ROUNDS:
            s = (x[b] + x[c]) & _MASK
            x[a] ^= ((s << shift) | (s >> (32 - shift))) & _MASK
    return b"".join(((x[i] + words[i]) & _MASK).to_bytes(4, "little") for i in range(16))


def _xor(left: bytes, right: bytes) -> bytes:
    return (int.from_bytes(left, "little") ^ int.from_bytes(right, "little")).to_bytes(
        len(left), "little"
    )


def block_mix(block: bytes) -> bytes:
    """scrypt's BlockMix: chain Salsa20/8 through the 2r 64-byte pieces of a block.

    The outputs are interleaved: even-numbered results first, then odd.
    """
    if not isinstance(block, bytes) or not block or len(block) % 128:
        raise ValueError("a block is 128 * r bytes")
    pieces = [block[i : i + 64] for i in range(0, len(block), 64)]
    x = pieces[-1]
    out = []
    for piece in pieces:
        x = salsa20_8(_xor(x, piece))
        out.append(x)
    return b"".join(out[0::2] + out[1::2])


def romix(block: bytes, n: int, keep_every: int = 1) -> tuple[bytes, RomixCost]:
    """scrypt's ROMix, storing only every ``keep_every``-th table entry.

    A missing entry ``V_j`` is recomputed from the stored ``V_{j - j mod k}``.
    The output is the same for every ``keep_every``; only the cost changes.

    Parameters
    ----------
    block : bytes
        128 * r bytes.
    n : int
        The cost parameter N, a power of two above 1.
    keep_every : int
        k: 1 is scrypt as specified; N stores only the first entry.

    Returns
    -------
    tuple
        The mixed block, and a :class:`~blockchainkit.wallets.core.base.RomixCost`.

    Examples
    --------
    >>> from blockchainkit.wallets import romix
    >>> fast, cost = romix(bytes(range(128)), 64)
    >>> slow, frugal = romix(bytes(range(128)), 64, keep_every=8)
    >>> fast == slow, cost.stored, frugal.stored, cost.block_mixes < frugal.block_mixes
    (True, 64, 8, True)
    """
    integer(n, "n", 2)
    if n & (n - 1):
        raise ValueError("n must be a power of two")
    integer(keep_every, "keep_every", 1)
    if keep_every > n:
        raise ValueError("keep_every is at most n")
    x = block
    table = {}
    mixes = 0
    for i in range(n):
        if i % keep_every == 0:
            table[i] = x
        x = block_mix(x)
        mixes += 1
    r = len(block) // 128
    for _ in range(n):
        j = int.from_bytes(x[-64:-56], "little") % n
        v = table[j - j % keep_every]
        for _ in range(j % keep_every):
            v = block_mix(v)
            mixes += 1
        x = block_mix(_xor(x, v))
        mixes += 1
    return x, RomixCost(n, r, len(table), mixes)


def scrypt(password: bytes, salt: bytes, n: int, r: int, p: int, length: int) -> bytes:
    """scrypt (RFC 7914): PBKDF2, then ROMix on each of p blocks, then PBKDF2 again.

    Parameters
    ----------
    password, salt : bytes
        The secret and a per-user random value.
    n : int
        CPU and memory cost: a power of two above 1.
    r : int
        Block size: each table entry is 128 * r bytes.
    p : int
        Parallelization: independent ROMix runs.
    length : int
        Output bytes.

    Examples
    --------
    >>> from blockchainkit.wallets import scrypt
    >>> scrypt(b"", b"", 16, 1, 1, 64).hex()[:16]  # RFC 7914, section 12
    '77d6576238657b20'
    """
    integer(r, "r", 1)
    integer(p, "p", 1)
    width = 128 * r
    blocks = pbkdf2(password, salt, 1, p * width)
    mixed = b"".join(romix(blocks[i : i + width], n)[0] for i in range(0, p * width, width))
    return pbkdf2(password, mixed, 1, length)
