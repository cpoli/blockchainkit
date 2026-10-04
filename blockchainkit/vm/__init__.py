"""A small deterministic virtual machine for execution and gas experiments."""

from blockchainkit.vm.core.base import ExecutionResult, Instruction, VMError
from blockchainkit.vm.systems.stack_machine import execute

__all__ = ["ExecutionResult", "Instruction", "VMError", "execute"]
