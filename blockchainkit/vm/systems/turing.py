"""Turing machines (1936), the halting problem, and Radó's busy beaver (1962).

A Turing machine reads one cell of an unbounded tape, and according to its
state and the symbol there, writes a symbol, moves left or right, and
changes state. Turing proved that no program can decide, for every machine,
whether it halts. Radó turned that into numbers: the *busy beaver* ``S(n)``
is the most steps any halting ``n``-state, 2-symbol machine takes from a
blank tape. ``S`` grows faster than any computable function, so no
fixed budget can separate "still running" from "never halts". Blockchains
respond the way Radó's search must: they cap the work (gas) and stop there.
"""

import itertools
from collections.abc import Iterator, Mapping

from blockchainkit._validation import integer
from blockchainkit.vm.core.base import BusyBeaverResult, TuringRun

Rule = tuple[int, int, str]
"""``(write, move, next_state)``: move is -1 (left) or +1 (right); state ``"H"`` halts."""

HALT = "H"
"""str: The halting state."""

STATE_NAMES = "ABCDEFG"


def run_turing_machine(
    rules: Mapping[tuple[str, int], Rule], *, max_steps: int = 1000, start: str = "A"
) -> TuringRun:
    """Run a 2-symbol machine from a blank tape for at most ``max_steps`` steps.

    The transition into the halting state counts as a step, as in Radó's
    definition. If the machine returns to an earlier configuration (same
    state, head position and tape), it provably runs forever. Otherwise,
    when the budget runs out, the outcome is unknown.

    Examples
    --------
    >>> from blockchainkit.vm import run_turing_machine
    >>> champion = {("A", 0): (1, 1, "B"), ("A", 1): (1, -1, "B"),
    ...             ("B", 0): (1, -1, "A"), ("B", 1): (1, 1, "H")}
    >>> run = run_turing_machine(champion)
    >>> run.outcome, run.steps, run.ones
    ('halted', 6, 4)
    """
    integer(max_steps, "max_steps", 1)
    tape: dict[int, int] = {}
    state, head = start, 0
    seen: set[tuple[str, int, frozenset[int]]] = set()
    for step in range(1, max_steps + 1):
        config = (state, head, frozenset(cell for cell, symbol in tape.items() if symbol))
        if config in seen:
            return TuringRun("looping", step - 1, sum(tape.values()))
        seen.add(config)
        try:
            write, move, state = rules[(state, tape.get(head, 0))]
        except KeyError:
            raise ValueError(f"no rule for state {state!r} reading {tape.get(head, 0)}") from None
        if write not in (0, 1) or move not in (-1, 1):
            raise ValueError("rules write 0 or 1 and move -1 or +1")
        tape[head] = write
        head += move
        if state == HALT:
            return TuringRun("halted", step, sum(tape.values()))
    return TuringRun("unknown", max_steps, sum(tape.values()))


def enumerate_machines(states: int) -> Iterator[dict[tuple[str, int], Rule]]:
    """Yield every ``states``-state, 2-symbol machine: ``(4 (states + 1)) ** (2 states)`` of them.

    >>> from blockchainkit.vm import enumerate_machines
    >>> sum(1 for _ in enumerate_machines(1))
    64
    """
    integer(states, "states", 1)
    if states > len(STATE_NAMES):
        raise ValueError(f"at most {len(STATE_NAMES)} states")
    names = STATE_NAMES[:states]
    keys = [(name, symbol) for name in names for symbol in (0, 1)]
    choices = list(itertools.product((0, 1), (-1, 1), (*names, HALT)))
    for combination in itertools.product(choices, repeat=len(keys)):
        yield dict(zip(keys, combination, strict=True))


def busy_beaver(states: int, *, max_steps: int = 100) -> BusyBeaverResult:
    """Search every machine with ``states`` states for the longest halting run.

    Each machine runs for at most ``max_steps`` steps. The answer equals
    ``S(states)`` only if every machine classified as unknown really runs
    forever, which this search cannot prove; that gap is the halting problem.
    Feasible here for 1 or 2 states (20,736 machines for 2).

    Examples
    --------
    >>> from blockchainkit.vm import busy_beaver
    >>> busy_beaver(1).steps
    1
    """
    best: TuringRun | None = None
    champion: dict[tuple[str, int], Rule] = {}
    counts = {"halted": 0, "looping": 0, "unknown": 0}
    for rules in enumerate_machines(states):
        run = run_turing_machine(rules, max_steps=max_steps)
        counts[run.outcome] += 1
        if run.outcome == "halted" and (
            best is None or (run.steps, run.ones) > (best.steps, best.ones)
        ):
            best, champion = run, rules
    assert best is not None  # A machine whose first rule halts always exists.
    return BusyBeaverResult(best.steps, best.ones, champion, counts)
