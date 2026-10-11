"""Property-based fuzzing of contracts: Echidna (2020).

Echidna, from Trail of Bits, tests a contract the way QuickCheck (Claessen
and Hughes, 2000) tests a function: the author writes *properties* that
must always hold, and the fuzzer sends random sequences of transactions,
with random senders and arguments, checking every property after each one.
A failing sequence is then *shrunk*, by dropping transactions while it still
fails, to a short counterexample a person can read.

Unlike symbolic execution, fuzzing needs no model of the code, scales to
any contract, and never reports a bug that is not real; it only finds what
random sequences reach.
"""

import random
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from blockchainkit._validation import integer
from blockchainkit._validation import seed as _check_seed
from blockchainkit.contracts.core.base import FuzzCall, FuzzResult
from blockchainkit.contracts.systems.world import World


def _fails(
    setup: Callable[[World], str],
    sequence: Sequence[FuzzCall],
    prop: Callable[[World, str], bool],
) -> bool:
    world = World()
    target = setup(world)
    for call in sequence:
        world.transact(call.sender, target, call.function, *call.args)
        if not prop(world, target):
            return True
    return False


def shrink(
    setup: Callable[[World], str],
    sequence: Sequence[FuzzCall],
    prop: Callable[[World, str], bool],
) -> tuple[FuzzCall, ...]:
    """Drop transactions from a failing sequence, one at a time, while it still fails.

    The result is 1-minimal: removing any single transaction makes it pass.
    """
    current = list(sequence)
    index = 0
    while index < len(current):
        candidate = current[:index] + current[index + 1 :]
        if _fails(setup, candidate, prop):
            current = candidate
        else:
            index += 1
    return tuple(current)


def fuzz(
    setup: Callable[[World], str],
    functions: Mapping[str, Sequence[Sequence[Any]]],
    prop: Callable[[World, str], bool],
    *,
    senders: Sequence[str],
    runs: int = 100,
    depth: int = 10,
    seed: int = 0,
) -> FuzzResult:
    """Send random transaction sequences to a contract until a property fails.

    Parameters
    ----------
    setup : callable
        Given a fresh :class:`~blockchainkit.contracts.systems.world.World`,
        deploy the contract under test and return its address.
    functions : mapping
        For each function to call, the candidate values of each argument.
    prop : callable
        ``prop(world, target)`` must stay True; it is checked after every
        transaction, reverted or not.
    senders : sequence of str
        Accounts that send the transactions.
    runs : int
        Random sequences to try.
    depth : int
        Transactions per sequence.
    seed : int
        Seeds the choice of functions, arguments and senders.

    Returns
    -------
    FuzzResult
        The shrunk counterexample, if one was found, and the effort spent.

    Examples
    --------
    >>> from blockchainkit.contracts import ERC20, fuzz
    >>> def setup(world):
    ...     return world.deploy("alice", ERC20, 100)
    >>> def conserved(world, token):
    ...     return world.view(token, "total_supply") == 100
    >>> fuzz(setup, {"transfer": [["alice", "bob"], [0, 50]]}, conserved,
    ...      senders=["alice", "bob"], runs=5).failed
    False
    """
    integer(runs, "runs", 1)
    integer(depth, "depth", 1)
    _check_seed(seed)
    if not functions:
        raise ValueError("give at least one function to call")
    if not senders:
        raise ValueError("give at least one sender")
    rng = random.Random(seed)
    names = sorted(functions)
    transactions = 0
    for run in range(1, runs + 1):
        world = World()
        target = setup(world)
        sequence: list[FuzzCall] = []
        for _ in range(depth):
            name = rng.choice(names)
            args = tuple(rng.choice(list(choices)) for choices in functions[name])
            call = FuzzCall(rng.choice(list(senders)), name, args)
            sequence.append(call)
            world.transact(call.sender, target, call.function, *call.args)
            transactions += 1
            if not prop(world, target):
                shrunk = shrink(setup, sequence, prop)
                return FuzzResult(True, shrunk, transactions, run, transactions, len(sequence))
    return FuzzResult(False, (), None, runs, transactions, 0)
