"""Instruction semantics, deterministic branching, and atomic failure."""

import pytest

from blockchainkit.vm import VMError, execute


@pytest.mark.parametrize(
    "op,expected", [("ADD", 9), ("SUB", 5), ("MUL", 14), ("DIV", 3), ("EQ", 0), ("LT", 0)]
)
def test_binary_semantics(op, expected):
    result = execute([("PUSH", 7), ("PUSH", 2), (op, None)])
    assert result.stack == (expected,)
    assert result.gas_used == 3


def test_modular_arithmetic_stack_and_storage():
    assert execute([("PUSH", 0), ("PUSH", 1), ("SUB", None)]).stack == (2**256 - 1,)
    initial = {1: 12}
    program = [
        ("LOAD", 1),
        ("DUP", None),
        ("PUSH", 2),
        ("SWAP", None),
        ("DROP", None),
        ("ADD", None),
        ("STORE", 1),
        ("LOAD", 1),
        ("STOP", None),
    ]
    result = execute(program, storage=initial)
    assert result.stack == (14,) and result.storage[1] == 14
    assert initial == {1: 12}
    with pytest.raises(TypeError):
        result.storage[1] = 0
    assert execute([("LOAD", 99)]).stack == (0,)


def test_jumps_and_gas():
    program = [("PUSH", 0), ("JZ", 3), ("PUSH", 99), ("PUSH", 7)]
    assert execute(program).stack == (7,)
    assert execute([("PUSH", 1), *program[1:]]).stack == (99, 7)
    assert execute([("JMP", 2), ("PUSH", 1), ("PUSH", 2)]).stack == (2,)
    assert execute([], gas_limit=0).gas_used == 0
    with pytest.raises(VMError, match="out of gas"):
        execute([("JMP", 0)], gas_limit=10)
    with pytest.raises(VMError, match="stack limit"):
        execute([("PUSH", 1), ("DUP", None)], stack_limit=1)


@pytest.mark.parametrize(
    "program",
    [
        [("BAD", None)],
        [("ADD", None)],
        [("PUSH", None)],
        [("PUSH", -1)],
        [("PUSH", True)],
        [("PUSH", 2**256)],
        [("JMP", 1)],
        [("STOP", 1)],
        [("PUSH", 1), ("PUSH", 0), ("DIV", None)],
        ["PUSH"],
    ],
)
def test_malformed_programs(program):
    with pytest.raises(VMError):
        execute(program)


def test_failed_execution_does_not_commit_storage():
    initial = {0: 5}
    with pytest.raises(VMError):
        execute([("PUSH", 99), ("STORE", 0), ("PUSH", 1)], storage=initial, gas_limit=2)
    assert initial == {0: 5}
    for state in ({True: 1}, {1: -1}, {2**256: 0}):
        with pytest.raises(VMError):
            execute([], storage=state)


@pytest.mark.parametrize("opcode", [["PUSH"], None, 7])
def test_non_string_opcodes_raise_vm_error(opcode):
    with pytest.raises(VMError, match="opcode"):
        execute([(opcode, 1)])
