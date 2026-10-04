"""Peer graphs: random (Erdős–Rényi 1959), small-world (Watts–Strogatz 1998),
and scale-free (Barabási–Albert 1999).

Who is connected to whom decides how fast news spreads, how many links an
attacker must cut, and how much a single peer can see. These generators build
the three classic families so experiments can compare them on equal terms.
"""

from collections import deque
from collections.abc import Iterable
from random import Random

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed


class Graph:
    """An immutable undirected simple graph on the nodes ``0, 1, ..., n - 1``.

    Parameters
    ----------
    n : int
        Number of nodes, at least 1.
    edges : iterable of tuple of int
        Unordered pairs of distinct nodes; duplicates are merged.

    Examples
    --------
    >>> from blockchainkit.network import Graph
    >>> path = Graph(3, [(0, 1), (1, 2)])
    >>> path.distances(0)
    (0, 1, 2)
    >>> path.is_connected()
    True
    """

    def __init__(self, n: int, edges: Iterable[tuple[int, int]]) -> None:
        integer(n, "n", 1)
        adjacency: list[set[int]] = [set() for _ in range(n)]
        for left, right in edges:
            integer(left, "edge endpoint")
            integer(right, "edge endpoint")
            if left >= n or right >= n or left == right:
                raise ValueError("edges join two distinct nodes in range(n)")
            adjacency[left].add(right)
            adjacency[right].add(left)
        self._neighbors = tuple(tuple(sorted(nodes)) for nodes in adjacency)
        self._adjacent = tuple(frozenset(nodes) for nodes in adjacency)

    def __repr__(self) -> str:
        return f"Graph(n={self.n}, edges={len(self.edges)})"

    @property
    def n(self) -> int:
        """Number of nodes."""
        return len(self._neighbors)

    @property
    def edges(self) -> tuple[tuple[int, int], ...]:
        """Every edge once, as ``(smaller, larger)``, in sorted order."""
        return tuple((u, v) for u in range(self.n) for v in self._neighbors[u] if u < v)

    def neighbors(self, node: int) -> tuple[int, ...]:
        """Sorted neighbors of ``node``."""
        return self._neighbors[node]

    def degrees(self) -> tuple[int, ...]:
        """Number of neighbors of every node, indexed by node."""
        return tuple(len(nodes) for nodes in self._neighbors)

    def distances(self, source: int) -> tuple[int | None, ...]:
        """Hop counts from ``source`` by breadth-first search; None if unreachable."""
        result: list[int | None] = [None] * self.n
        result[source] = 0
        queue = deque([source])
        while queue:
            node = queue.popleft()
            hops = result[node]
            assert hops is not None  # Only reached nodes are queued.
            for neighbor in self._neighbors[node]:
                if result[neighbor] is None:
                    result[neighbor] = hops + 1
                    queue.append(neighbor)
        return tuple(result)

    def components(self) -> tuple[frozenset[int], ...]:
        """Connected components, largest first (ties by smallest node)."""
        unseen, found = set(range(self.n)), []
        while unseen:
            start = min(unseen)
            reached = frozenset(i for i, d in enumerate(self.distances(start)) if d is not None)
            found.append(reached)
            unseen -= reached
        return tuple(sorted(found, key=lambda c: (-len(c), min(c))))

    def is_connected(self) -> bool:
        """True if every node can reach every other node."""
        return len(self.components()) == 1

    def average_path_length(self) -> float:
        """Mean hop count over all ordered pairs of distinct, mutually reachable nodes.

        This is the *L* of Watts and Strogatz. A graph with no such pair
        (a single node, or no edges) has length 0.
        """
        total = pairs = 0
        for source in range(self.n):
            for d in self.distances(source):
                if d:
                    total += d
                    pairs += 1
        return total / pairs if pairs else 0.0

    def clustering(self) -> float:
        """Average local clustering coefficient: the *C* of Watts and Strogatz.

        A node's coefficient is the fraction of pairs of its neighbors that
        are themselves linked ("my friends know each other"). Nodes with fewer
        than two neighbors contribute 0.
        """
        total = 0.0
        for nodes in self._neighbors:
            k = len(nodes)
            if k >= 2:
                linked = sum(
                    1 for i, u in enumerate(nodes) for v in nodes[i + 1 :] if v in self._adjacent[u]
                )
                total += linked / (k * (k - 1) / 2)
        return total / self.n


def complete_graph(n: int) -> Graph:
    """Every pair of the ``n`` nodes linked: the setting of classic rumor-spreading results.

    >>> from blockchainkit.network import complete_graph
    >>> len(complete_graph(5).edges)
    10
    """
    integer(n, "n", 1)
    return Graph(n, ((u, v) for u in range(n) for v in range(u + 1, n)))


def erdos_renyi(n: int, p: float, *, seed: int = 0) -> Graph:
    """Random graph G(n, p): each of the n(n-1)/2 possible links exists with probability p.

    Erdős and Rényi showed that connectivity appears abruptly: for large n,
    G(n, p) is almost surely disconnected when ``p < (1 - e) ln n / n`` and
    almost surely connected when ``p > (1 + e) ln n / n``.

    >>> from blockchainkit.network import erdos_renyi
    >>> erdos_renyi(30, 1.0).is_connected()
    True
    """
    integer(n, "n", 1)
    probability(p, "p")
    check_seed(seed)
    random = Random(seed)
    return Graph(n, ((u, v) for u in range(n) for v in range(u + 1, n) if random.random() < p))


def ring_lattice(n: int, k: int) -> Graph:
    """Ring where each node links to its ``k`` nearest nodes, ``k / 2`` on each side.

    >>> from blockchainkit.network import ring_lattice
    >>> ring_lattice(6, 2).neighbors(0)
    (1, 5)
    """
    integer(n, "n", 3)
    integer(k, "k", 2)
    if k % 2 or k >= n:
        raise ValueError("k must be even and smaller than n")
    return Graph(n, ((u, (u + j) % n) for u in range(n) for j in range(1, k // 2 + 1)))


def watts_strogatz(n: int, k: int, beta: float, *, seed: int = 0) -> Graph:
    """Small-world graph: rewire each ring-lattice edge with probability ``beta``.

    Following Watts and Strogatz, each edge ``(u, u + j)`` of
    :func:`ring_lattice` keeps its endpoint ``u`` and, with probability
    ``beta``, moves its other end to a uniformly random node, avoiding
    self-loops and duplicate links. A few shortcuts (small ``beta``) shrink
    the average path length almost to that of a random graph while the
    clustering stays close to the lattice's.

    >>> from blockchainkit.network import watts_strogatz
    >>> len(watts_strogatz(20, 4, 0.3, seed=1).edges)
    40
    """
    lattice = ring_lattice(n, k)
    probability(beta, "beta")
    check_seed(seed)
    random = Random(seed)
    adjacency = [set(lattice.neighbors(u)) for u in range(n)]
    for j in range(1, k // 2 + 1):  # Rewire lap by lap, as in the 1998 paper.
        for u in range(n):
            v = (u + j) % n
            if random.random() >= beta:
                continue
            choices = [w for w in range(n) if w != u and w not in adjacency[u]]
            if not choices:
                continue  # u already links to everyone; nothing to rewire to.
            w = random.choice(choices)
            adjacency[u].discard(v)
            adjacency[v].discard(u)
            adjacency[u].add(w)
            adjacency[w].add(u)
    return Graph(n, ((u, v) for u in range(n) for v in adjacency[u] if u < v))


def barabasi_albert(n: int, m: int, *, seed: int = 0) -> Graph:
    """Scale-free graph by preferential attachment.

    Start from ``m + 1`` fully linked nodes. Each new node links to ``m``
    distinct existing nodes, chosen with probability proportional to their
    current degree ("the rich get richer"). The degree distribution
    approaches the power law ``P(k) ~ k^-3``: a few hubs, many small nodes.

    >>> from blockchainkit.network import barabasi_albert
    >>> g = barabasi_albert(50, 2, seed=3)
    >>> len(g.edges) == 3 + 2 * (50 - 3)
    True
    """
    integer(m, "m", 1)
    integer(n, "n", m + 1)
    check_seed(seed)
    random = Random(seed)
    edges = [(u, v) for u in range(m + 1) for v in range(u + 1, m + 1)]
    # Each node appears in ``ends`` once per incident edge, so a uniform pick
    # from ``ends`` is a pick proportional to degree.
    ends = [node for edge in edges for node in edge]
    for new in range(m + 1, n):
        targets: set[int] = set()
        while len(targets) < m:
            targets.add(random.choice(ends))
        for target in sorted(targets):
            edges.append((target, new))
            ends.extend((target, new))
    return Graph(n, edges)
