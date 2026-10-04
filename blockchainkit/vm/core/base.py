"""Instruction type, error, and result container for blockchainkit.vm."""

from collections.abc import Mapping
from dataclasses import dataclass

Instruction = tuple[str, int | None]
"""An ``(opcode, operand)`` pair; the operand is ``None`` for simple opcodes."""


class VMError(ValueError):
    """Invalid instruction, stack operation, arithmetic operation, or resource limit."""


@dataclass(frozen=True)
class ExecutionResult:
    """Final stack, read-only storage, and consumed gas after successful execution."""

    stack: tuple[int, ...]
    storage: Mapping[int, int]
    gas_used: int
