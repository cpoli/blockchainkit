"""Ben-Or's randomized consensus (1983), and the FLP impossibility (1985) it sidesteps.

Fischer, Lynch and Paterson proved that no *deterministic* protocol can
guarantee agreement in an asynchronous network if even one process may
crash: an adversary scheduling message delivery can keep it undecided
forever. Ben-Or's protocol escapes by tossing coins. In each round processes
exchange values, propose a strong majority if they see one, and adopt a
proposal or flip a coin. Whatever the schedule, the coins eventually line up.
"""

from collections.abc import Callable, Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.consensus.core.base import ConsensusRun

_UNDECIDED = -1


def _adversarial_pick(values: dict[int, int], quota: int, favor_mixed: bool) -> list[int]:
    """Choose ``quota`` senders that keep the receiver as undecided as possible."""
    ones = [p for p, v in values.items() if v == 1]
    zeros = [p for p, v in values.items() if v == 0]
    others = [p for p, v in values.items() if v not in (0, 1)]
    if favor_mixed:  # Phase 1: alternate values so no strong majority appears.
        order: list[int] = []
        while zeros or ones:
            for group in (zeros, ones):
                if group:
                    order.append(group.pop())
        return order[:quota]
    return (others + zeros + ones)[:quota]  # Phase 2: as few concrete proposals as possible.


def ben_or(
    initial: Sequence[int],
    faults: int,
    *,
    coin: Callable[[int, int], int] | None = None,
    adversarial: bool = True,
    seed: int = 0,
    max_rounds: int = 1000,
) -> ConsensusRun:
    """Run Ben-Or's binary consensus for crash faults (n > 2f).

    Each process waits for ``n - f`` messages per phase, the most it can
    wait for when f processes may have crashed; the scheduler chooses which.

    Parameters
    ----------
    initial : sequence of int
        Each process's input bit.
    faults : int
        The number of crashes f the protocol is sized for.
    coin : callable, optional
        ``coin(process, round) -> 0 or 1``. Defaults to a seeded fair coin.
        Pass a deterministic function to see the FLP adversary win.
    adversarial : bool
        If True, the scheduler delivers the messages most likely to delay a
        decision; otherwise a random ``n - f`` subset.
    seed : int
        Seed for the coin and the random scheduler.
    max_rounds : int
        Give up after this many rounds.

    Returns
    -------
    ConsensusRun
        Decisions so far, rounds run, and whether every process decided.

    Examples
    --------
    >>> from blockchainkit.consensus import ben_or
    >>> ben_or([1, 1, 1], faults=1).decisions
    {0: 1, 1: 1, 2: 1}
    """
    n = len(initial)
    integer(faults, "faults")
    integer(max_rounds, "max_rounds", 1)
    check_seed(seed)
    if n <= 2 * faults:
        raise ValueError("Ben-Or needs n > 2f processes")
    if any(v not in (0, 1) for v in initial):
        raise ValueError("inputs must be bits")
    rng = Random(seed)
    flip = coin or (lambda process, round_: rng.getrandbits(1))
    quota = n - faults
    values = dict(enumerate(initial))
    decisions: dict[int, int] = {}
    for round_ in range(1, max_rounds + 1):
        proposals = {}
        for p in range(n):
            heard = (
                _adversarial_pick(dict(values), quota, True)
                if adversarial
                else rng.sample(range(n), quota)
            )
            counts = [sum(values[q] == bit for q in heard) for bit in (0, 1)]
            strong = [bit for bit in (0, 1) if counts[bit] > n / 2]
            proposals[p] = strong[0] if strong else _UNDECIDED
        for p in range(n):
            heard = (
                _adversarial_pick(dict(proposals), quota, False)
                if adversarial
                else rng.sample(range(n), quota)
            )
            seen = [proposals[q] for q in heard if proposals[q] != _UNDECIDED]
            if seen and len(seen) >= faults + 1:
                decisions.setdefault(p, seen[0])
            values[p] = seen[0] if seen else flip(p, round_)
        if len(decisions) == n:
            return ConsensusRun(decisions, round_, True)
    return ConsensusRun(decisions, max_rounds, False)
