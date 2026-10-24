"""Onion routing in Tor: low-latency anonymity and its end-to-end weakness (2004).

Tor wraps traffic in layers as a mix-net does, through a *circuit* of three
relays: an entry guard, a middle relay and an exit. Each relay learns only
its neighbours on the circuit. Unlike a mix, a relay forwards each packet
at once, without batching or reordering, so web browsing stays fast. The
price, which Dingledine, Mathewson and Syverson state in the design, is
that an adversary watching both the entry and the exit of a circuit can
match the timing of what goes in to what comes out. If it runs a fraction
``f`` of the relays, about ``f**2`` of circuits are exposed.

The circuit itself reuses :func:`~blockchainkit.privacy.systems.mixnets.wrap`;
real Tor builds circuits by telescoping Diffie-Hellman handshakes and then
sends fixed 512-byte cells under symmetric keys.
"""

from collections.abc import Collection, Sequence
from random import Random

from blockchainkit._validation import integer, positive
from blockchainkit._validation import seed as check_seed
from blockchainkit.privacy.core.base import FlowObservation


def circuit_compromise_rate(
    relays: int, malicious: Collection[int], circuits: int, *, seed: int = 0
) -> float:
    """Fraction of random three-relay circuits whose entry and exit are both malicious.

    Each circuit picks three distinct relays uniformly; real Tor weights the
    choice by bandwidth and keeps the same entry guard for months.

    >>> from blockchainkit.privacy import circuit_compromise_rate
    >>> circuit_compromise_rate(10, set(), 100)
    0.0
    """
    integer(relays, "relays", 3)
    integer(circuits, "circuits", 1)
    check_seed(seed)
    if any(type(r) is not int or not 0 <= r < relays for r in malicious):
        raise ValueError("malicious must hold relay indices")
    rng = Random(seed)
    bad = frozenset(malicious)
    exposed = 0
    for _ in range(circuits):
        entry, _middle, exit_ = rng.sample(range(relays), 3)
        exposed += entry in bad and exit_ in bad
    return exposed / circuits


def simulate_flows(
    flows: int,
    packets: int,
    *,
    latency: float = 0.2,
    jitter: float = 0.01,
    seed: int = 0,
) -> FlowObservation:
    """Packet times of concurrent flows at their entry and at their exit.

    Each flow sends ``packets`` packets with exponential gaps of mean 1. The
    network delays every packet by ``latency`` plus Gaussian ``jitter``,
    and the exit side sees the flows in a shuffled order.
    """
    integer(flows, "flows", 1)
    integer(packets, "packets", 2)
    positive(latency, "latency")
    positive(jitter, "jitter")
    check_seed(seed)
    rng = Random(seed)
    entering = []
    for _ in range(flows):
        times, now = [], rng.uniform(0, 1)
        for _ in range(packets):
            now += rng.expovariate(1.0)
            times.append(now)
        entering.append(tuple(times))
    leaving = [tuple(t + latency + rng.gauss(0, jitter) for t in flow) for flow in entering]
    order = list(range(flows))
    rng.shuffle(order)
    truth = [0] * flows
    for position, flow in enumerate(order):
        truth[flow] = position
    return FlowObservation(tuple(entering), tuple(leaving[flow] for flow in order), tuple(truth))


def _gaps(times: Sequence[float]) -> list[float]:
    return [b - a for a, b in zip(times, times[1:], strict=False)]


def match_flows(
    entering: Sequence[Sequence[float]], leaving: Sequence[Sequence[float]]
) -> tuple[int, ...]:
    """Match each entering flow to the leaving flow with the most similar packet gaps.

    The end-to-end timing attack: delay shifts every packet alike, so the
    gaps between packets survive the trip. Distance is the sum of absolute
    differences of the gaps.
    """
    if not leaving:
        raise ValueError("no leaving flows to match")
    matches = []
    for flow in entering:
        gaps = _gaps(flow)
        distances = [
            sum(abs(a - b) for a, b in zip(gaps, _gaps(other), strict=False))
            + abs(len(other) - len(flow))
            for other in leaving
        ]
        matches.append(distances.index(min(distances)))
    return tuple(matches)
