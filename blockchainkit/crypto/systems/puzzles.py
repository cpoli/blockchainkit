"""Merkle's puzzles (1974-1978): key agreement from symmetric primitives alone.

Alice publishes ``count`` puzzles, each a short secret (an identifier and a
session key) encrypted under a deliberately weak key of ``bits`` bits. Bob
solves one at random, about ``2**(bits-1)`` trials, and announces only its
identifier. An eavesdropper does not know which puzzle Bob chose and must
solve, on average, half of them. With ``count`` near ``2**bits``, honest work
is linear and the attacker's quadratic: the first public-key idea, with a
gap that is only polynomial.
"""

import secrets
from collections.abc import Callable

from blockchainkit._validation import integer
from blockchainkit.constants import PUZZLE_DOMAIN, PUZZLE_MAGIC
from blockchainkit.crypto.core.base import PuzzleSolution
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.one_time_pad import xor_bytes

_MAX_BITS = 24


def _keystream(weak_key: int) -> bytes:
    return sha256(PUZZLE_DOMAIN + weak_key.to_bytes(8, "big"))


def merkle_puzzles(
    count: int,
    bits: int,
    *,
    randbits: Callable[[int], int] = secrets.randbits,
) -> tuple[tuple[bytes, ...], dict[bytes, bytes]]:
    """Create Alice's puzzles and her private table of identifiers to keys.

    Parameters
    ----------
    count : int
        Number of puzzles to publish.
    bits : int
        Size of each weak key, between 1 and 24; solving takes up to
        ``2**bits`` trials.
    randbits : callable
        Randomness source; inject ``random.Random(seed).getrandbits`` only
        for reproducible experiments.

    Returns
    -------
    tuple
        ``(puzzles, table)``: 32-byte puzzles to publish, and the mapping
        from each 8-byte identifier to its 16-byte session key.
    """
    integer(count, "count", 1)
    integer(bits, "bits", 1)
    if bits > _MAX_BITS:
        raise ValueError(f"bits must be at most {_MAX_BITS} to keep solving bounded")
    puzzles, table = [], {}
    for _ in range(count):
        puzzle_id = randbits(64).to_bytes(8, "big")
        key = randbits(128).to_bytes(16, "big")
        weak_key = randbits(bits)
        puzzles.append(xor_bytes(PUZZLE_MAGIC + puzzle_id + key, _keystream(weak_key)))
        table[puzzle_id] = key
    return tuple(puzzles), table


def solve_puzzle(puzzle: bytes, bits: int) -> PuzzleSolution:
    """Open a puzzle by brute force over every weak key.

    A trial succeeds when the decrypted plaintext starts with the known
    marker, ``PUZZLE_MAGIC``.

    Raises
    ------
    ValueError
        No weak key of that size opens the puzzle.

    Examples
    --------
    >>> from random import Random
    >>> from blockchainkit.crypto import merkle_puzzles, solve_puzzle
    >>> puzzles, table = merkle_puzzles(3, 6, randbits=Random(1).getrandbits)
    >>> solution = solve_puzzle(puzzles[0], bits=6)
    >>> table[solution.puzzle_id] == solution.key
    True
    """
    if not isinstance(puzzle, bytes) or len(puzzle) != 32:
        raise ValueError("a puzzle is 32 bytes")
    integer(bits, "bits", 1)
    if bits > _MAX_BITS:
        raise ValueError(f"bits must be at most {_MAX_BITS} to keep solving bounded")
    for weak_key in range(2**bits):
        plaintext = xor_bytes(puzzle, _keystream(weak_key))
        if plaintext.startswith(PUZZLE_MAGIC):
            return PuzzleSolution(plaintext[8:16], plaintext[16:], weak_key + 1)
    raise ValueError("no weak key of that size opens this puzzle")
