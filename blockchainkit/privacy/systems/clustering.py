"""Address clustering: grouping a ledger's addresses by owner (Meiklejohn et al., 2013).

Bitcoin users hide behind fresh addresses, but how they spend gives them
away. *A Fistful of Bitcoins* clustered addresses with two heuristics:

- **Common input ownership.** A transaction's inputs are signed by their
  owners together, so every input address of one transaction belongs to
  one user (Nakamoto noted it in the white paper).
- **One-time change.** A wallet sends the change back to a fresh address.
  If exactly one output address of a transaction has never appeared
  before, and no input address reappears among the outputs, that output is
  the change and belongs to the sender too.

Labelling a few clusters, by buying from a service or depositing at an
exchange, then names every address in them.

:func:`simulate_payments` makes a toy economy with known owners; real
wallets select coins and create change in many more ways, which is where
the change heuristic makes its mistakes.
"""

from collections.abc import Iterable
from random import Random

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.privacy.core.base import ClusterScore, PaymentHistory, TransactionRecord


def fresh_address(label: str) -> str:
    """A 16-hex-digit address derived from ``label``, which an observer cannot read back."""
    return sha256(label.encode()).hex()[:16]


def simulate_payments(
    users: int,
    payments: int,
    *,
    coins: int = 2,
    reuse: float = 0.5,
    seed: int = 0,
) -> PaymentHistory:
    """Simulate users paying each other, with the owner of every address recorded.

    Every user starts with ``coins`` coins at fresh addresses. In each
    payment a random user pays a random share of its money to another,
    spending its largest coins first and sending the change to a fresh
    address. With probability ``reuse`` the payee is paid at an address it
    used before, as a shop or an exchange deposit address is.
    """
    integer(users, "users", 2)
    integer(payments, "payments")
    integer(coins, "coins", 1)
    probability(reuse, "reuse")
    check_seed(seed)
    rng = Random(seed)
    owners: dict[str, str] = {}
    wallets: dict[str, list[tuple[str, int]]] = {f"user{u}": [] for u in range(users)}
    used: dict[str, list[str]] = {name: [] for name in wallets}
    counter = 0

    def new_address(user: str) -> str:
        nonlocal counter
        counter += 1
        address = fresh_address(f"{seed}:{counter}")
        owners[address] = user
        used[user].append(address)
        return address

    transactions = []
    for name, wallet in wallets.items():
        minted = tuple((new_address(name), rng.randrange(10, 100)) for _ in range(coins))
        wallet.extend(minted)
        transactions.append(TransactionRecord((), minted))
    names = list(wallets)
    for _ in range(payments):
        payer, payee = rng.sample(names, 2)
        wallet = wallets[payer]
        if not wallet:
            continue
        wallet.sort(key=lambda coin: coin[1], reverse=True)
        total = sum(amount for _, amount in wallet)
        amount = rng.randint(1, max(1, total * 2 // 3))
        spent, covered = [], 0
        while covered < amount:
            coin = wallet.pop(0)
            spent.append(coin)
            covered += coin[1]
        if used[payee] and rng.random() < reuse:
            to = rng.choice(used[payee])
        else:
            to = new_address(payee)
        outputs = [(to, amount)]
        if covered > amount:
            outputs.append((new_address(payer), covered - amount))
            wallet.append(outputs[-1])
        rng.shuffle(outputs)
        wallets[payee].append((to, amount))
        transactions.append(TransactionRecord(tuple(spent), tuple(outputs)))
    return PaymentHistory(tuple(transactions), owners)


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        self.parent[self.find(left)] = self.find(right)


def cluster_addresses(
    transactions: Iterable[TransactionRecord], *, change: bool = False
) -> tuple[frozenset[str], ...]:
    """Group addresses by common input ownership, and optionally by one-time change.

    Returns the clusters, largest first.

    >>> from blockchainkit.privacy import TransactionRecord, cluster_addresses
    >>> tx = TransactionRecord((("a", 5), ("b", 5)), (("c", 10),))
    >>> sorted(map(sorted, cluster_addresses([tx])))
    [['a', 'b'], ['c']]
    """
    groups = _UnionFind()
    seen: set[str] = set()
    for tx in transactions:
        inputs = [address for address, _ in tx.inputs]
        outputs = [address for address, _ in tx.outputs]
        for address in inputs + outputs:
            groups.find(address)
        for address in inputs[1:]:
            groups.union(inputs[0], address)
        if change and inputs and len(outputs) > 1 and not set(inputs) & set(outputs):
            new = [address for address in outputs if address not in seen]
            if len(new) == 1:
                groups.union(inputs[0], new[0])
        seen.update(inputs)
        seen.update(outputs)
    clusters: dict[str, set[str]] = {}
    for address in groups.parent:
        clusters.setdefault(groups.find(address), set()).add(address)
    return tuple(sorted((frozenset(c) for c in clusters.values()), key=len, reverse=True))


def score_clusters(clusters: Iterable[frozenset[str]], owners: dict[str, str]) -> ClusterScore:
    """Compare clusters with the true owners of their addresses.

    Raises
    ------
    KeyError
        A clustered address has no known owner.
    """
    clusters = tuple(clusters)
    addresses = sum(len(c) for c in clusters)
    owner_sets = [{owners[a] for a in cluster} for cluster in clusters]
    users = set().union(*owner_sets) if owner_sets else set()
    clusters_of: dict[str, int] = {}
    for cluster_owners in owner_sets:
        for user in cluster_owners:
            clusters_of[user] = clusters_of.get(user, 0) + 1
    identified = sum(1 for o in owner_sets if len(o) == 1 and clusters_of[next(iter(o))] == 1)
    return ClusterScore(
        addresses=addresses,
        users=len(users),
        clusters=len(clusters),
        false_merges=sum(1 for o in owner_sets if len(o) > 1),
        identified=identified,
        largest=max((len(c) for c in clusters), default=0),
    )
