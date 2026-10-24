"""Traceability in Monero: how decoys fail (Möser et al.; Kumar et al., 2018).

A Monero input hides its real output among *decoys* (*mixins*) drawn from
earlier outputs. Two studies in 2017-2018 found that, in practice, most
inputs up to 2017 could be traced:

- **Zero-mixin chain reaction.** Until 2016 Monero allowed rings with no
  decoys. Such an input reveals the output it spends; that output can then
  be struck from every other ring that uses it as a decoy, which may leave
  some of those rings with one member, and so on. Möser et al. could
  deduce the real output of most inputs made before 2017 this way.
- **Guess-newest.** People tend to spend coins soon after receiving them,
  but decoys were drawn uniformly from all past outputs, so most of them
  were old. The newest member of a ring was the real one about 80% of the
  time.

Monero's fixes were a minimum ring size (2016, raised to 11 in 2018) and
drawing decoys from a distribution fitted to real spending ages. In
:func:`simulate_rings` an output's index is its age order, and real
spends and ``"recent"`` decoys share one geometric age distribution.
"""

from collections.abc import Iterable, Sequence
from random import Random

from blockchainkit._validation import integer, positive, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.privacy.core.base import RingInput, TraceReport

SAMPLINGS = ("uniform", "recent")
"""tuple of str: How :func:`simulate_rings` draws decoys."""


def _recent(rng: Random, height: int, mean_age: float) -> int:
    """An output index ``height - 1 - age``, with a geometric age of mean ``mean_age``."""
    while True:
        age = int(rng.expovariate(1 / mean_age))
        if age < height:
            return height - 1 - age


def simulate_rings(
    outputs: int,
    inputs: int,
    *,
    ring_size: int = 5,
    zero_mixin: float = 0.0,
    sampling: str = "uniform",
    mean_age: float = 20.0,
    seed: int = 0,
) -> tuple[RingInput, ...]:
    """Simulate ring inputs over a ledger of ``outputs`` outputs created one after another.

    Inputs are made at random heights after the first tenth of the outputs,
    and never so early that more than half the outputs are spent.
    Each spends a recent unspent output, chosen with a geometric age of mean
    ``mean_age``. With probability ``zero_mixin`` its ring holds only that
    output; otherwise ``ring_size - 1`` distinct decoys are added, drawn
    uniformly from all earlier outputs or with the same age distribution as
    real spends.
    """
    integer(outputs, "outputs", 10)
    integer(inputs, "inputs", 1)
    integer(ring_size, "ring_size", 1)
    probability(zero_mixin, "zero_mixin")
    positive(mean_age, "mean_age")
    check_seed(seed)
    if sampling not in SAMPLINGS:
        raise ValueError(f"sampling must be one of {SAMPLINGS}")
    if 2 * inputs + ring_size > outputs:
        raise ValueError("need at least 2 * inputs + ring_size outputs")
    rng = Random(seed)
    drawn = sorted(rng.randrange(outputs // 10 + ring_size, outputs + 1) for _ in range(inputs))
    # Never more spends than half the outputs so far, so unspent outputs remain.
    heights = [max(h, 2 * i + 2 + ring_size) for i, h in enumerate(drawn)]
    spent: set[int] = set()
    rings = []
    for height in heights:
        real = _recent(rng, height, mean_age)
        while real in spent:
            real = rng.randrange(height)
        spent.add(real)
        members = {real}
        if rng.random() >= zero_mixin:
            while len(members) < ring_size:
                if sampling == "uniform":
                    members.add(rng.randrange(height))
                else:
                    members.add(_recent(rng, height, mean_age))
        rings.append(RingInput(tuple(sorted(members)), real, height))
    return tuple(rings)


def chain_reaction(rings: Sequence[RingInput]) -> dict[int, int]:
    """Deduce real spends: ``{ring index: output}`` for every ring left with one possible member.

    Repeatedly removes, from every other ring, the outputs already known to
    be spent by a deduced ring.
    """
    known: dict[int, int] = {}
    changed = True
    while changed:
        changed = False
        taken = set(known.values())
        for i, ring in enumerate(rings):
            if i in known:
                continue
            left = [m for m in ring.members if m not in taken]
            if len(left) == 1:
                known[i] = left[0]
                taken.add(left[0])
                changed = True
    return known


def guess_newest(rings: Iterable[RingInput]) -> tuple[int, ...]:
    """Guess that each ring spends its newest member."""
    return tuple(max(ring.members) for ring in rings)


def trace_rings(rings: Sequence[RingInput]) -> TraceReport:
    """Measure how much of a ledger's ring inputs the two heuristics trace.

    >>> from blockchainkit.privacy import simulate_rings, trace_rings
    >>> report = trace_rings(simulate_rings(1_000, 100, zero_mixin=1.0))
    >>> report.deduced == report.rings == 100
    True
    """
    deduced = chain_reaction(rings)
    newest = guess_newest(rings)
    return TraceReport(
        rings=len(rings),
        zero_mixin=sum(1 for ring in rings if len(ring.members) == 1),
        deduced=sum(1 for i, out in deduced.items() if rings[i].real == out),
        newest_correct=sum(1 for ring, g in zip(rings, newest, strict=True) if ring.real == g),
    )
