"""Validation and edge cases for the vm APIs added with the history page."""

import pytest

import blockchainkit as bk
from blockchainkit.crypto import public_key, sign

V = bk.vm


def test_arguments_and_new_opcodes_are_validated():
    with pytest.raises(V.VMError, match="argument"):
        V.execute([], arguments=(2**256,))
    with pytest.raises(V.VMError, match="stack limit"):
        V.execute([], arguments=(1, 2), stack_limit=1)
    with pytest.raises(V.VMError, match="underflow"):
        V.execute([("ROT", None)], arguments=(1, 2))
    with pytest.raises(V.VMError, match="reverted") as error:
        V.execute([("PUSH", 1), ("REVERT", None)], trace=True)
    assert len(error.value.trace) == 1


@pytest.mark.parametrize(
    "source,message",
    [
        ("x:\nx:\nSTOP", "repeated label"),
        ("1x:\nSTOP", "bad or repeated"),
        ("PUSH 1 2", "one operand"),
        ("JMP nowhere", "unknown label"),
        ("ADD 3", "takes no operand"),
        ("FLY", "unknown opcode"),
    ],
)
def test_assembler_errors(source, message):
    with pytest.raises(V.VMError, match=message):
        V.assemble(source)


def test_assembler_type_and_comments():
    with pytest.raises(TypeError):
        V.assemble(b"STOP")  # type: ignore[arg-type]
    assert V.assemble("# only a comment\n\n  stop  # lowercase works") == (("STOP", None),)


@pytest.mark.parametrize(
    "expression,message",
    [
        ("1 2", "two operands"),
        ("2 (3)", "missing operator"),
        ("()", "empty parentheses"),
        ("1)", "unbalanced"),
        ("(1", "unbalanced"),
        ("+ 1", "missing an operand"),
        ("1 +", "ends with an operator"),
        ("", "empty"),
        ("1 % 2", "unexpected character"),
    ],
)
def test_expression_errors(expression, message):
    with pytest.raises(V.VMError, match=message):
        V.to_rpn(expression)


def test_expression_type_and_word_size():
    with pytest.raises(TypeError):
        V.to_rpn(3)  # type: ignore[arg-type]
    with pytest.raises(V.VMError, match="256-bit"):
        V.compile_expression(str(2**256))


def test_verifier_edge_cases():
    assert V.verify_bytecode([]) == V.VerificationResult(0, ())
    with pytest.raises(ValueError):
        V.verify_bytecode([], arguments=-1)
    # Both branches of JZ meet at "end" with the same height: accepted once.
    branches = V.assemble("PUSH 0\nJZ end\nPUSH 1\nDROP\nend:\nSTOP")
    assert V.verify_bytecode(branches).ok
    clash = V.assemble("PUSH 0\nJZ end\nPUSH 1\nend:\nPUSH 2\nJMP end")
    assert len(V.verify_bytecode(clash).errors) == 1  # Reported once, not per visit.
    assert V.verify_bytecode(
        [("REVERT", None), ("ADD", None)]
    ).ok  # Unreachable code is not checked.


def test_turing_validation():
    with pytest.raises(ValueError, match="no rule"):
        V.run_turing_machine({})
    with pytest.raises(ValueError, match="write 0 or 1"):
        V.run_turing_machine({("A", 0): (2, 1, "H")})
    with pytest.raises(ValueError, match="at most"):
        next(V.enumerate_machines(8))
    assert V.busy_beaver(1, max_steps=5).counts == {"halted": 32, "looping": 0, "unknown": 32}


def test_script_failures():
    key = public_key(7)
    assert "unknown opcode" in V.verify_script(["OP_FLY"], []).error
    assert "OP_IF on an empty" in V.verify_script(["OP_IF"], []).error
    assert "without OP_IF" in V.verify_script(["OP_ELSE"], []).error
    assert "without OP_ENDIF" in V.verify_script(["OP_TRUE", "OP_IF"], []).error
    assert "needs 2" in V.verify_script(["OP_TRUE", "OP_EQUAL"], []).error
    assert "OP_VERIFY" in V.verify_script(["OP_FALSE", "OP_VERIFY"], []).error
    assert V.verify_script([], []).error == "the top of the stack is not true"
    assert V.verify_script([b"a", b"a", "OP_EQUAL"], []).valid
    assert V.verify_script([b"\x01", "OP_VERIFY", "OP_TRUE"], []).valid
    assert V.verify_script(
        [b"x", "OP_DUP", "OP_DROP", "OP_HASH256", "OP_DROP", "OP_TRUE"], []
    ).valid
    # Nested IF inside a skipped branch stays skipped, including its ELSE.
    nested = [
        "OP_FALSE",
        "OP_IF",
        "OP_TRUE",
        "OP_IF",
        "OP_RETURN",
        "OP_ELSE",
        "OP_RETURN",
        "OP_ENDIF",
        "OP_ENDIF",
        "OP_TRUE",
    ]
    assert V.verify_script(nested, []).valid
    # Malformed signatures and keys make CHECKSIG false rather than raising.
    garbage = V.verify_script([b"\x04" + b"\x00" * 96, V.encode_public_key(key), "OP_CHECKSIG"], [])
    assert not garbage.valid
    short = V.verify_script([V.encode_signature(sign(b"m", 7, nonce=2)), b"key", "OP_CHECKSIG"], [])
    assert not short.valid
    with pytest.raises(TypeError):
        V.verify_script([], [], message="text")  # type: ignore[arg-type]
    assert V.number(0) == b"" and V.number(256) == b"\x01\x00"
    with pytest.raises(ValueError, match="32-byte"):
        V.htlc_locking(b"short", key, key, 1)


def test_program_library_validation():
    with pytest.raises(ValueError, match="at least one"):
        V.batch_transfer(1, [])
    with pytest.raises(TypeError):
        V.batch_transfer(1, ["2"])  # type: ignore[list-item]
    with pytest.raises(ValueError):
        V.drain_bank(10, 0)
    assert V.drain_bank(10, 5, max_depth=1).withdrawn == 5
