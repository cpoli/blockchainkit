"""Symbolic execution: King (1976) and Oyente (2016).

King ran programs on *symbols* instead of numbers. Each variable holds an
expression over the inputs, and each branch on an expression forks the run.
Every path then carries a *path condition*, the conjunction of the branch
decisions it took, and any input that satisfies the condition drives a
concrete run down that path. Solving the condition of a path that fails an
assertion produces an input that triggers the bug.

Oyente (Luu et al., 2016) applied the idea to EVM bytecode with the Z3
solver, and found thousands of vulnerable contracts on the main network.
:func:`symbolic_bytecode` does the same for the stack machine of
:mod:`blockchainkit.vm`.

There is no SMT solver here: :func:`solve` searches a small set of
candidate values, the boundary values that bugs tend to hide behind (0, 1,
the constants of the program and their neighbors, and, for words, half the
modulus and the largest word). It finds what such a set contains and
reports nothing otherwise, so a None answer is not a proof.
"""

import itertools
from collections.abc import Iterable, Mapping, Sequence

from blockchainkit._validation import integer
from blockchainkit.constants import WORD_MODULUS
from blockchainkit.contracts.core.base import Expr, SymbolicPath, SymbolicResult
from blockchainkit.contracts.utils.expressions import (
    Statement,
    constants,
    evaluate,
    make,
    parse_program,
    substitute,
    variables,
)
from blockchainkit.vm.core.base import Instruction
from blockchainkit.vm.systems.stack_machine import STACK_EFFECTS, validate_program


def _free_variables(paths: Iterable[SymbolicPath]) -> tuple[str, ...]:
    found: set[str] = set()
    for path in paths:
        for condition in path.conditions:
            found |= variables(condition)
        for value in path.state.values():
            found |= variables(value)
    return tuple(sorted(found))


def symbolic_execute(
    program: str | Iterable[Statement], *, modulus: int | None = None
) -> SymbolicResult:
    """Explore every path of a program with symbolic inputs.

    Each ``if``, ``require`` and ``assert`` on a non-constant condition forks
    the run; a ``require`` that fails ends its path as ``"reverted"`` and an
    ``assert`` that fails as ``"assertion"``. Paths are not checked for
    feasibility: use :func:`solve` on their conditions.

    Parameters
    ----------
    program : str or iterable of Statement
        Source text or parsed statements.
    modulus : int, optional
        Word size for wrapping arithmetic.

    Examples
    --------
    >>> from blockchainkit.contracts import symbolic_execute
    >>> result = symbolic_execute("require(x > 10)\\nif x > 100:\\n    y = 1\\nelse:\\n    y = 2")
    >>> result.outcomes
    {'reverted': 1, 'ok': 2}
    """
    statements = parse_program(program) if isinstance(program, str) else tuple(program)
    paths: list[SymbolicPath] = []
    _explore(statements, {}, (), (), modulus, paths)
    return SymbolicResult(tuple(paths), _free_variables(paths), True)


def _explore(
    statements: tuple[Statement, ...],
    state: dict[str, Expr],
    conditions: tuple[Expr, ...],
    decisions: tuple[bool, ...],
    modulus: int | None,
    paths: list[SymbolicPath],
) -> None:
    for index, statement in enumerate(statements):
        kind = statement[0]
        if kind == "assign":
            state = {**state, statement[1]: substitute(statement[2], state, modulus)}
            continue
        condition = substitute(statement[1], state, modulus)
        rest = statements[index + 1 :]
        if kind == "if":
            branches = [(True, statement[2], condition), (False, statement[3], _negate(condition))]
            for taken, body, guard in branches:
                if type(guard) is int:
                    if guard:
                        _explore(body + rest, state, conditions, decisions, modulus, paths)
                    continue
                _explore(
                    body + rest,
                    state,
                    (*conditions, guard),
                    (*decisions, taken),
                    modulus,
                    paths,
                )
            return
        failure = "reverted" if kind == "require" else "assertion"
        if type(condition) is int:
            if condition:
                continue
            paths.append(_path(conditions, failure, state, decisions))
            return
        paths.append(_path((*conditions, _negate(condition)), failure, state, (*decisions, False)))
        conditions, decisions = (*conditions, condition), (*decisions, True)
    paths.append(_path(conditions, "ok", state, decisions))


def _negate(condition: Expr) -> Expr:
    return make("not", condition)


def _path(
    conditions: tuple[Expr, ...],
    outcome: str,
    state: Mapping[str, Expr],
    decisions: tuple[bool, ...],
) -> SymbolicPath:
    return SymbolicPath(conditions, outcome, dict(state), decisions)


def boundary_values(conditions: Iterable[Expr], *, modulus: int | None = None) -> tuple[int, ...]:
    """Candidate inputs for :func:`solve`: 0, 1, 2, every constant and its neighbors, and,
    for words, the largest value, half the modulus and its neighbors.

    Examples
    --------
    >>> from blockchainkit.contracts import boundary_values, parse_expression
    >>> boundary_values([parse_expression("x > 100")])
    (0, 1, 2, 99, 100, 101)
    """
    values = {0, 1, 2}
    for condition in conditions:
        for constant in constants(condition):
            values |= {constant - 1, constant, constant + 1}
    if modulus is not None:
        half = modulus // 2
        values |= {half - 1, half, half + 1, modulus - 1}
        return tuple(sorted(v for v in values if 0 <= v < modulus))
    return tuple(sorted(v for v in values if v >= 0))


def solve(
    conditions: Iterable[Expr],
    *,
    modulus: int | None = None,
    candidates: Iterable[int] | Mapping[str, Iterable[int]] | None = None,
    max_assignments: int = 1_000_000,
) -> dict[str, int] | None:
    """Find values of the variables that satisfy every condition, by bounded search.

    Parameters
    ----------
    conditions : iterable of Expr
        A path condition, possibly with extra constraints such as a bug's
        definition.
    modulus : int, optional
        Word size for wrapping arithmetic.
    candidates : iterable of int or mapping, optional
        Values to try, for every variable or per variable. Defaults to
        :func:`boundary_values`.
    max_assignments : int
        Refuse searches larger than this.

    Returns
    -------
    dict or None
        A satisfying assignment, or None if no candidate combination works.

    Examples
    --------
    >>> from blockchainkit.contracts import parse_expression, solve
    >>> solve([parse_expression("2 * x == 0"), parse_expression("x > 0")], modulus=2**256)
    {'x': 57896044618658097711785492504343953926634992332820282019728792003956564819968}
    """
    conditions = tuple(conditions)
    integer(max_assignments, "max_assignments", 1)
    names = sorted(set().union(*(variables(c) for c in conditions)))
    if candidates is None:
        default = boundary_values(conditions, modulus=modulus)
        pools = [default for _ in names]
    elif isinstance(candidates, Mapping):
        pools = [tuple(candidates[name]) for name in names]
    else:
        shared = tuple(candidates)
        pools = [shared for _ in names]
    size = 1
    for pool in pools:
        size *= len(pool)
    if size > max_assignments:
        raise ValueError(f"{size} assignments exceed max_assignments={max_assignments}")
    for combination in itertools.product(*pools):
        env = dict(zip(names, combination, strict=True))
        if all(evaluate(condition, env, modulus) for condition in conditions):
            return env
    return None


def symbolic_bytecode(
    program: Iterable[Instruction],
    *,
    arguments: Sequence[str] = (),
    max_steps: int = 1_000,
    max_paths: int = 1_000,
) -> SymbolicResult:
    """Execute a :mod:`blockchainkit.vm` program on symbolic arguments and storage.

    The arguments are symbols named by ``arguments`` (bottom of the stack
    first); storage slot ``k`` starts as the symbol ``s<k>``. ``JZ`` on a
    symbolic value forks, and so does ``DIV`` by a symbolic divisor, whose
    zero case is an error. Arithmetic wraps modulo ``2**256`` as in the
    machine. Each path's state holds every slot it read or wrote, as
    ``slot<k>``.

    Parameters
    ----------
    program : iterable of tuple
        The bytecode, as for
        :func:`~blockchainkit.vm.systems.stack_machine.execute`.
    arguments : sequence of str
        Names of the symbolic arguments.
    max_steps : int
        Instructions per path; a longer path ends as ``"bound"``.
    max_paths : int
        Paths in total; the search stops there.

    Examples
    --------
    >>> from blockchainkit.contracts import symbolic_bytecode
    >>> program = [("PUSH", 10), ("LT", None), ("JZ", 4), ("REVERT", None), ("STOP", None)]
    >>> symbolic_bytecode(program, arguments=("x",)).outcomes
    {'stop': 1, 'revert': 1}
    """
    code = validate_program(program)
    integer(max_steps, "max_steps", 1)
    integer(max_paths, "max_paths", 1)
    names = tuple(arguments)
    for name in names:
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError("argument names must be identifiers")
    paths: list[SymbolicPath] = []
    pending: list[_Branch] = [(0, list(names), {}, (), (), 0)]
    complete = True
    while pending:
        if len(paths) >= max_paths:
            complete = False
            break
        pc, stack, storage, conditions, decisions, steps = pending.pop()
        outcome = "stop"
        while pc < len(code):
            if steps >= max_steps:
                outcome, complete = "bound", False
                break
            steps += 1
            op, arg = code[pc]
            pc += 1
            if len(stack) < STACK_EFFECTS[op][0]:
                outcome = "error"
                break
            if op in ("REVERT", "STOP"):
                outcome = "revert" if op == "REVERT" else "stop"
                break
            if op in _SYMBOLS:
                right, left = stack.pop(), stack.pop()
                if op == "DIV" and type(right) is not int:
                    # The machine raises on division by zero: fork off that case.
                    paths.append(
                        _bytecode_path(
                            (*conditions, make("==", right, 0)),
                            "error",
                            storage,
                            (*decisions, False),
                        )
                    )
                    conditions = (*conditions, make("!=", right, 0))
                    decisions = (*decisions, True)
                elif op == "DIV" and right == 0:
                    outcome = "error"
                    break
                stack.append(make(_SYMBOLS[op], left, right, modulus=WORD_MODULUS))
            elif op == "JZ":
                value = stack.pop()
                if type(value) is not int:
                    pending.append(
                        (
                            pc,
                            list(stack),
                            dict(storage),
                            (*conditions, make("!=", value, 0)),
                            (*decisions, False),
                            steps,
                        )
                    )
                    conditions = (*conditions, make("==", value, 0))
                    decisions = (*decisions, True)
                    pc = int(arg)  # type: ignore[arg-type]
                elif value == 0:
                    pc = int(arg)  # type: ignore[arg-type]
            else:
                _stack_step(op, arg, stack, storage)
                if op == "JMP":
                    pc = int(arg)  # type: ignore[arg-type]
        paths.append(_bytecode_path(conditions, outcome, storage, decisions))
    return SymbolicResult(tuple(paths), _free_variables(paths), complete)


_Branch = tuple[int, list[Expr], dict[int, Expr], tuple[Expr, ...], tuple[bool, ...], int]
_SYMBOLS = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "//", "EQ": "==", "LT": "<"}


def _stack_step(op: str, arg: int | None, stack: list[Expr], storage: dict[int, Expr]) -> None:
    """Apply one instruction that neither branches nor computes."""
    if op == "PUSH":
        stack.append(int(arg))  # type: ignore[arg-type]
    elif op == "LOAD":
        stack.append(storage.setdefault(int(arg), f"s{arg}"))  # type: ignore[arg-type]
    elif op == "STORE":
        storage[int(arg)] = stack.pop()  # type: ignore[arg-type]
    elif op == "DUP":
        stack.append(stack[-1])
    elif op == "DROP":
        stack.pop()
    elif op == "SWAP":
        stack[-1], stack[-2] = stack[-2], stack[-1]
    elif op == "OVER":
        stack.append(stack[-2])
    elif op == "ROT":  # ( a b c -- b c a )
        stack.append(stack.pop(-3))


def _bytecode_path(
    conditions: tuple[Expr, ...],
    outcome: str,
    storage: Mapping[int, Expr],
    decisions: tuple[bool, ...],
) -> SymbolicPath:
    final = {f"slot{slot}": value for slot, value in sorted(storage.items())}
    return SymbolicPath(conditions, outcome, final, decisions)
