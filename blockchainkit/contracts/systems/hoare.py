"""Floyd-Hoare logic: proving a program correct with assertions (1967-1969).

Floyd attached assertions to the edges of a flowchart; Hoare turned them into
triples ``{P} S {Q}``: if P holds before S runs and S finishes, Q holds after.
The assignment axiom ``{Q[e/x]} x = e {Q}`` lets a postcondition be pushed
backwards through code. Dijkstra (1975) named the result the *weakest
precondition* ``wp(S, Q)``, and proving the triple reduces to showing that P
implies it.

Programs here are straight-line code with branches (see
:mod:`blockchainkit.contracts.utils.expressions`). ``require(c)`` reverts
when c is false, so a triple says nothing about states that revert;
``assert c`` must hold, as a Solidity ``assert`` must.
"""

import itertools
from collections.abc import Iterable, Mapping
from typing import Any

from blockchainkit.contracts.core.base import Expr, TripleResult
from blockchainkit.contracts.utils.expressions import (
    Statement,
    evaluate,
    make,
    parse_expression,
    parse_program,
    substitute,
)

_BOOLEAN = frozenset({"==", "!=", "<", "<=", ">", ">=", "and", "or", "not"})


def _program(program: str | Iterable[Statement]) -> tuple[Statement, ...]:
    return parse_program(program) if isinstance(program, str) else tuple(program)


def _condition(condition: str | Expr) -> Expr:
    return parse_expression(condition) if isinstance(condition, str) else condition


def _boolean(expr: Expr) -> bool:
    return isinstance(expr, tuple) and expr[0] in _BOOLEAN


def _and(left: Expr, right: Expr) -> Expr:
    if left == 0 or right == 0:
        return 0
    if left == 1 and _boolean(right):
        return right
    if right == 1 and _boolean(left):
        return left
    return make("and", left, right)


def _or(left: Expr, right: Expr) -> Expr:
    if left == 1 or right == 1:
        return 1
    if left == 0 and _boolean(right):
        return right
    if right == 0 and _boolean(left):
        return left
    return make("or", left, right)


def _not(expr: Expr) -> Expr:
    return make("not", expr)


def _wp(statements: tuple[Statement, ...], post: Expr, modulus: int | None) -> Expr:
    for statement in reversed(statements):
        kind = statement[0]
        if kind == "assign":
            post = substitute(post, {statement[1]: statement[2]}, modulus)
        elif kind == "require":
            post = _or(_not(statement[1]), post)
        elif kind == "assert":
            post = _and(statement[1], post)
        else:
            condition = statement[1]
            post = _or(
                _and(condition, _wp(statement[2], post, modulus)),
                _and(_not(condition), _wp(statement[3], post, modulus)),
            )
    return post


def weakest_precondition(
    program: str | Iterable[Statement], postcondition: str | Expr, *, modulus: int | None = None
) -> Expr:
    """The weakest condition on the inputs under which ``program`` establishes ``postcondition``.

    Assignments substitute (``wp(x = e, Q) = Q[e/x]``), ``require(c)`` adds
    ``not c or ...`` (a revert proves nothing), ``assert c`` adds ``c and ...``,
    and a branch takes both sides under their conditions.

    Parameters
    ----------
    program : str or iterable of Statement
        Source text, or statements from
        :func:`~blockchainkit.contracts.utils.expressions.parse_program`.
    postcondition : str or Expr
        What must hold afterwards.
    modulus : int, optional
        Word size, for wrapping arithmetic such as ``2**256``.

    Examples
    --------
    >>> from blockchainkit.contracts import to_source, weakest_precondition
    >>> to_source(weakest_precondition("balance = balance - amount", "balance >= 0"))
    'balance - amount >= 0'
    """
    return _wp(_program(program), _condition(postcondition), modulus)


def run_program(
    program: str | Iterable[Statement], env: Mapping[str, int], *, modulus: int | None = None
) -> tuple[str, dict[str, int]]:
    """Run a program on concrete values.

    Returns
    -------
    tuple
        ``(outcome, variables)``: the outcome is ``"ok"``, ``"reverted"`` (a
        ``require`` failed) or ``"assertion"`` (an ``assert`` failed); the
        variables are their values when the program stopped.
    """
    state = dict(env)
    pending = list(reversed(_program(program)))
    while pending:
        statement = pending.pop()
        kind = statement[0]
        if kind == "assign":
            state[statement[1]] = evaluate(statement[2], state, modulus)
        elif kind in ("require", "assert"):
            if not evaluate(statement[1], state, modulus):
                return ("reverted" if kind == "require" else "assertion"), state
        else:
            branch = statement[2] if evaluate(statement[1], state, modulus) else statement[3]
            pending.extend(reversed(branch))
    return "ok", state


def check_triple(
    precondition: str | Expr,
    program: str | Iterable[Statement],
    postcondition: str | Expr,
    domain: Mapping[str, Iterable[int]],
    *,
    modulus: int | None = None,
) -> TripleResult:
    """Check the Hoare triple ``{P} S {Q}`` on every combination of input values.

    A starting state that reverts satisfies the triple; one that fails an
    ``assert``, or finishes without Q, refutes it.

    Parameters
    ----------
    precondition, postcondition : str or Expr
        P and Q.
    program : str or iterable of Statement
        S.
    domain : mapping
        The values to try for each input variable.
    modulus : int, optional
        Word size for wrapping arithmetic.

    Examples
    --------
    >>> from blockchainkit.contracts import check_triple
    >>> program = "require(amount <= balance)\\nbalance = balance - amount"
    >>> check_triple("balance >= 0", program, "balance >= 0",
    ...              {"balance": range(5), "amount": range(5)}).holds
    True
    """
    pre, post, statements = _condition(precondition), _condition(postcondition), _program(program)
    names = sorted(domain)
    values: list[list[Any]] = [list(domain[name]) for name in names]
    checked = 0
    for combination in itertools.product(*values):
        env = dict(zip(names, combination, strict=True))
        if not _evaluate(pre, env, modulus):
            continue
        checked += 1
        outcome, final = run_program(statements, env, modulus=modulus)
        if outcome == "assertion" or (outcome == "ok" and not _evaluate(post, final, modulus)):
            return TripleResult(False, checked, env)
    return TripleResult(True, checked, None)


def _evaluate(expr: Expr, env: Mapping[str, int], modulus: int | None) -> int:
    try:
        return evaluate(expr, env, modulus)
    except KeyError as exc:
        raise ValueError(f"the domain gives no values for {exc.args[0]}") from None
