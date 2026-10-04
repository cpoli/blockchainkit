"""A two-pass assembler: write programs as text, with labels for jump targets.

Each line holds one instruction, an opcode with an optional operand, or a
label ending in ``:``. ``#`` starts a comment. A jump may name a label
instead of an address; the first pass records where each label points, the
second replaces label names by those addresses.

Example::

    # Sum 1 + 2 + ... + n, with n in slot 0 and the sum in slot 1.
    loop:
        LOAD 0
        JZ done
        LOAD 1
        LOAD 0
        ADD
        STORE 1
        LOAD 0
        PUSH 1
        SUB
        STORE 0
        JMP loop
    done:
        STOP
"""

from blockchainkit.vm.core.base import Instruction, VMError
from blockchainkit.vm.systems.stack_machine import OPERAND_OPCODES, validate_program


def assemble(source: str) -> tuple[Instruction, ...]:
    """Translate assembly text into ``(opcode, operand)`` instructions.

    Operands are decimal or ``0x`` hexadecimal integers, or labels for
    ``JMP`` and ``JZ``.

    Examples
    --------
    >>> from blockchainkit.vm import assemble
    >>> assemble('''
    ... start:
    ...     PUSH 0x10   # sixteen
    ...     JZ start
    ... ''')
    (('PUSH', 16), ('JZ', 0))
    """
    if not isinstance(source, str):
        raise TypeError("source must be a str")
    labels: dict[str, int] = {}
    lines: list[tuple[int, list[str]]] = []
    for number, raw in enumerate(source.splitlines(), start=1):
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        if text.endswith(":"):
            name = text[:-1].strip()
            if not name.isidentifier() or name in labels:
                raise VMError(f"line {number}: bad or repeated label {name!r}")
            labels[name] = len(lines)
            continue
        lines.append((number, text.split()))
    program: list[Instruction] = []
    for number, words in lines:
        op = words[0].upper()
        if len(words) > 2:
            raise VMError(f"line {number}: one operand at most")
        if len(words) == 1:
            program.append((op, None))
            continue
        word = words[1]
        if op in {"JMP", "JZ"} and word in labels:
            program.append((op, labels[word]))
        elif op in OPERAND_OPCODES:
            try:
                program.append((op, int(word, 0)))
            except ValueError:
                raise VMError(f"line {number}: unknown label or number {word!r}") from None
        else:
            raise VMError(f"line {number}: {op} takes no operand")
    return validate_program(program)
