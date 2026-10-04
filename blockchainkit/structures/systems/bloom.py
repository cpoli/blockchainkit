"""Bloom filters (1970): compact set membership with false positives but no false negatives.

Bitcoin's lightweight clients (BIP 37, 2012) sent full nodes a Bloom filter
of their addresses, so nodes could forward matching transactions without
the client listing its addresses outright. The false positives were meant
to give privacy; in practice they leaked much of it.
"""

from math import exp, log

from blockchainkit._validation import integer
from blockchainkit.constants import BLOOM_DOMAIN
from blockchainkit.crypto.systems.hashing import sha256


class BloomFilter:
    """An array of ``size`` bits, set at ``hashes`` positions per added item.

    An item is reported present if all its positions are set. Items that
    were added are always found; others are wrongly found with probability
    about ``(1 - exp(-k n / m))**k``.

    Parameters
    ----------
    size : int
        Number of bits m.
    hashes : int
        Number of positions k per item.

    Examples
    --------
    >>> from blockchainkit.structures import BloomFilter
    >>> bloom = BloomFilter(256, 3)
    >>> bloom.add(b"alice")
    >>> b"alice" in bloom
    True
    """

    def __init__(self, size: int, hashes: int) -> None:
        integer(size, "size", 1)
        integer(hashes, "hashes", 1)
        self._size, self._hashes = size, hashes
        self._bits = bytearray((size + 7) // 8)
        self._count = 0

    def _positions(self, item: bytes) -> list[int]:
        if not isinstance(item, bytes):
            raise TypeError("items must be bytes")
        return [
            int.from_bytes(sha256(BLOOM_DOMAIN + i.to_bytes(4, "big") + item), "big") % self._size
            for i in range(self._hashes)
        ]

    def add(self, item: bytes) -> None:
        """Set the item's bit positions."""
        for position in self._positions(item):
            self._bits[position // 8] |= 1 << (position % 8)
        self._count += 1

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, bytes):
            return False
        return all(self._bits[p // 8] >> (p % 8) & 1 for p in self._positions(item))

    def __len__(self) -> int:
        return self._count

    @property
    def fill_ratio(self) -> float:
        """Fraction of bits set."""
        return sum(bin(byte).count("1") for byte in self._bits) / self._size

    @staticmethod
    def false_positive_rate(size: int, hashes: int, items: int) -> float:
        """Return Bloom's estimate ``(1 - exp(-k n / m))**k``."""
        return float((1 - exp(-hashes * items / size)) ** hashes)

    @staticmethod
    def optimal_hash_count(size: int, items: int) -> int:
        """Return the k minimizing false positives, ``round((m / n) ln 2)``."""
        return max(1, round(size / items * log(2)))
