"""Eclipse attacks on peer selection (Heilman, Kendler, Zohar and Goldberg 2015).

A node picks its outbound connections at random from a table of addresses
it has heard of. An attacker who fills that table with its own addresses
can make every connection land on an attacker: the node is *eclipsed*, and
sees only the blocks and transactions the attacker chooses to show it.

Bitcoin's defense, strengthened after the 2015 paper, is bucketing: an
address goes to a bucket determined by a secret hash of its network group
(its /16 IP prefix), and each group can reach only a few buckets. An
attacker with many addresses but few groups can then fill only a small part
of the table, however many addresses it sends.
"""

from random import Random

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.crypto.systems.hashing import sha256


def eclipse_probability(attacker_fraction: float, outbound: int) -> float:
    """Chance that all ``outbound`` connections land on attackers: ``f ** outbound``.

    Each connection is modeled as an independent draw from a table in which
    a fraction ``f`` of the entries belong to the attacker.

    >>> from blockchainkit.network import eclipse_probability
    >>> eclipse_probability(0.5, 8)
    0.00390625
    """
    probability(attacker_fraction, "attacker_fraction")
    integer(outbound, "outbound", 1)
    return float(attacker_fraction**outbound)


class AddressManager:
    """A node's table of known peer addresses, with optional group bucketing.

    Parameters
    ----------
    buckets : int
        Number of buckets.
    bucket_size : int
        Capacity of each bucket. Adding to a full bucket evicts a random
        entry, so a flood of new addresses pushes old ones out.
    buckets_per_group : int, optional
        If given, each network group can place addresses in only this many
        buckets (Bitcoin's defense). If omitted, an address may land in any
        bucket.
    seed : int
        Seeds both the node's secret bucketing key and its random choices.

    Examples
    --------
    >>> from blockchainkit.network import AddressManager
    >>> table = AddressManager(buckets=4, bucket_size=2, seed=1)
    >>> table.add("10.0.0.1", "10.0")
    >>> table.addresses
    ('10.0.0.1',)
    """

    def __init__(
        self,
        *,
        buckets: int = 64,
        bucket_size: int = 16,
        buckets_per_group: int | None = None,
        seed: int = 0,
    ) -> None:
        integer(buckets, "buckets", 1)
        integer(bucket_size, "bucket_size", 1)
        if buckets_per_group is not None:
            integer(buckets_per_group, "buckets_per_group", 1)
        check_seed(seed)
        self._random = Random(seed)
        self._secret = self._random.randbytes(16)
        self._per_group = buckets_per_group
        self._buckets: list[list[str]] = [[] for _ in range(buckets)]
        self._size = bucket_size

    def __repr__(self) -> str:
        return f"AddressManager(buckets={len(self._buckets)}, addresses={len(self.addresses)})"

    def _hash(self, *parts: str) -> int:
        return int.from_bytes(sha256(self._secret + "\0".join(parts).encode())[:8], "big")

    def bucket_of(self, address: str, group: str) -> int:
        """The bucket an address is stored in, derived from the node's secret key."""
        if self._per_group is None:
            return self._hash(address) % len(self._buckets)
        slot = self._hash(address) % self._per_group
        return self._hash(group, str(slot)) % len(self._buckets)

    def add(self, address: str, group: str) -> None:
        """Store an address heard from the network, evicting a random entry if needed."""
        if not isinstance(address, str) or not isinstance(group, str):
            raise TypeError("address and group must be str")
        bucket = self._buckets[self.bucket_of(address, group)]
        if address in bucket:
            return
        if len(bucket) >= self._size:
            bucket.pop(self._random.randrange(len(bucket)))
        bucket.append(address)

    @property
    def addresses(self) -> tuple[str, ...]:
        """Every stored address, bucket by bucket."""
        return tuple(address for bucket in self._buckets for address in bucket)

    def select(self, count: int) -> tuple[str, ...]:
        """Choose ``count`` distinct addresses: each time a random nonempty bucket, then an entry.

        Picking a bucket first, as Bitcoin does, means an attacker confined
        to a few buckets is picked rarely even if those buckets are full.
        """
        integer(count, "count", 1)
        if count > len(self.addresses):
            raise ValueError("not enough addresses")
        chosen: list[str] = []
        while len(chosen) < count:
            bucket = self._random.choice([b for b in self._buckets if b])
            address = self._random.choice(bucket)
            if address not in chosen:
                chosen.append(address)
        return tuple(chosen)
