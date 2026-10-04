"""Static bytecode verification (Gosling 1995; the Java virtual machine).

Java's virtual machine checks downloaded code *before* running it, so the
interpreter can skip run-time checks. The verifier follows every path
through the program, tracking how many values are on the stack at each
instruction, without running anything. It rejects code that could
underflow the stack on some path, or that reaches the same instruction with
different stack heights along different paths (as a loop that pushes on
every turn does). Code that passes has a known maximum stack depth.
"""

from collections.abc import Iterable

from blockchainkit._validation import integer
from blockchainkit.vm.core.base import Instruction, VerificationResult
from blockchainkit.vm.systems.stack_machine import STACK_EFFECTS, validate_program


def verify_bytecode(program: Iterable[Instruction], *, arguments: int = 0) -> VerificationResult:
    """Check stack safety on every path and compute the maximum stack depth.

    This is abstract interpretation: the abstract state at an instruction is
    a single number, the stack height on entry. Starting from ``arguments``
    at instruction 0, the verifier propagates heights along every edge
    (both outcomes of ``JZ``) until nothing changes.

    Parameters
    ----------
    program : iterable of tuple
        Instructions, validated for shape first.
    arguments : int
        Values on the stack when execution starts.

    Returns
    -------
    VerificationResult
        ``max_depth`` and the list of problems found; ``ok`` if there are none.

    Examples
    --------
    >>> from blockchainkit.vm import verify_bytecode
    >>> verify_bytecode([("PUSH", 1), ("ADD", None)]).errors
    ('pc 1: ADD needs 2 values but only 1 can be on the stack',)
    >>> verify_bytecode([("PUSH", 1), ("PUSH", 2), ("ADD", None)]).max_depth
    2
    """
    code = validate_program(program)
    integer(arguments, "arguments")
    heights: dict[int, int] = {0: arguments} if code else {}
    errors: list[str] = []
    pending = [0] if code else []
    max_depth = arguments
    while pending:
        pc = pending.pop()
        height = heights[pc]
        op, arg = code[pc]
        pops, pushes = STACK_EFFECTS[op]
        if height < pops:
            errors.append(
                f"pc {pc}: {op} needs {pops} values but only {height} can be on the stack"
            )
            continue
        after = height - pops + pushes
        max_depth = max(max_depth, after)
        if op in {"STOP", "REVERT"}:
            continue
        successors = [] if op == "JMP" else [pc + 1]
        if op in {"JMP", "JZ"}:
            assert arg is not None  # Jumps always carry a validated target.
            successors.append(arg)
        for target in successors:
            if target >= len(code):
                continue  # Falling off the end halts normally.
            if target not in heights:
                heights[target] = after
                pending.append(target)
            elif heights[target] != after:
                message = f"pc {target}: reached with stack heights {heights[target]} and {after}"
                if message not in errors:
                    errors.append(message)
    return VerificationResult(max_depth, tuple(errors))
