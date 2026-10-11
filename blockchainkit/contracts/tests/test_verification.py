"""Verification tools: expressions, Hoare triples, symbolic execution and fuzzing."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk
from blockchainkit.constants import WORD_MODULUS
from blockchainkit.contracts import (
    ERC20,
    Contract,
    FuzzCall,
    boundary_values,
    check_triple,
    evaluate,
    expression,
    fuzz,
    parse_expression,
    parse_program,
    run_program,
    shrink,
    solve,
    substitute,
    symbolic_bytecode,
    symbolic_execute,
    to_source,
    weakest_precondition,
)
from blockchainkit.contracts.utils.expressions import constants, make, variables

WITHDRAW = """
require(amount <= balance)
if amount > 100:
    fee = 2
else:
    fee = 1
balance = balance - amount - fee
assert balance >= 0
"""


# Expressions ----------------------------------------------------------------


def test_parsing_and_printing_round_trip():
    for source in [
        "a - b - (c - d)",
        "a * (b + c) // 2 % 7",
        "not a < b or c == d and e != 1",
        "(a <= b) == (c >= d)",
        "x > 0 and y > 0 and z > 0",
    ]:
        expr = parse_expression(source)
        assert parse_expression(to_source(expr)) == expr
    assert to_source(parse_expression("not (a or b)")) == "not (a or b)"
    assert parse_expression("True") == 1 and parse_expression("x / 2") == ("//", "x", 2)


def test_evaluation_follows_evm_conventions():
    assert evaluate(parse_expression("7 // 0 + 7 % 0"), {}) == 0
    assert evaluate(parse_expression("0 - 1"), {}, WORD_MODULUS) == WORD_MODULUS - 1
    assert evaluate(parse_expression("0 - 1"), {}) == -1
    assert evaluate(parse_expression("not 0 and (1 or 0)"), {}) == 1
    with pytest.raises(KeyError):
        evaluate("x", {})
    with pytest.raises(ValueError, match="unknown operator"):
        evaluate(("^", 1, 2), {})


def test_folding_and_helpers():
    assert make("+", 2, 3) == 5 and make("not", ("not", "x")) == "x"
    assert make("not", "x") == ("not", "x")
    assert substitute(parse_expression("x + y"), {"x": 1, "y": 2}) == 3
    assert expression("a > b", a=("+", "b", 1)) == (">", ("+", "b", 1), "b")
    assert variables(parse_expression("x + y * 2")) == {"x", "y"}
    assert constants(parse_expression("x + y * 2 - 7")) == {2, 7}


@pytest.mark.parametrize(
    "source", ["x ** 2", "f(x)", "a < b < c", "x if y else z", "'text'", "-x", "1.5"]
)
def test_unsupported_expressions(source):
    with pytest.raises(ValueError):
        parse_expression(source)


def test_program_parsing():
    program = parse_program(WITHDRAW)
    assert [statement[0] for statement in program] == ["require", "if", "assign", "assert"]
    with pytest.raises(ValueError):
        parse_program("while x:\n    x = x - 1")
    with pytest.raises(ValueError):
        parse_program("a, b = 1, 2")
    with pytest.raises(ValueError):
        parse_program("if x:\n  y = (")
    with pytest.raises(ValueError):
        parse_expression("(")
    with pytest.raises(TypeError):
        parse_program(1)
    with pytest.raises(TypeError):
        parse_expression(1)
    assert parse_program("") == ()


# Floyd-Hoare ----------------------------------------------------------------


def test_weakest_precondition_rules():
    assert to_source(weakest_precondition("x = x + 1", "x > 0")) == "x + 1 > 0"
    assert to_source(weakest_precondition("require(x > 0)", "x > 0")) == "not x > 0 or x > 0"
    assert to_source(weakest_precondition("assert x > 0", "y > 0")) == "x > 0 and y > 0"
    assert weakest_precondition("x = 1", "x == 1") == 1
    assert weakest_precondition("x = 1", "x == 2") == 0
    assert weakest_precondition("assert x > 0\nx = 1", "x == 2") == 0
    assert weakest_precondition("require(x > 0)\nx = 1", "x == 1") == 1
    assert weakest_precondition("assert 1", "y > 0") == (">", "y", 0)
    assert weakest_precondition("require(1)", "y > 0") == (">", "y", 0)
    branchy = "if c > 0:\n    x = 1\nelse:\n    x = 2"
    assert to_source(weakest_precondition(branchy, "x == 1")) == "c > 0"


def test_triples_on_the_withdraw_program():
    domain = {"balance": range(0, 120, 7), "amount": range(0, 120, 7)}
    result = check_triple("balance >= 0", WITHDRAW, "balance >= 0", domain)
    assert not result.holds and result.counterexample is not None
    assert run_program(WITHDRAW, result.counterexample)[0] == "assertion"
    fixed = WITHDRAW.replace("amount <= balance", "amount + 2 <= balance")
    assert check_triple("balance >= 0", fixed, "balance >= 0", domain).holds
    assert check_triple("balance < 0", WITHDRAW, "1 == 0", domain).checked == 0
    with pytest.raises(ValueError, match="no values for"):
        check_triple("x > 0", "y = x", "y > 0", {"z": [1]})


def test_wrapping_breaks_a_triple():
    program = "require(amount <= balance)\nbalance = balance - amount\nreceived = received + amount"
    post = "received >= amount"
    domain = {name: range(4) for name in ("balance", "amount", "received")}
    assert check_triple("1", program, post, domain).holds
    wrapped = check_triple("1", program, post, domain, modulus=4)
    assert not wrapped.holds


@given(st.integers(0, 30), st.integers(0, 30), st.integers(0, 30), st.sampled_from([None, 16]))
def test_wp_agrees_with_running_the_program(balance, amount, total, modulus):
    if modulus:
        balance, amount, total = balance % modulus, amount % modulus, total % modulus
    env = {"balance": balance, "amount": amount, "total": total}
    post = "balance + fee <= total"
    wp = weakest_precondition(WITHDRAW, post, modulus=modulus)
    outcome, final = run_program(WITHDRAW, env, modulus=modulus)
    expected = outcome == "reverted" or (
        outcome == "ok" and evaluate(parse_expression(post), final, modulus)
    )
    assert bool(evaluate(wp, env, modulus)) == expected


# Symbolic execution ---------------------------------------------------------


def test_symbolic_execution_finds_the_assertion_failure():
    result = symbolic_execute(WITHDRAW)
    assert result.outcomes == {"reverted": 1, "assertion": 2, "ok": 2}
    assert result.variables == ("amount", "balance") and result.complete
    failures = [path for path in result.paths if path.outcome == "assertion"]
    witness = solve(failures[0].conditions)
    assert witness is not None
    assert run_program(WITHDRAW, witness)[0] == "assertion"


def test_constant_branches_do_not_fork():
    result = symbolic_execute("x = 1\nif x > 0:\n    y = 1\nelse:\n    y = 2\nrequire(x == 1)")
    assert result.outcomes == {"ok": 1} and result.paths[0].state == {"x": 1, "y": 1}
    assert symbolic_execute("require(0)").outcomes == {"reverted": 1}
    assert symbolic_execute("if 0:\n    y = 1\nelse:\n    y = 2").paths[0].state == {"y": 2}


@given(st.integers(0, 300), st.integers(0, 300))
def test_path_conditions_partition_the_inputs(amount, balance):
    env = {"amount": amount, "balance": balance}
    matching = [
        path
        for path in symbolic_execute(WITHDRAW).paths
        if all(evaluate(condition, env) for condition in path.conditions)
    ]
    assert len(matching) == 1
    assert matching[0].outcome == run_program(WITHDRAW, env)[0]


def test_solver_options():
    conditions = [parse_expression("x * y == 12"), parse_expression("x < y")]
    assert solve(conditions, candidates=range(1, 13)) == {"x": 1, "y": 12}
    assert solve(conditions, candidates={"x": [3], "y": [4, 5]}) == {"x": 3, "y": 4}
    assert solve([parse_expression("x > 5")], candidates=[1, 2]) is None
    with pytest.raises(ValueError, match="exceed"):
        solve(conditions, candidates=range(100), max_assignments=50)
    assert boundary_values([], modulus=8) == (0, 1, 2, 3, 4, 5, 7)


def test_symbolic_bytecode_finds_the_beautychain_overflow():
    bug = "slot1 >= s1 and slot2 > s2"
    found = []
    for checked in (False, True):
        result = symbolic_bytecode(
            bk.vm.batch_transfer(1, [2, 3], checked=checked), arguments=("value",)
        )
        assert result.complete and "value" in result.variables
        witnesses = [
            solve((*path.conditions, expression(bug, **path.state)), modulus=WORD_MODULUS)
            for path in result.paths
            if path.outcome == "stop"
        ]
        found.append([w for w in witnesses if w is not None])
    assert found[0] and found[0][0]["value"] == 2**255 and not found[1]
    value = found[0][0]["value"]
    storage = {1: found[0][0]["s1"], 2: found[0][0]["s2"]}
    run = bk.vm.execute(bk.vm.batch_transfer(1, [2, 3]), arguments=(value,), storage=storage)
    assert run.storage[2] == 2**255  # Tokens from nothing, confirmed concretely.


def test_symbolic_bytecode_edge_cases():
    division = [("DIV", None), ("STOP", None)]
    result = symbolic_bytecode(division, arguments=("a", "b"))
    assert sorted(path.outcome for path in result.paths) == ["error", "stop"]
    assert symbolic_bytecode([("PUSH", 0), ("PUSH", 0), ("DIV", None)]).outcomes == {"error": 1}
    assert symbolic_bytecode([("PUSH", 4), ("PUSH", 2), ("DIV", None)]).outcomes == {"stop": 1}
    assert symbolic_bytecode([("ADD", None)]).outcomes == {"error": 1}
    loop = symbolic_bytecode([("JMP", 0)], max_steps=10)
    assert loop.outcomes == {"bound": 1} and not loop.complete
    concrete = [("PUSH", 0), ("JZ", 3), ("REVERT", None), ("PUSH", 1), ("JZ", 0), ("STOP", None)]
    assert symbolic_bytecode(concrete).outcomes == {"stop": 1}
    words = [
        ("DUP", None),
        ("OVER", None),
        ("SWAP", None),
        ("ROT", None),
        ("DROP", None),
        ("STORE", 5),
        ("LOAD", 6),
        ("STORE", 7),
        ("PUSH", 1),
        ("JMP", 10),
        ("STOP", None),
    ]
    final = symbolic_bytecode(words, arguments=("a",)).paths[0].state
    assert final == {"slot5": "a", "slot6": "s6", "slot7": "s6"}
    branching = [("DUP", None), ("JZ", 3), ("DROP", None), ("STOP", None)]
    assert len(symbolic_bytecode(branching, arguments=("x",), max_paths=1).paths) == 1
    assert not symbolic_bytecode(branching, arguments=("x",), max_paths=1).complete
    with pytest.raises(ValueError, match="identifiers"):
        symbolic_bytecode([], arguments=("not valid",))


# Fuzzing --------------------------------------------------------------------


class CachedToken(Contract):
    """Reads both balances before writing either: a self-transfer creates tokens."""

    layout = ("supply", "balances")

    def constructor(self, supply):
        self.write("supply", supply)
        self.write("balances", self.sender, supply)

    def transfer(self, to, amount):
        source, target = self.read("balances", self.sender), self.read("balances", to)
        self.require(source >= amount, "insufficient balance")
        self.write("balances", self.sender, source - amount)
        self.write("balances", to, target + amount)

    def total(self):
        return sum(self.entries("balances").values())


def _setup(world):
    return world.deploy("alice", CachedToken, 100)


def _conserved(world, token):
    return world.view(token, "total") == world.read(token, "supply")


def test_fuzzing_finds_and_shrinks_the_self_transfer_bug():
    functions = {"transfer": [["alice", "bob", "carol"], [0, 1, 10, 50]]}
    result = fuzz(_setup, functions, _conserved, senders=["alice", "bob", "carol"], seed=1)
    assert result.failed and len(result.sequence) == 1
    (call,) = result.sequence
    assert call.sender == call.args[0] and call.args[1] > 0
    assert result.original_length >= 1 and result.found_after <= result.transactions


def test_fuzzing_a_correct_token_finds_nothing():
    def setup(world):
        return world.deploy("alice", ERC20, 100)

    def conserved(world, token):
        return world.view(token, "total_supply") == 100

    functions = {"transfer": [["alice", "bob"], [0, 30, 200]], "approve": [["bob"], [5]]}
    result = fuzz(setup, functions, conserved, senders=["alice", "bob"], runs=10, depth=5)
    assert not result.failed and result.transactions == 50 and result.found_after is None


def test_shrinking_and_argument_checks():
    noise = FuzzCall("bob", "transfer", ("alice", 0))
    bug = FuzzCall("alice", "transfer", ("alice", 10))
    assert shrink(_setup, [noise, bug, noise], _conserved) == (bug,)
    with pytest.raises(ValueError, match="function"):
        fuzz(_setup, {}, _conserved, senders=["a"])
    with pytest.raises(ValueError, match="sender"):
        fuzz(_setup, {"transfer": [["a"], [1]]}, _conserved, senders=[])
    with pytest.raises(TypeError):
        fuzz(_setup, {"transfer": [["a"], [1]]}, _conserved, senders=["a"], seed=1.0)
