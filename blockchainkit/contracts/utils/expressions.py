"""A small expression and statement language shared by the verification tools.

Expressions are written in Python syntax and parsed with :mod:`ast` into
tuples: ``"balance - amount"`` becomes ``("-", "balance", "amount")``.
Supported: integer constants, names, ``+ - * // %``, comparisons, ``and``,
``or`` and ``not``. Booleans are the integers 0 and 1. Division and modulo by
zero give 0, as in the EVM.

Programs are Python source restricted to assignments to a name,
``if``/``else``, ``assert condition`` and ``require(condition)``: straight-line
code with branches, and no loops.
"""

import ast
from collections.abc import Mapping
from typing import Any

from blockchainkit.contracts.core.base import Expr

Statement = tuple[Any, ...]
"""``("assign", name, expr)``, ``("require", expr)``, ``("assert", expr)``,
or ``("if", expr, body, orelse)`` with statement tuples as bodies."""

_BINARY = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.FloorDiv: "//",
    ast.Div: "//",
    ast.Mod: "%",
}
_COMPARE = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}
_ARITHMETIC = frozenset(_BINARY.values())
_PRECEDENCE = {"or": 1, "and": 2, "not": 3, "+": 5, "-": 5, "*": 6, "//": 6, "%": 6}
_PRECEDENCE.update({op: 4 for op in _COMPARE.values()})


def _convert(node: ast.AST) -> Expr:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return int(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        return (_BINARY[type(node.op)], _convert(node.left), _convert(node.right))
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _COMPARE:
        return (_COMPARE[type(node.ops[0])], _convert(node.left), _convert(node.comparators[0]))
    if isinstance(node, ast.BoolOp):
        op = "and" if isinstance(node.op, ast.And) else "or"
        result = _convert(node.values[0])
        for value in node.values[1:]:
            result = (op, result, _convert(value))
        return result
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return ("not", _convert(node.operand))
    raise ValueError(f"unsupported expression: {ast.unparse(node)}")


def parse_expression(source: str) -> Expr:
    """Parse one expression.

    Examples
    --------
    >>> from blockchainkit.contracts import parse_expression
    >>> parse_expression("amount <= balance and amount > 0")
    ('and', ('<=', 'amount', 'balance'), ('>', 'amount', 0))
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression: {source!r}") from exc
    return _convert(tree.body)


def _statement(node: ast.stmt) -> Statement:
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        return ("assign", node.targets[0].id, _convert(node.value))
    if isinstance(node, ast.Assert):
        return ("assert", _convert(node.test))
    if (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "require"
        and len(node.value.args) == 1
    ):
        return ("require", _convert(node.value.args[0]))
    if isinstance(node, ast.If):
        body = tuple(_statement(child) for child in node.body)
        orelse = tuple(_statement(child) for child in node.orelse)
        return ("if", _convert(node.test), body, orelse)
    raise ValueError(f"unsupported statement: {ast.unparse(node)}")


def parse_program(source: str) -> tuple[Statement, ...]:
    """Parse a program of assignments, ``if``/``else``, ``assert`` and ``require(...)``.

    Examples
    --------
    >>> from blockchainkit.contracts import parse_program
    >>> parse_program("require(amount <= balance)\\nbalance = balance - amount")
    (('require', ('<=', 'amount', 'balance')), ('assign', 'balance', ('-', 'balance', 'amount')))
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    lines = [line for line in source.splitlines() if line.strip()]
    indent = min((len(line) - len(line.lstrip()) for line in lines), default=0)
    try:
        tree = ast.parse("\n".join(line[indent:] for line in lines))
    except SyntaxError as exc:
        raise ValueError("invalid program") from exc
    return tuple(_statement(node) for node in tree.body)


def make(op: str, *operands: Expr, modulus: int | None = None) -> Expr:
    """Build ``(op, *operands)``, folding it to a constant when every operand is one."""
    values = [operand for operand in operands if isinstance(operand, int)]
    if len(values) == len(operands):
        return _apply(op, values, modulus)
    inner = operands[0]
    if op == "not" and isinstance(inner, tuple) and inner[0] == "not":
        result: Expr = inner[1]
        return result
    return (op, *operands)


def _apply(op: str, values: list[int], modulus: int | None) -> int:
    if op == "not":
        return int(not values[0])
    a, b = values
    if op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "*":
        result = a * b
    elif op == "//":
        result = a // b if b else 0
    elif op == "%":
        result = a % b if b else 0
    elif op == "==":
        return int(a == b)
    elif op == "!=":
        return int(a != b)
    elif op == "<":
        return int(a < b)
    elif op == "<=":
        return int(a <= b)
    elif op == ">":
        return int(a > b)
    elif op == ">=":
        return int(a >= b)
    elif op == "and":
        return int(bool(a) and bool(b))
    elif op == "or":
        return int(bool(a) or bool(b))
    else:
        raise ValueError(f"unknown operator: {op}")
    return result % modulus if modulus is not None else result


def evaluate(expr: Expr, env: Mapping[str, int], modulus: int | None = None) -> int:
    """Evaluate ``expr`` on the values in ``env``; arithmetic wraps modulo ``modulus`` if given.

    Examples
    --------
    >>> from blockchainkit.contracts import evaluate, parse_expression
    >>> evaluate(parse_expression("2 * x"), {"x": 2**255}, modulus=2**256)
    0
    """
    if isinstance(expr, int):
        return expr
    if isinstance(expr, str):
        if expr not in env:
            raise KeyError(f"no value for variable {expr!r}")
        return env[expr]
    op, *operands = expr
    return _apply(op, [evaluate(operand, env, modulus) for operand in operands], modulus)


def substitute(expr: Expr, bindings: Mapping[str, Expr], modulus: int | None = None) -> Expr:
    """Replace variables by expressions, folding constants: ``Q[e/x]`` in Hoare's notation."""
    if isinstance(expr, int):
        return expr
    if isinstance(expr, str):
        return bindings.get(expr, expr)
    op, *operands = expr
    return make(
        op, *(substitute(operand, bindings, modulus) for operand in operands), modulus=modulus
    )


def expression(source: str, **bindings: Expr) -> Expr:
    """Parse ``source`` and substitute ``bindings``, such as a symbolic path's final state.

    Examples
    --------
    >>> from blockchainkit.contracts import expression
    >>> expression("after > before", after=("+", "before", "x"))
    ('>', ('+', 'before', 'x'), 'before')
    """
    return substitute(parse_expression(source), bindings)


def variables(expr: Expr) -> set[str]:
    """The variable names in ``expr``."""
    if isinstance(expr, int):
        return set()
    if isinstance(expr, str):
        return {expr}
    found: set[str] = set()
    for operand in expr[1:]:
        found |= variables(operand)
    return found


def constants(expr: Expr) -> set[int]:
    """The integer constants in ``expr``."""
    if isinstance(expr, int):
        return {expr}
    if isinstance(expr, str):
        return set()
    found: set[int] = set()
    for operand in expr[1:]:
        found |= constants(operand)
    return found


def to_source(expr: Expr) -> str:
    """Write ``expr`` back in Python syntax, with only the parentheses it needs.

    Examples
    --------
    >>> from blockchainkit.contracts import parse_expression, to_source
    >>> to_source(parse_expression("(a - b) - (c - d)"))
    'a - b - (c - d)'
    """
    return _source(expr, 0)


def _source(expr: Expr, parent: int) -> str:
    if isinstance(expr, int):
        return str(expr)
    if isinstance(expr, str):
        return expr
    op = expr[0]
    level = _PRECEDENCE[op]
    if op == "not":
        text = f"not {_source(expr[1], level)}"
    else:
        # Comparisons do not chain, and the right operand of a left-associative
        # operator needs parentheses at equal precedence.
        left_level = level + 1 if level == 4 else level
        text = f"{_source(expr[1], left_level)} {op} {_source(expr[2], level + 1)}"
    return f"({text})" if level < parent else text
