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
