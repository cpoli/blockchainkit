"""Instruction type, errors, and result containers for blockchainkit.vm."""

from collections.abc import Mapping
from dataclasses import dataclass

Instruction = tuple[str, int | None]
"""An ``(opcode, operand)`` pair; the operand is ``None`` for simple opcodes."""


@dataclass(frozen=True)
class TraceStep:
    """Machine state just after one executed instruction.

    Attributes
    ----------
    pc : int
        Index of the instruction that ran.
    opcode : str
        Its opcode.
    operand : int or None
        Its operand.
    stack : tuple of int
        Stack after the instruction, bottom first.
    storage : Mapping
        Working storage after the instruction (committed only on success).
    gas_used : int
        Cumulative gas, including this instruction.
    """

    pc: int
    opcode: str
    operand: int | None
    stack: tuple[int, ...]
    storage: Mapping[int, int]
    gas_used: int


class VMError(ValueError):
    """Invalid instruction, stack operation, arithmetic operation, or resource limit.

    Attributes
    ----------
    trace : tuple of TraceStep
        Steps executed before the failure, when ``execute(..., trace=True)``
        was requested; otherwise empty.
    """

    trace: tuple[TraceStep, ...] = ()


@dataclass(frozen=True)
class ExecutionResult:
    """Final stack, read-only storage, consumed gas, and optional step trace."""

    stack: tuple[int, ...]
    storage: Mapping[int, int]
    gas_used: int
    trace: tuple[TraceStep, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of static bytecode verification.

    Attributes
    ----------
    max_depth : int
        The largest stack height any path can reach.
    errors : tuple of str
        Every problem found; empty if the program is safe.
    """

    max_depth: int
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True if no path can underflow and every join agrees on the stack height."""
        return not self.errors


@dataclass(frozen=True)
class TuringRun:
    """How a Turing machine run ended.

    Attributes
    ----------
    outcome : str
        ``"halted"``, ``"looping"`` (a configuration repeated, so it never
        halts), or ``"unknown"`` (the step budget ran out first).
    steps : int
        Steps executed, counting the halting transition.
    ones : int
        Number of 1s on the tape at the end.
    """

    outcome: str
    steps: int
    ones: int


@dataclass(frozen=True)
class BusyBeaverResult:
    """The longest-running halting machine found by an exhaustive search.

    Attributes
    ----------
    steps : int
        Its number of steps: the busy-beaver value S if no unknown machine halts later.
    ones : int
        The 1s it leaves on the tape.
    machine : dict
        Its rules, ``(state, symbol) -> (write, move, next_state)``.
    counts : dict
        Machines per outcome: ``"halted"``, ``"looping"``, ``"unknown"``.
    """

    steps: int
    ones: int
    machine: dict[tuple[str, int], tuple[int, int, str]]
    counts: dict[str, int]


@dataclass(frozen=True)
class ScriptResult:
    """Outcome of validating a Bitcoin-style script pair.

    Attributes
    ----------
    valid : bool
        Both scripts ran without error and left a true value on top.
    stack : tuple of bytes
        The final stack, bottom first.
    error : str or None
        Why validation failed, if it did.
    operations : int
        Opcodes and pushes executed. Scripts have no loops, so this never
        exceeds the combined script length.
    """

    valid: bool
    stack: tuple[bytes, ...]
    error: str | None
    operations: int


@dataclass(frozen=True)
class ReentrancyResult:
    """What an attacker withdrew from a bank contract.

    Attributes
    ----------
    withdrawn : int
        Total paid out to the attacker.
    deposited : int
        What the attacker had deposited.
    calls : int
        Times ``withdraw`` was entered, including re-entries.
    bank_balance : int
        Funds left in the bank afterwards.
    """

    withdrawn: int
    deposited: int
    calls: int
    bank_balance: int

    @property
    def stolen(self) -> int:
        """Withdrawn beyond the attacker's own deposit."""
        return self.withdrawn - self.deposited
