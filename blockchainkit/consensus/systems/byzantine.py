"""The Byzantine generals problem and the oral-messages algorithm (1982).

Lamport, Shostak and Pease asked how loyal generals can agree on a plan when
some generals, possibly including the commander, are traitors who send
different messages to different recipients. Their algorithm OM(m) has every
lieutenant relay what it heard, recursively, and take a majority. It
succeeds whenever there are more than three times as many generals as
traitors: n > 3m. With three generals and one traitor no algorithm can.
"""

from collections import Counter
from collections.abc import Callable, Set

from blockchainkit._validation import integer
from blockchainkit.consensus.core.base import GeneralsResult

ATTACK, RETREAT = "attack", "retreat"


def _default_lie(sender: int, receiver: int, value: str) -> str:
    """A traitor's strategy: tell even-numbered receivers to attack, odd ones to retreat."""
    return ATTACK if receiver % 2 == 0 else RETREAT


def _majority(values: list[str]) -> str:
    counts = Counter(values)
    return ATTACK if counts[ATTACK] > counts[RETREAT] else RETREAT  # Ties retreat.


def oral_messages(
    generals: int,
    traitors: Set[int],
    order: str,
    *,
    rounds: int,
    lie: Callable[[int, int, str], str] = _default_lie,
) -> GeneralsResult:
    """Run OM(rounds) with general 0 as commander.

    Parameters
    ----------
    generals : int
        Total number of generals n, at least 3; general 0 commands.
    traitors : set of int
        Traitorous generals; they send ``lie(sender, receiver, value)``
        instead of the true value.
    order : str
        The commander's order, ``"attack"`` or ``"retreat"``.
    rounds : int
        The recursion depth m: OM(m) tolerates m traitors when n > 3m.
    lie : callable
        The traitors' strategy.

    Returns
    -------
    GeneralsResult
        Loyal lieutenants' decisions and whether IC1 and IC2 hold.

    Examples
    --------
    >>> from blockchainkit.consensus import oral_messages
    >>> oral_messages(4, {3}, "attack", rounds=1).decisions
    {1: 'attack', 2: 'attack'}
    """
    integer(generals, "generals", 3)
    integer(rounds, "rounds")
    if order not in (ATTACK, RETREAT):
        raise ValueError("order must be 'attack' or 'retreat'")
    if any(t not in range(generals) for t in traitors):
        raise ValueError("traitors must be general numbers")

    def send(sender: int, receiver: int, value: str) -> str:
        return lie(sender, receiver, value) if sender in traitors else value

    def om(m: int, commander: int, value: str, lieutenants: list[int]) -> dict[int, str]:
        received = {lt: send(commander, lt, value) for lt in lieutenants}
        if m == 0:
            return received
        relayed = {
            j: om(m - 1, j, received[j], [lt for lt in lieutenants if lt != j]) for j in lieutenants
        }
        return {
            lt: _majority([received[lt]] + [relayed[j][lt] for j in lieutenants if j != lt])
            for lt in lieutenants
        }

    result = om(rounds, 0, order, list(range(1, generals)))
    loyal = {g: v for g, v in result.items() if g not in traitors}
    agreement = len(set(loyal.values())) <= 1
    validity = 0 in traitors or all(v == order for v in loyal.values())
    return GeneralsResult(loyal, agreement, validity)
