"""Transaction-origin privacy: diffusion versus Dandelion (Bojja Venkatakrishnan,
Fanti and Viswanath 2017).

When a peer broadcasts its transaction, it is usually the first to send it.
*Spy* peers that connect widely record who first sent them each
transaction and guess that peer is the origin: the *first-spy estimator*.
Dandelion first passes the transaction along a random path (the *stem*),
each hop continuing with probability ``q``, and only then diffuses it. The
spies then see the end of the stem, far from the origin.
"""

import heapq
from collections.abc import Iterable
from random import Random

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.network.systems.topology import Graph

MODES = ("diffusion", "dandelion")
"""tuple of str: The broadcast strategies compared by :func:`first_spy_precision`."""


def _first_spy_guess(
    graph: Graph, spies: frozenset[int], start: int, previous: int, random: Random
) -> int | None:
    """Diffuse from ``start`` with exponential link delays; return the first spy's sender.

    ``previous`` is the peer that handed the transaction to ``start``
    (``start`` itself at the origin). Returns None if no spy is reachable.
    """
    if start in spies:
        return previous
    heard = {start}
    queue = [(random.expovariate(1.0), start, neighbor) for neighbor in graph.neighbors(start)]
    heapq.heapify(queue)
    while queue:
        time, sender, peer = heapq.heappop(queue)
        if peer in heard:
            continue
        heard.add(peer)
        if peer in spies:
            return sender
        for neighbor in graph.neighbors(peer):
            if neighbor not in heard:
                heapq.heappush(queue, (time + random.expovariate(1.0), peer, neighbor))
    return None


def first_spy_precision(
    graph: Graph,
    spies: Iterable[int],
    *,
    mode: str = "diffusion",
    trials: int = 200,
    stem_probability: float = 0.9,
    seed: int = 0,
) -> float:
    """Fraction of broadcasts whose origin the first-spy estimator identifies.

    Each trial picks an honest origin uniformly at random.

    * ``"diffusion"``: the origin sends to all neighbors, and each peer
      forwards on first receipt, with independent Exp(1) delay per message.
    * ``"dandelion"``: the transaction first walks to a random neighbor;
      after each hop it continues the stem with probability
      ``stem_probability`` and otherwise diffuses from where it is. A spy on
      the stem guesses the peer that handed it the transaction.

    The original Dandelion routes stems over a dedicated line-shaped
    anonymity graph; here the stem is a random walk on ``graph`` itself.

    Examples
    --------
    >>> from blockchainkit.network import complete_graph, first_spy_precision
    >>> first_spy_precision(complete_graph(2), {1}, trials=10)
    1.0
    """
    spy_set = frozenset(spies)
    honest = [node for node in range(graph.n) if node not in spy_set]
    if not spy_set or not honest or not spy_set <= set(range(graph.n)):
        raise ValueError("spies must be a nonempty proper subset of the peers")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    integer(trials, "trials", 1)
    probability(stem_probability, "stem_probability")
    check_seed(seed)
    random = Random(seed)
    hits = 0
    for _ in range(trials):
        origin = previous = current = random.choice(honest)
        if mode == "dandelion":
            while graph.neighbors(current) and current not in spy_set:
                previous, current = current, random.choice(graph.neighbors(current))
                if random.random() >= stem_probability:
                    break
        hits += _first_spy_guess(graph, spy_set, current, previous, random) == origin
    return hits / trials
