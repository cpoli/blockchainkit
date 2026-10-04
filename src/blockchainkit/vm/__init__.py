"""A small deterministic virtual machine for execution and gas experiments."""

from blockchainkit.vm.execution import ExecutionResult, Instruction, VMError, execute

__all__ = ["ExecutionResult", "Instruction", "VMError", "execute"]
