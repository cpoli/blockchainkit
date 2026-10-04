"""APIs behind the execution history: RPN, Turing machines and busy beavers,
Forth stack words, assembly, verification, Script, contracts, and attacks."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk
from blockchainkit.crypto import public_key, sha256, sign

V = bk.vm


# Reverse Polish notation ----------------------------------------------------

expressions = st.recursive(
    st.integers(0, 10**6).map(str),
    lambda inner: st.tuples(inner, st.sampled_from("+-*"), inner).map(
        lambda t: f"({t[0]} {t[1]} {t[2]})"
    ),
    max_leaves=12,
)


@given(expressions)
def test_compiled_expressions_agree_with_python_modulo_the_word(expression):
    assert V.execute(V.compile_expression(expression)).stack == (eval(expression) % 2**256,)


def test_shunting_yard_respects_precedence_and_associativity():
    assert V.to_rpn("1 - 2 - 3") == ("1", "2", "-", "3", "-")  # Left associative.
    assert V.to_rpn("1 + 2 * 3") == ("1", "2", "3", "*", "+")
    assert V.to_rpn("8 / (4 / 2)") == ("8", "4", "2", "/", "/")
    assert V.execute(V.compile_expression("7 / 2")).stack == (3,)


# Turing machines and the busy beaver ----------------------------------------


def test_busy_beaver_two_states_matches_rado():
    result = V.busy_beaver(2, max_steps=50)
    assert (result.steps, result.ones) == (6, 4)  # S(2) = 6, Sigma(2) = 4.
    assert V.run_turing_machine(result.machine).steps == 6
    assert sum(result.counts.values()) == 12**4
    assert result.counts["looping"] > 0 and result.counts["unknown"] > 0


def test_three_state_champions():
    # S(3) = 21 (Lin and Rado 1965): the longest-running 3-state machine.
    longest = {
        ("A", 0): (1, 1, "B"),
        ("A", 1): (0, -1, "H"),
        ("B", 0): (1, -1, "B"),
        ("B", 1): (0, 1, "C"),
        ("C", 0): (1, -1, "C"),
        ("C", 1): (1, -1, "A"),
    }
    assert V.run_turing_machine(longest).steps == 21
    # Sigma(3) = 6: the most 1s, written by a different machine in 14 steps.
    most_ones = {
        ("A", 0): (1, 1, "B"),
        ("A", 1): (1, 1, "H"),
        ("B", 0): (0, 1, "C"),
        ("B", 1): (1, 1, "B"),
        ("C", 0): (1, -1, "C"),
        ("C", 1): (1, -1, "A"),
    }
    run = V.run_turing_machine(most_ones)
    assert (run.outcome, run.steps, run.ones) == ("halted", 14, 6)


def test_turing_outcomes():
    loop = {("A", 0): (0, 1, "A"), ("A", 1): (0, 1, "A")}
    assert V.run_turing_machine(loop, max_steps=50).outcome == "unknown"  # Runs off rightward.
    bounce = {
        ("A", 0): (0, 1, "B"),
        ("A", 1): (0, 1, "B"),
        ("B", 0): (0, -1, "A"),
        ("B", 1): (0, -1, "A"),
    }
    assert V.run_turing_machine(bounce).outcome == "looping"


# Forth stack words ------------------------------------------------------------


def test_over_and_rot_follow_their_stack_diagrams():
    assert V.execute([("OVER", None)], arguments=(1, 2)).stack == (1, 2, 1)
    assert V.execute([("ROT", None)], arguments=(1, 2, 3)).stack == (2, 3, 1)
    # x**2 + x with no variables: DUP DUP MUL SWAP... ( x -- x*x+x )
    square_plus = [("DUP", None), ("DUP", None), ("MUL", None), ("ADD", None)]
    assert V.execute(square_plus, arguments=(9,)).stack == (90,)


# Assembly and structured control flow ----------------------------------------

SUM = """
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


def test_assembled_loop_sums_one_to_n():
    program = V.assemble(SUM)
    assert program[-2] == ("JMP", 0) and program[1] == ("JZ", 11)
    assert V.execute(program, storage={0: 100}).storage[1] == 5050


# Bytecode verification -----------------------------------------------------------


def test_verifier_accepts_safe_loops_and_rejects_growing_ones():
    assert V.verify_bytecode(V.assemble(SUM)) == V.VerificationResult(2, ())
    growing = V.assemble("top:\n PUSH 1\n JMP top")
    result = V.verify_bytecode(growing)
    assert not result.ok and "heights 0 and 1" in result.errors[0]


def test_verifier_max_depth_bounds_every_run():
    program = V.compile_expression("1 + (2 + (3 + (4 + 5)))")
    bound = V.verify_bytecode(program).max_depth
    trace = V.execute(program, trace=True).trace
    assert bound == max(len(step.stack) for step in trace) == 5


def test_verifier_needs_the_declared_arguments():
    vending = V.vending_machine()
    assert not V.verify_bytecode(vending).ok
    assert V.verify_bytecode(vending, arguments=1).ok


# Bitcoin Script --------------------------------------------------------------------

MESSAGE = b"spend outpoint 0 to carol"


def test_p2pkh_spend():
    key = public_key(7)
    unlocking = V.p2pkh_unlocking(sign(MESSAGE, 7, nonce=11), key)
    result = V.verify_script(unlocking, V.p2pkh_locking(key), message=MESSAGE)
    assert result.valid and result.operations == 7
    other = public_key(8)
    wrong_key = V.p2pkh_unlocking(sign(MESSAGE, 8, nonce=11), other)
    assert "EQUALVERIFY" in V.verify_script(wrong_key, V.p2pkh_locking(key), message=MESSAGE).error
    assert not V.verify_script(unlocking, V.p2pkh_locking(key), message=b"another tx").valid


def test_htlc_claim_and_refund():
    alice, bob = public_key(7), public_key(5)
    preimage = b"payment preimage"
    lock = V.htlc_locking(sha256(preimage), bob, alice, timeout=500)
    claim = (V.encode_signature(sign(MESSAGE, 5, nonce=3)), preimage, "OP_TRUE")
    assert V.verify_script(claim, lock, message=MESSAGE).valid
    wrong = (V.encode_signature(sign(MESSAGE, 5, nonce=3)), b"guess", "OP_TRUE")
    assert not V.verify_script(wrong, lock, message=MESSAGE).valid
    refund = (V.encode_signature(sign(MESSAGE, 7, nonce=4)), "OP_FALSE")
    early = V.verify_script(refund, lock, message=MESSAGE, locktime=499)
    assert "lock time" in early.error
    assert V.verify_script(refund, lock, message=MESSAGE, locktime=500).valid


def test_separate_execution_closes_the_2010_op_return_bug():
    result = V.verify_script(["OP_TRUE", "OP_RETURN"], V.p2pkh_locking(public_key(7)))
    assert not result.valid and result.operations == 2


# Contracts and their failures ------------------------------------------------------


def test_vending_machine_enforces_its_terms():
    storage = {0: 2, 1: 3}
    sale = V.execute(V.vending_machine(), arguments=(5,), storage=storage)
    assert sale.stack == (2,) and dict(sale.storage) == {0: 1, 1: 3, 2: 3}
    with pytest.raises(V.VMError, match="reverted"):
        V.execute(V.vending_machine(), arguments=(2,), storage=storage)
    with pytest.raises(V.VMError, match="reverted"):
        V.execute(V.vending_machine(), arguments=(5,), storage={0: 0, 1: 3})


def test_batch_transfer_overflow_and_safemath():
    program = V.batch_transfer(1, [2, 3])
    minted = V.execute(program, arguments=(2**255,), storage={1: 0}).storage
    assert minted[2] == minted[3] == 2**255 and minted[1] == 0
    with pytest.raises(V.VMError, match="reverted"):
        V.execute(V.batch_transfer(1, [2, 3], checked=True), arguments=(2**255,), storage={1: 0})
    for checked in (False, True):
        normal = V.execute(
            V.batch_transfer(1, [2, 3], checked=checked), arguments=(10,), storage={1: 100}
        )
        assert dict(normal.storage) == {1: 80, 2: 10, 3: 10}
        with pytest.raises(V.VMError):
            V.execute(
                V.batch_transfer(1, [2, 3], checked=checked), arguments=(60,), storage={1: 100}
            )
        with pytest.raises(V.VMError):
            V.execute(V.batch_transfer(1, [2], checked=checked), arguments=(0,), storage={1: 100})


def test_reentrancy_drains_until_depth_or_funds_run_out():
    dao = V.drain_bank(1_000, 100)
    assert dao.withdrawn == 1_100 and dao.bank_balance == 0 and dao.stolen == 1_000
    deep = V.drain_bank(10**6, 100)
    assert deep.calls == 1024 and deep.withdrawn == 102_400
    safe = V.drain_bank(10**6, 100, checks_effects_interactions=True)
    assert safe.stolen == 0 and safe.calls == 2 and safe.bank_balance == 10**6
