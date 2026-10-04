"""Step traces and per-opcode gas schedules."""

import pytest

from blockchainkit.vm import TraceStep, VMError, execute

INCREMENT = [("LOAD", 0), ("PUSH", 5), ("ADD", None), ("STORE", 0), ("STOP", None)]


def test_trace_records_state_after_every_executed_instruction():
    result = execute(INCREMENT, storage={0: 10}, trace=True)
    assert [step.opcode for step in result.trace] == ["LOAD", "PUSH", "ADD", "STORE", "STOP"]
    assert [step.stack for step in result.trace] == [(10,), (10, 5), (15,), (), ()]
    assert result.trace[3].storage == {0: 15}
    assert [step.gas_used for step in result.trace] == [1, 2, 3, 4, 5]
    assert [step.pc for step in result.trace] == [0, 1, 2, 3, 4]
    assert result.trace[1] == TraceStep(1, "PUSH", 5, (10, 5), {0: 10}, 2)


def test_trace_follows_jumps_that_prefix_replay_cannot():
    # Count down from 2: the loop body runs twice, so pc 2..5 appear twice.
    program = [
        ("PUSH", 2),
        ("STORE", 0),
        ("LOAD", 0),
        ("JZ", 9),
        ("LOAD", 0),
        ("PUSH", 1),
        ("SUB", None),
        ("STORE", 0),
        ("JMP", 2),
        ("STOP", None),
    ]
    result = execute(program, trace=True)
    pcs = [step.pc for step in result.trace]
    assert pcs.count(3) == 3 and pcs[-1] == 9
    assert result.storage == {0: 0}


def test_trace_is_empty_unless_requested():
    assert execute(INCREMENT).trace == ()


def test_a_failed_execution_carries_its_partial_trace():
    with pytest.raises(VMError, match="out of gas") as caught:
        execute([("JMP", 0)], gas_limit=3, trace=True)
    assert [step.pc for step in caught.value.trace] == [0, 0, 0]
    with pytest.raises(VMError) as caught:
        execute([("JMP", 0)], gas_limit=3)
    assert caught.value.trace == ()


def test_gas_schedule_prices_opcodes_individually():
    costs = {"STORE": 20, "LOAD": 5}
    result = execute(INCREMENT, storage={0: 1}, gas_costs=costs)
    assert result.gas_used == 5 + 1 + 1 + 20 + 1
    with pytest.raises(VMError, match="out of gas"):
        execute(INCREMENT, storage={0: 1}, gas_costs=costs, gas_limit=26)
    assert execute(INCREMENT, storage={0: 1}, gas_costs=costs, gas_limit=28).storage[0] == 6


@pytest.mark.parametrize(
    "costs,error", [({"NOPE": 1}, VMError), ({"JMP": 0}, ValueError), ({"ADD": 1.5}, TypeError)]
)
def test_gas_schedule_is_validated(costs, error):
    with pytest.raises(error):
        execute(INCREMENT, gas_costs=costs)
