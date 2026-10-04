"""Epidemic dissemination: push, pull and push-pull rumor spreading.

Each round, every peer calls one neighbor chosen uniformly at random. In
*push*, informed callers tell the callee; in *pull*, uninformed callers ask
the callee and learn the rumor if it knows it; *push-pull* does both. Demers
et al. (1987) compared these for replicated databases. On the complete graph,
push alone informs everyone in about ``log2 n + ln n`` rounds (Frieze and
Grimmett 1985, Pittel 1987).
"""

from math import log, log2
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.network.core.base import RumorRun
from blockchainkit.network.systems.topology import Graph

MODES = ("push", "pull", "push-pull")
"""tuple of str: The supported exchange modes."""


def pittel_rounds(n: int) -> float:
    """Rounds push gossip needs on the complete graph: ``log2 n + ln n``, up to O(1).

    The ``log2 n`` term is the doubling phase, while few peers know the
    rumor; the ``ln n`` term is the coupon-collector tail, while the last
    uninformed peers wait to be called.

    >>> from blockchainkit.network import pittel_rounds
    >>> round(pittel_rounds(1024), 2)
    16.93
    """
    integer(n, "n", 1)
    return log2(n) + log(n)


def spread_rumor(
    network: Graph | int,
    *,
    mode: str = "push",
    source: int = 0,
    seed: int = 0,
    max_rounds: int = 10_000,
) -> RumorRun:
    """Simulate synchronous random-call rumor spreading.

    Parameters
    ----------
    network : Graph or int
        The peer graph, or an integer ``n`` for the complete graph on ``n``
        peers (simulated without building its n(n-1)/2 edges).
    mode : {"push", "pull", "push-pull"}
        Who learns from each call; see the module docstring.
    source : int
        The peer that knows the rumor at round 0.
    seed : int
        Seed for the random calls.
    max_rounds : int
        Stop after this many rounds even if peers remain uninformed.

    Returns
    -------
    RumorRun
        Informed counts per round. The run also stops once every peer that
        the source can reach is informed.

    Examples
    --------
    >>> from blockchainkit.network import spread_rumor
    >>> run = spread_rumor(1000, seed=1)
    >>> run.complete, run.informed[:4]
    (True, (1, 2, 4, 8))
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    check_seed(seed)
    integer(max_rounds, "max_rounds", 1)
    if isinstance(network, Graph):
        n = network.n
        reachable = sum(1 for d in network.distances(source) if d is not None)
    else:
        integer(network, "n", 1)
        n = reachable = network
    integer(source, "source")
    if source >= n:
        raise ValueError("source must be a peer in range(n)")
    random = Random(seed)

    def call(peer: int) -> int | None:
        if isinstance(network, Graph):
            neighbors = network.neighbors(peer)
            return random.choice(neighbors) if neighbors else None
        partner = random.randrange(n - 1)  # Any peer but the caller.
        return partner + 1 if partner >= peer else partner

    informed = [False] * n
    informed[source] = True
    counts = [1]
    while counts[-1] < reachable and len(counts) <= max_rounds:
        before = informed[:]  # Calls in a round see the state at its start.
        for caller in range(n):
            callee = call(caller)
            if callee is None:
                continue
            if mode != "pull" and before[caller]:
                informed[callee] = True
            if mode != "push" and before[callee]:
                informed[caller] = True
        counts.append(sum(informed))
    return RumorRun(tuple(counts), n)
