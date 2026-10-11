"""Errors, expression type, and result containers for blockchainkit.contracts."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

Expr = int | str | tuple[Any, ...]
"""An integer constant, a variable name, or ``(operator, operand, ...)``
with operators such as ``"+"``, ``"<"``, ``"and"`` and ``"not"``: a symbolic
expression."""


class ContractError(ValueError):
    """A revert: the call fails, and every state change it made is undone."""


@dataclass(frozen=True)
class CallRecord:
    """One call in a transaction's call tree, in the order the calls began.

    Attributes
    ----------
    depth : int
        Nesting depth; the transaction's own call is 0.
    kind : str
        ``"call"``, ``"delegatecall"`` or ``"create"``.
    sender : str
        ``msg.sender`` of the call.
    to : str
        The address whose code ran.
    context : str
        The address whose storage and balance the code used: ``to``, except
        for a ``delegatecall``, where it is the caller.
    function : str or None
        The function called; None for a plain payment.
    value : int
        Ether sent with the call.
    gas_used : int
        Gas the call consumed, including its own nested calls.
    error : str or None
        Why the call reverted, if it did.
    """

    depth: int
    kind: str
    sender: str
    to: str
    context: str
    function: str | None
    value: int
    gas_used: int
    error: str | None

    @property
    def ok(self) -> bool:
        """True if the call returned without reverting."""
        return self.error is None


@dataclass(frozen=True)
class Event:
    """A log entry emitted by a contract.

    Attributes
    ----------
    emitter : str
        The address in whose context the code emitted it.
    name : str
        The event name, such as ``"Transfer"``.
    fields : Mapping
        Its named values.
    """

    emitter: str
    name: str
    fields: Mapping[str, Any]


@dataclass(frozen=True)
class Receipt:
    """What a transaction did.

    Attributes
    ----------
    success : bool
        False if the top-level call reverted; its state changes were then undone.
    result : Any
        The called function's return value (None on failure).
    error : str or None
        The revert reason, on failure.
    gas_used : int
        Gas consumed, including the fixed transaction cost.
    calls : tuple of CallRecord
        Every call made, in the order they began, reverted ones included.
    events : tuple of Event
        Events emitted by calls that did not revert; empty on failure.
    """

    success: bool
    result: Any
    error: str | None
    gas_used: int
    calls: tuple[CallRecord, ...]
    events: tuple[Event, ...]


@dataclass(frozen=True)
class TripleResult:
    """Outcome of checking a Hoare triple ``{P} S {Q}`` on every state of a finite domain.

    Attributes
    ----------
    holds : bool
        True if every state satisfying P that runs S to completion satisfies Q.
    checked : int
        States of the domain that satisfy P.
    counterexample : Mapping or None
        A starting state for which the triple fails.
    """

    holds: bool
    checked: int
    counterexample: Mapping[str, int] | None


@dataclass(frozen=True)
class SymbolicPath:
    """One execution path found by symbolic execution.

    Attributes
    ----------
    conditions : tuple of Expr
        The path condition: every branch decision taken, as expressions over
        the symbolic inputs. Inputs satisfying all of them follow this path.
    outcome : str
        How the path ends: ``"ok"``, ``"reverted"`` or ``"assertion"`` for
        programs, ``"stop"``, ``"revert"``, ``"error"`` or ``"bound"`` for
        bytecode.
    state : Mapping
        The variables the path assigned (for bytecode, the storage slots it
        read or wrote, as ``slot<k>``), as expressions over the inputs.
    decisions : tuple of bool
        The branch taken at each fork, in order, for drawing the tree.
    """

    conditions: tuple[Expr, ...]
    outcome: str
    state: Mapping[str, Expr]
    decisions: tuple[bool, ...]


@dataclass(frozen=True)
class SymbolicResult:
    """Every path through a program, up to the exploration bound.

    Attributes
    ----------
    paths : tuple of SymbolicPath
        In depth-first order, the taken branch first.
    variables : tuple of str
        The symbolic inputs, sorted.
    complete : bool
        False if a path hit the step bound, so some behavior is unexplored.
    """

    paths: tuple[SymbolicPath, ...]
    variables: tuple[str, ...]
    complete: bool

    @property
    def outcomes(self) -> dict[str, int]:
        """Number of paths ending in each outcome."""
        return dict(Counter(path.outcome for path in self.paths))


@dataclass(frozen=True)
class FuzzCall:
    """One transaction of a fuzzing campaign.

    Attributes
    ----------
    sender : str
        Who sends it.
    function : str
        The target contract's function.
    args : tuple
        Its arguments.
    """

    sender: str
    function: str
    args: tuple[Any, ...]


@dataclass(frozen=True)
class FuzzResult:
    """Outcome of a property-based fuzzing campaign.

    Attributes
    ----------
    failed : bool
        True if some sequence of transactions broke the property.
    sequence : tuple of FuzzCall
        The shrunk failing sequence; empty if none was found.
    found_after : int or None
        Transactions executed, over all runs, until the first failure.
    runs : int
        Random sequences executed.
    transactions : int
        Transactions executed in total, shrinking excluded.
    original_length : int
        Length of the failing sequence before shrinking (0 if none).
    """

    failed: bool
    sequence: tuple[FuzzCall, ...]
    found_after: int | None
    runs: int
    transactions: int
    original_length: int


@dataclass(frozen=True)
class RicardianContract:
    """A Ricardian contract: prose and parameters, signed, and named by their hash.

    Attributes
    ----------
    text : str
        The human-readable terms, with ``{name}`` placeholders for parameters.
    parameters : Mapping
        The machine-readable values the program uses.
    issuer : tuple of int
        The issuer's public key.
    signature : SchnorrSignature
        The issuer's signature over :attr:`digest`.
    digest : bytes
        SHA-256 of the domain tag and the canonical encoding of text and
        parameters: the contract's identifier.
    """

    text: str
    parameters: Mapping[str, int | str]
    issuer: tuple[int, int]
    signature: Any
    digest: bytes

    @property
    def identifier(self) -> str:
        """The digest in hex, as payments cite it."""
        return self.digest.hex()

    @property
    def rendered(self) -> str:
        """The prose with every parameter filled in, as a person reads it."""
        return self.text.format(**self.parameters)
