"""A bounded deterministic 256-bit stack machine with atomic storage updates.

Instruction encoding: each instruction is a (opcode, operand) pair. Only
PUSH, LOAD, STORE, JMP, and JZ take an integer operand. All instructions cost
one teaching gas unit; this is not an EVM implementation or cost schedule.
"""

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.constants import WORD_MODULUS
from blockchainkit.vm.core.base import ExecutionResult, Instruction, VMError


def execute(
    program: Iterable[Instruction],
    *,
    storage: Mapping[int, int] | None = None,
    gas_limit: int = 10_000,
    stack_limit: int = 1024,
) -> ExecutionResult:
    """Execute a program against a copy of storage, committing only on success.

    Parameters
    ----------
    program : iterable of tuple
        (opcode, operand) pairs. For binary operations the top value is the
        right operand: PUSH 7; PUSH 2; SUB produces 5.
    storage : mapping, optional
        Initial 256-bit integer keys and values. Never mutated by execution.
    gas_limit : int
        Maximum executed instructions, including STOP.
    stack_limit : int
        Maximum stack depth.

    Returns
    -------
    ExecutionResult
        Deterministic stack, storage, and instruction count.

    Examples
    --------
    >>> from blockchainkit.vm import execute
    >>> execute([("PUSH", 7), ("PUSH", 2), ("SUB", None)]).stack
    (5,)
    """
    integer(gas_limit, "gas_limit")
    integer(stack_limit, "stack_limit", 1)
    code = tuple(program)
    state = dict(storage or {})
    for key, value in state.items():
        if type(key) is not int or type(value) is not int:
            raise VMError("storage keys and values must be integers")
        if not 0 <= key < WORD_MODULUS or not 0 <= value < WORD_MODULUS:
            raise VMError("storage keys and values must be 256-bit words")
    operands = {"PUSH", "LOAD", "STORE", "JMP", "JZ"}
    simple = {"ADD", "SUB", "MUL", "DIV", "EQ", "LT", "DUP", "DROP", "SWAP", "STOP"}
    for instruction in code:
        if not isinstance(instruction, tuple) or len(instruction) != 2:
            raise VMError("instructions must be (opcode, operand) pairs")
        op, arg = instruction
        if not isinstance(op, str) or op not in operands | simple:
            raise VMError(f"unknown opcode: {op}")
        if op in operands:
            if type(arg) is not int or not 0 <= arg < WORD_MODULUS:
                raise VMError(f"{op} requires a 256-bit integer operand")
            if op in {"JMP", "JZ"} and arg >= len(code):
                raise VMError("jump target outside program")
        elif arg is not None:
            raise VMError(f"{op} takes no operand")
    stack: list[int] = []
    pc = gas_used = 0
    while pc < len(code):
        if gas_used >= gas_limit:
            raise VMError("out of gas")
        gas_used += 1
        op, arg = code[pc]
        pc += 1
        needed = 2 if op in {"ADD", "SUB", "MUL", "DIV", "EQ", "LT", "SWAP"} else 0
        if op in {"DUP", "DROP", "STORE", "JZ"}:
            needed = 1
        if len(stack) < needed:
            raise VMError("stack underflow")
        if op == "STOP":
            break
        if op in operands:
            assert arg is not None  # Checked for every operand opcode before execution.
            if op == "PUSH":
                stack.append(arg)
            elif op == "LOAD":
                stack.append(state.get(arg, 0))
            elif op == "STORE":
                state[arg] = stack.pop()
            elif op == "JMP" or stack.pop() == 0:
                pc = arg
        elif op == "DUP":
            stack.append(stack[-1])
        elif op == "DROP":
            stack.pop()
        elif op == "SWAP":
            stack[-1], stack[-2] = stack[-2], stack[-1]
        else:
            right, left = stack.pop(), stack.pop()
            if op == "ADD":
                value = left + right
            elif op == "SUB":
                value = left - right
            elif op == "MUL":
                value = left * right
            elif op == "DIV":
                if right == 0:
                    raise VMError("division by zero")
                value = left // right
            elif op == "EQ":
                value = int(left == right)
            else:
                value = int(left < right)
            stack.append(value % WORD_MODULUS)
        if len(stack) > stack_limit:
            raise VMError("stack limit exceeded")
    return ExecutionResult(tuple(stack), MappingProxyType(state), gas_used)
