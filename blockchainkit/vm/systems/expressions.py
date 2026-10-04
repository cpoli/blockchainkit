"""Reverse Polish notation (Łukasiewicz 1924; Hamblin 1957) and its compilation.

Łukasiewicz wrote logical formulas with the operator first, which needs no
parentheses: ``+ 1 * 2 3``. Hamblin saw that the reversed form,
``1 2 3 * +``, is exactly the order in which a stack machine computes: push
operands, and let each operator replace the top two values by its result.
Dijkstra's shunting-yard algorithm (1961) converts ordinary infix notation
to that order, which is how expressions become stack-machine code.
"""

import re

from blockchainkit.vm.core.base import Instruction, VMError
from blockchainkit.vm.systems.stack_machine import check_word

_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}
_OPCODES = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
_TOKEN = re.compile(r"\s*(?:(\d+)|(.))")


def to_rpn(expression: str) -> tuple[str, ...]:
    """Convert an infix expression to reverse Polish notation (shunting yard).

    Supports non-negative integers, ``+ - * /`` with the usual precedence
    and left associativity, and parentheses.

    Examples
    --------
    >>> from blockchainkit.vm import to_rpn
    >>> to_rpn("(1 + 2) * 3 - 4")
    ('1', '2', '+', '3', '*', '4', '-')
    """
    if not isinstance(expression, str):
        raise TypeError("expression must be a str")
    output: list[str] = []
    operators: list[str] = []
    expect_operand = True
    for number, symbol in _TOKEN.findall(expression.strip()):
        if number:
            if not expect_operand:
                raise VMError("two operands in a row")
            output.append(number)
            expect_operand = False
        elif symbol == "(":
            if not expect_operand:
                raise VMError("missing operator before '('")
            operators.append(symbol)
        elif symbol == ")":
            while operators and operators[-1] != "(":
                output.append(operators.pop())
            if not operators or expect_operand:
                raise VMError("unbalanced or empty parentheses")
            operators.pop()
        elif symbol in _PRECEDENCE:
            if expect_operand:
                raise VMError(f"operator {symbol!r} is missing an operand")
            while operators and _PRECEDENCE.get(operators[-1], 0) >= _PRECEDENCE[symbol]:
                output.append(operators.pop())
            operators.append(symbol)
            expect_operand = True
        else:
            raise VMError(f"unexpected character {symbol!r}")
    if expect_operand:
        raise VMError("the expression is empty or ends with an operator")
    while operators:
        if operators[-1] == "(":
            raise VMError("unbalanced parentheses")
        output.append(operators.pop())
    return tuple(output)


def compile_expression(expression: str) -> tuple[Instruction, ...]:
    """Compile an infix expression to stack-machine instructions via RPN.

    Each number becomes ``PUSH`` and each operator its opcode. Arithmetic is
    then the machine's: modulo ``2**256``, with ``/`` as floor division.

    Examples
    --------
    >>> from blockchainkit.vm import compile_expression, execute
    >>> execute(compile_expression("(1 + 2) * 3 - 4")).stack
    (5,)
    """
    program: list[Instruction] = []
    for token in to_rpn(expression):
        if token in _OPCODES:
            program.append((_OPCODES[token], None))
        else:
            check_word(int(token), "every number")
            program.append(("PUSH", int(token)))
    return tuple(program)
