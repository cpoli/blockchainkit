r"""Duplex micropayment channels (Decker and Wattenhofer, 2015).

A Spilman channel pays in one direction only, and is used up once its
capacity has been paid. Decker and Wattenhofer pair two of them, one each
way, so payments can flow back and forth, and *reset* them when one runs
dry: the parties sign a new pair whose capacities are the current balances.
The old pair must then become unpublishable, and without a penalty
mechanism they used time locks to rank the states.

The pairs hang below an *invalidation tree*: a chain of ``d`` transactions,
each spending its parent, from the funding output down to the current
pair. Each transaction can be confirmed only a set number of blocks after
its parent (a relative lock time), and replacing a node lowers that number
by ``delta``. Of two branches that diverge at some level, the
newer one has the lower lock time there, so it can be confirmed first and
spends the shared parent before the older one is valid. With ``steps``
lock-time values per level, the tree supports ``steps ** d`` resets, and
the state with digits ``c_0 ... c_{d-1}`` in base ``steps`` has lock times

.. math::

   t_l = \text{base} + (\text{steps} - 1 - c_l)\,\delta.
"""

from collections.abc import Iterable
from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import Settlement


def invalidation_locktimes(
    state: int, *, depth: int, steps: int, delta: int, base: int = 0
) -> tuple[int, ...]:
    """Lock times along the invalidation tree's branch for reset number ``state``.

    Parameters
    ----------
    state : int
        The reset counter, below ``steps ** depth``.
    depth : int
        Levels of the tree.
    steps : int
        Lock-time values per level.
    delta : int
        Blocks between successive lock times of a node.
    base : int
        The smallest lock time.

    Returns
    -------
    tuple of int
        One lock time per level, root first.

    Examples
    --------
    >>> from blockchainkit.channels import invalidation_locktimes
    >>> [invalidation_locktimes(s, depth=2, steps=3, delta=10) for s in (0, 1, 3, 8)]
    [(20, 20), (20, 10), (10, 20), (0, 0)]
    """
    integer(depth, "depth", 1)
    integer(steps, "steps", 2)
    integer(delta, "delta", 1)
    integer(base, "base")
    integer(state, "state")
    if state >= steps**depth:
        raise ValueError(f"the tree supports only {steps**depth} states")
    digits = []
    for _ in range(depth):
        state, digit = divmod(state, steps)
        digits.append(digit)
    return tuple(base + (steps - 1 - c) * delta for c in reversed(digits))


def first_confirmed(published: Iterable[int], *, depth: int, steps: int, delta: int) -> int:
    """Which of several published branches the chain confirms.

    At the first level where two branches differ, the one with the lower
    lock time becomes valid first and spends the shared parent output,
    which invalidates the other; Python's tuple order compares exactly so.

    Examples
    --------
    >>> from blockchainkit.channels import first_confirmed
    >>> first_confirmed([2, 7, 5], depth=2, steps=3, delta=10)
    7
    """
    states = list(published)
    if not states:
        raise ValueError("no branch was published")
    return min(
        states,
        key=lambda s: invalidation_locktimes(s, depth=depth, steps=steps, delta=delta),
    )


class DuplexChannel:
    """Two one-way channels under an invalidation tree.

    Parameters
    ----------
    parties : tuple of str
        The two parties.
    deposits : tuple of int
        Each party's initial capacity in its outgoing channel.
    depth, steps, delta : int
        The invalidation tree; see :func:`invalidation_locktimes`.

    Examples
    --------
    >>> from blockchainkit.channels import DuplexChannel
    >>> channel = DuplexChannel(("alice", "bob"), (10, 10), depth=2, steps=4, delta=6)
    >>> for _ in range(3):
    ...     channel.pay("alice", 8)
    ...     channel.pay("bob", 8)
    >>> channel.balances(), channel.resets
    ({'alice': 10, 'bob': 10}, 2)
    """

    def __init__(
        self,
        parties: tuple[str, str],
        deposits: tuple[int, int],
        *,
        depth: int,
        steps: int,
        delta: int,
    ) -> None:
        if len(set(parties)) != 2:
            raise ValueError("a channel needs two distinct parties")
        for deposit in deposits:
            integer(deposit, "deposit")
        self.parties = parties
        self.depth, self.steps, self.delta = depth, steps, delta
        invalidation_locktimes(0, depth=depth, steps=steps, delta=delta)  # Validates the tree.
        self._capacity = dict(zip(parties, deposits, strict=True))
        self._sent = dict.fromkeys(parties, 0)
        self.resets = 0

    def balances(self) -> dict[str, int]:
        """What each party would receive if the channel closed now."""
        first, second = self.parties
        return {
            first: self._capacity[first] - self._sent[first] + self._sent[second],
            second: self._capacity[second] - self._sent[second] + self._sent[first],
        }

    def pay(self, sender: str, amount: int) -> None:
        """Pay through the sender's one-way channel, resetting both if it runs dry.

        Raises
        ------
        ValueError
            The sender's balance is too small, or the tree has no resets left.
        """
        if sender not in self.parties:
            raise ValueError(f"{sender!r} is not a party to the channel")
        integer(amount, "amount", 1)
        if amount > self.balances()[sender]:
            raise ValueError("insufficient balance")
        if self._sent[sender] + amount > self._capacity[sender]:
            if self.resets + 1 >= self.steps**self.depth:
                raise ValueError("the invalidation tree is exhausted; close the channel")
            self._capacity = self.balances()
            self._sent = dict.fromkeys(self.parties, 0)
            self.resets += 1
        self._sent[sender] += amount

    def locktimes(self) -> tuple[int, ...]:
        """The current branch's lock times, root first."""
        return invalidation_locktimes(
            self.resets, depth=self.depth, steps=self.steps, delta=self.delta
        )

    def close(self, *, height: int) -> Settlement:
        """Publish the current branch at ``height``; it settles after the sum of its lock times."""
        integer(height, "height")
        delay = sum(self.locktimes())
        payouts = MappingProxyType(self.balances())
        return Settlement("unilateral", payouts, height + delay, self.resets)
