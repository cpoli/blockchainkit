"""A bounded deterministic 256-bit stack machine with atomic storage updates.

Instruction encoding: each instruction is a (opcode, operand) pair. Only
PUSH, LOAD, STORE, JMP, and JZ take an integer operand. All instructions cost
one teaching gas unit unless a schedule says otherwise; this is not an EVM
implementation or cost schedule.
"""

from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.constants import WORD_MODULUS
from blockchainkit.vm.core.base import ExecutionResult, Instruction, TraceStep, VMError

OPERAND_OPCODES = frozenset({"PUSH", "LOAD", "STORE", "JMP", "JZ"})
"""Opcodes that take a 256-bit integer operand."""

STACK_EFFECTS: Mapping[str, tuple[int, int]] = MappingProxyType(
    {
        "PUSH": (0, 1),
        "LOAD": (0, 1),
        "STORE": (1, 0),
        "JMP": (0, 0),
        "JZ": (1, 0),
        "ADD": (2, 1),
        "SUB": (2, 1),
        "MUL": (2, 1),
        "DIV": (2, 1),
        "EQ": (2, 1),
        "LT": (2, 1),
        "DUP": (1, 2),
        "DROP": (1, 0),
        "SWAP": (2, 2),
        "OVER": (2, 3),
        "ROT": (3, 3),
        "STOP": (0, 0),
        "REVERT": (0, 0),
    }
)
"""Values each opcode pops and pushes, as ``(pops, pushes)``.

Forth writes these as stack diagrams: ``OVER`` is ``( a b -- a b a )`` and
``ROT`` is ``( a b c -- b c a )``.
"""

OPCODES = frozenset(STACK_EFFECTS)
"""Every opcode the machine accepts."""

_ARITHMETIC = frozenset({"ADD", "SUB", "MUL", "DIV", "EQ", "LT"})


def check_word(value: int, name: str) -> None:
    """Raise VMError unless ``value`` is an int in ``[0, 2**256)``."""
    if type(value) is not int or not 0 <= value < WORD_MODULUS:
        raise VMError(f"{name} must be a 256-bit word")


def validate_program(program: Iterable[Instruction]) -> tuple[Instruction, ...]:
    """Check every instruction's shape before anything runs; return the program as a tuple.

    Raises
    ------
    VMError
        An unknown opcode, a missing or extra operand, an operand outside
        256 bits, or a jump target outside the program.
    """
    code = tuple(program)
    for instruction in code:
        if not isinstance(instruction, tuple) or len(instruction) != 2:
            raise VMError("instructions must be (opcode, operand) pairs")
        op, arg = instruction
        if not isinstance(op, str) or op not in OPCODES:
            raise VMError(f"unknown opcode: {op}")
        if op in OPERAND_OPCODES:
            if type(arg) is not int or not 0 <= arg < WORD_MODULUS:
                raise VMError(f"{op} requires a 256-bit integer operand")
            if op in {"JMP", "JZ"} and arg >= len(code):
                raise VMError("jump target outside program")
        elif arg is not None:
            raise VMError(f"{op} takes no operand")
    return code


def execute(
    program: Iterable[Instruction],
    *,
    storage: Mapping[int, int] | None = None,
    arguments: Sequence[int] = (),
    gas_limit: int = 10_000,
    stack_limit: int = 1024,
    gas_costs: Mapping[str, int] | None = None,
    trace: bool = False,
) -> ExecutionResult:
    """Execute a program against a copy of storage, committing only on success.

    Parameters
    ----------
    program : iterable of tuple
        (opcode, operand) pairs. For binary operations the top value is the
        right operand: PUSH 7; PUSH 2; SUB produces 5.
    storage : mapping, optional
        Initial 256-bit integer keys and values. Never mutated by execution.
    arguments : sequence of int
        Initial stack, bottom first: the call's inputs, like a contract's
        call data.
    gas_limit : int
        Maximum total gas, including STOP.
    stack_limit : int
        Maximum stack depth.
    gas_costs : mapping, optional
        Per-opcode gas prices overriding the default of one unit each, for
        experiments with a cost schedule. Unlisted opcodes cost one unit;
        every price must be at least one, so gas always bounds the run.
    trace : bool
        Record a :class:`~blockchainkit.vm.core.base.TraceStep` after every
        executed instruction, in ``ExecutionResult.trace`` on success or
        ``VMError.trace`` on failure.

    Returns
    -------
    ExecutionResult
        Deterministic stack, storage, gas used, and the trace if requested.

    Raises
    ------
    VMError
        Malformed program, stack underflow or overflow, division by zero,
        ``REVERT``, or running out of gas. Storage is then left unchanged.

    Examples
    --------
    >>> from blockchainkit.vm import execute
    >>> execute([("PUSH", 7), ("PUSH", 2), ("SUB", None)]).stack
    (5,)
    >>> [step.stack for step in execute([("PUSH", 7), ("DUP", None)], trace=True).trace]
    [(7,), (7, 7)]
    >>> execute([("MUL", None)], arguments=(6, 7)).stack
    (42,)
    """
    integer(gas_limit, "gas_limit")
    integer(stack_limit, "stack_limit", 1)
    code = validate_program(program)
    state = dict(storage or {})
    for key, value in state.items():
        if type(key) is not int or type(value) is not int:
            raise VMError("storage keys and values must be integers")
        check_word(key, "storage keys and values")
        check_word(value, "storage keys and values")
    stack = list(arguments)
    for value in stack:
        check_word(value, "every argument")
    if len(stack) > stack_limit:
        raise VMError("stack limit exceeded")
    prices = dict(gas_costs or {})
    for name, price in prices.items():
        if name not in OPCODES:
            raise VMError(f"gas schedule names an unknown opcode: {name}")
        # A zero price would let a loop run forever without exhausting gas.
        integer(price, f"gas cost of {name}", 1)
    steps: list[TraceStep] = []
    try:
        gas_used = _run(
            code, stack, state, prices, gas_limit, stack_limit, steps if trace else None
        )
    except VMError as error:
        error.trace = tuple(steps)
        raise
    return ExecutionResult(tuple(stack), MappingProxyType(state), gas_used, tuple(steps))


def _run(
    code: tuple[Instruction, ...],
    stack: list[int],
    state: dict[int, int],
    prices: Mapping[str, int],
    gas_limit: int,
    stack_limit: int,
    steps: list[TraceStep] | None,
) -> int:
    pc = gas_used = 0
    while pc < len(code):
        start = pc
        op, arg = code[pc]
        price = prices.get(op, 1)
        if gas_used + price > gas_limit:
            raise VMError("out of gas")
        gas_used += price
        pc += 1
        if len(stack) < STACK_EFFECTS[op][0]:
            raise VMError("stack underflow")
        if op == "REVERT":
            raise VMError("reverted")
        if op == "STOP":
            if steps is not None:
                steps.append(TraceStep(start, op, arg, tuple(stack), dict(state), gas_used))
            break
        if op in OPERAND_OPCODES:
            assert arg is not None  # Checked for every operand opcode before execution.
            if op == "PUSH":
                stack.append(arg)
            elif op == "LOAD":
                stack.append(state.get(arg, 0))
            elif op == "STORE":
                state[arg] = stack.pop()
            elif op == "JMP" or stack.pop() == 0:
                pc = arg
        elif op in _ARITHMETIC:
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
        elif op == "DUP":
            stack.append(stack[-1])
        elif op == "DROP":
            stack.pop()
        elif op == "SWAP":
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == "OVER":
            stack.append(stack[-2])
        else:  # ROT: ( a b c -- b c a )
            stack.append(stack.pop(-3))
        if len(stack) > stack_limit:
            raise VMError("stack limit exceeded")
        if steps is not None:
            steps.append(TraceStep(start, op, arg, tuple(stack), dict(state), gas_used))
    return gas_used
