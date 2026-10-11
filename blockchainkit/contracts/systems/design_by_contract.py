"""Design by contract: preconditions, postconditions and invariants (Meyer, 1986).

Meyer's Eiffel treats a routine as a contract between caller and supplier:
the caller must establish the *precondition*, the routine then guarantees
the *postcondition*, and every public routine preserves the class
*invariant*. Checked at run time, a violated clause is a bug in whichever
side broke its part, caught where it happens rather than where it shows.

Here :func:`requires` and :func:`ensures` decorate a contract's functions,
and :meth:`~blockchainkit.contracts.systems.world.Contract.invariant` is the
class invariant, checked by the world after every call. Any violation
reverts, which is how Solidity's ``require`` (precondition) and ``assert``
(internal invariant) behave. Checking costs no gas here; on chain it would.
"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from blockchainkit.contracts.core.base import ContractError
from blockchainkit.contracts.systems.world import Contract, _slot, _unmetered

F = TypeVar("F", bound=Callable[..., Any])


def requires(
    predicate: Callable[..., object], message: str = "precondition failed"
) -> Callable[[F], F]:
    """Revert with ``message`` unless ``predicate(self, *args)`` holds when the function is called.

    Examples
    --------
    >>> from blockchainkit.contracts import Contract, World, requires
    >>> class Counter(Contract):
    ...     layout = ("count",)
    ...     @requires(lambda self, step: step > 0, "step must be positive")
    ...     def add(self, step):
    ...         self.write("count", self.read("count") + step)
    >>> world = World()
    >>> counter = world.deploy("alice", Counter)
    >>> world.transact("alice", counter, "add", 0).error
    'step must be positive'
    """

    def decorate(function: F) -> F:
        @functools.wraps(function)
        def checked(self: Contract, *args: Any) -> Any:
            with _unmetered(self._frame):
                held = predicate(self, *args)
            if not held:
                raise ContractError(message)
            return function(self, *args)

        return checked  # type: ignore[return-value]

    return decorate


def ensures(
    predicate: Callable[..., object], message: str = "postcondition failed"
) -> Callable[[F], F]:
    """Revert with ``message`` unless ``predicate(self, old, result, *args)`` holds on return.

    ``old(name, *keys)`` reads a storage field as it was when the function
    was called, Eiffel's ``old`` expression; ``result`` is the return value.

    Examples
    --------
    >>> from blockchainkit.contracts import Contract, World, ensures
    >>> class Counter(Contract):
    ...     layout = ("count",)
    ...     @ensures(lambda self, old, result: self.read("count") == old("count") + 1)
    ...     def increment(self):
    ...         self.write("count", self.read("count") + 2)  # A bug.
    >>> world = World()
    >>> world.transact("alice", world.deploy("alice", Counter), "increment").error
    'postcondition failed'
    """

    def decorate(function: F) -> F:
        @functools.wraps(function)
        def checked(self: Contract, *args: Any) -> Any:
            before = dict(self._world._storage.get(self.address, {}))
            code = type(self)

            def old(name: str, *keys: Any) -> Any:
                return before.get(_slot(code, name, keys), 0)

            result = function(self, *args)
            with _unmetered(self._frame):
                held = predicate(self, old, result, *args)
            if not held:
                raise ContractError(message)
            return result

        return checked  # type: ignore[return-value]

    return decorate
