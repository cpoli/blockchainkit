"""Byzantine reliable broadcast (Bracha 1987).

A sender wants every correct process to deliver the same value, even if the
sender lies by telling different processes different things. Bracha's
protocol adds two all-to-all phases on top of the sender's message:

1. **Echo.** On the sender's value, a process tells everyone "I got v".
2. **Ready.** On ``ceil((n + t + 1) / 2)`` echoes of v, or ``t + 1`` readies
   of v (amplification), a process tells everyone "ready for v", once.
3. **Deliver.** On ``2t + 1`` readies of v, a process delivers v.

Any two echo quorums overlap in a correct process, which echoes only once,
so correct processes never become ready for different values. Amplification
makes delivery all-or-nothing. Both arguments need ``n > 3t``.
"""

from collections.abc import Iterable, Sequence

from blockchainkit._validation import integer
from blockchainkit.network.core.base import BroadcastResult

SENDER = 0
"""int: The broadcasting process."""


def reliable_broadcast(
    n: int,
    faulty: Iterable[int],
    proposals: Sequence[str],
    *,
    tolerance: int | None = None,
) -> BroadcastResult:
    """Run Bracha's broadcast in synchronous rounds from process 0.

    Parameters
    ----------
    n : int
        Number of processes, at least 2.
    faulty : iterable of int
        Byzantine processes. A faulty sender sends ``proposals[r]`` to each
        process ``r``. Faulty processes collude with that split: to each
        correct process ``r`` they echo and ready ``proposals[r]``, the
        strongest support they can give to a disagreement.
    proposals : sequence of str
        One value per process; entries at faulty processes are ignored. If
        the sender is correct, all correct entries must equal ``proposals[0]``.
    tolerance : int, optional
        The ``t`` used in the thresholds; defaults to ``(n - 1) // 3``, the
        most the protocol can tolerate. Running with more faulty processes
        than ``tolerance`` shows the bound is needed.

    Returns
    -------
    BroadcastResult

    Examples
    --------
    >>> from blockchainkit.network import reliable_broadcast
    >>> result = reliable_broadcast(4, {0}, ["a", "a", "b", "b"])
    >>> result.agreement, result.totality, sorted(set(result.delivered.values()))
    (True, True, ['b'])
    """
    integer(n, "n", 2)
    bad = set(faulty)
    for process in bad:
        integer(process, "faulty process")
        if process >= n:
            raise ValueError("faulty processes must be in range(n)")
    t = (n - 1) // 3 if tolerance is None else tolerance
    integer(t, "tolerance")
    if len(proposals) != n or not all(isinstance(v, str) for v in proposals):
        raise ValueError("give one str proposal per process")
    correct = [p for p in range(n) if p not in bad]
    if SENDER not in bad and any(proposals[p] != proposals[SENDER] for p in correct):
        raise ValueError("a correct sender sends the same value to everyone")
    echo_quorum, amplify, deliver_quorum = -(-(n + t + 1) // 2), t + 1, 2 * t + 1

    echoes: dict[int, dict[str, set[int]]] = {p: {} for p in correct}
    readies: dict[int, dict[str, set[int]]] = {p: {} for p in correct}
    for r in correct:  # Faulty processes back the value the sender gave r.
        for f in bad:
            echoes[r].setdefault(proposals[r], set()).add(f)
            readies[r].setdefault(proposals[r], set()).add(f)
    echoed: set[int] = set()
    ready: dict[int, str] = {}
    delivered: dict[int, str | None] = dict.fromkeys(correct)
    messages = len(correct) if SENDER in correct else 0  # The SEND messages.

    def broadcast(table: dict[int, dict[str, set[int]]], source: int, value: str) -> int:
        for r in correct:
            table[r].setdefault(value, set()).add(source)
        return n

    changed = True
    while changed:
        changed = False
        sends: list[tuple[str, int, str]] = []
        for p in correct:
            if p not in echoed:
                sends.append(("echo", p, proposals[p]))
                echoed.add(p)
            if p not in ready:
                candidates = sorted(
                    v
                    for v in set(echoes[p]) | set(readies[p])
                    if len(echoes[p].get(v, ())) >= echo_quorum
                    or len(readies[p].get(v, ())) >= amplify
                )
                if candidates:
                    ready[p] = candidates[0]
                    sends.append(("ready", p, candidates[0]))
            if delivered[p] is None:
                for v in sorted(readies[p]):
                    if len(readies[p][v]) >= deliver_quorum:
                        delivered[p] = v
                        changed = True
                        break
        for kind, p, value in sends:  # Messages of a round arrive together.
            messages += broadcast(echoes if kind == "echo" else readies, p, value)
            changed = True
    values = {v for v in delivered.values() if v is not None}
    some = any(v is not None for v in delivered.values())
    every = all(v is not None for v in delivered.values())
    return BroadcastResult(delivered, len(values) <= 1, every or not some, messages)
