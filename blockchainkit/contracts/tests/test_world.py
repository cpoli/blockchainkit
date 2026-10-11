"""The world-state model: dispatch, storage, gas, value, rollback, creation and depth."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import blockchainkit as bk
from blockchainkit.contracts import (
    Contract,
    ContractError,
    World,
    code_hash,
    create2_address,
    create_address,
)
from blockchainkit.contracts.systems.world import CALL_STIPEND, GAS_COSTS, MAX_CALL_DEPTH


class Store(Contract):
    layout = ("value", "table")

    def constructor(self, value=0):
        self.write("value", value)

    def get(self):
        return self.read("value")

    def set(self, value):
        self.write("value", value)

    def put(self, key, value):
        self.write("table", key, value)

    def table(self):
        return self.entries("table")

    def fail_after_set(self, value):
        self.write("value", value)
        self.emit("Set", value=value)
        self.require(False, "nope")

    def burn(self, amount):
        self.use_gas(amount)

    def crash(self):
        self.write("value", 99)
        raise RuntimeError("a bug, not a revert")


class Caller(Contract):
    layout = ("value",)

    def call_set(self, target, value):
        return self.call(target, "set", value)

    def try_then_continue(self, target, value):
        self.write("value", 1)
        try:
            self.call(target, "fail_after_set", value)
        except ContractError:
            return "caught"
        return "not reached"

    def delegate_set(self, target, value):
        return self.delegatecall(target, "set", value)

    def pay(self, to, amount):
        return self.send(to, amount)

    def call_with_gas(self, target, gas):
        return self.call(target, "burn", 10_000, gas=gas)

    def make(self, value, salt=None):
        return self.create(Store, value, salt=salt)

    def receive(self):
        pass


class Recursor(Contract):
    layout = ("depth",)

    def down(self, levels):
        if levels:
            self.call(self.address, "down", levels - 1)
        self.write("depth", self.read("depth") + 1)


class Fallback(Contract):
    layout = ("last",)

    def fallback(self, function, *args):
        self.write("last", function or "payment")
        return args


class Destroyer(Contract):
    layout = ()

    def receive(self):
        pass

    def destroy(self, beneficiary):
        self.selfdestruct(beneficiary)


class Guarded(Contract):
    layout = ("count",)

    def bump(self, amount):
        self.write("count", self.read("count") + amount)

    def invariant(self):
        return self.read("count") <= 10


class NoConstructor(Contract):
    layout = ()


class Context(Contract):
    layout = ()

    def info(self):
        return (self.sender, self.origin, self.value, self.block_number, self.timestamp)

    def gas(self):
        return self.gas_left

    def balances(self, account):
        return self.ether_balance(), self.ether_balance(account)

    def code_of(self, account):
        return self.code_at(account)

    def hash_of(self, number):
        return self.blockhash(number)

    def bad_write(self):
        self.write("missing", 1)

    def no_value(self):
        self.write("missing")


@pytest.fixture
def world():
    return World()


def test_deploy_transact_view_and_storage(world):
    store = world.deploy("alice", Store, 5, name="store")
    assert world.view(store, "get") == 5
    receipt = world.transact("bob", store, "set", 7)
    assert receipt.success and receipt.result is None and receipt.error is None
    assert receipt.gas_used == GAS_COSTS["transaction"] + GAS_COSTS["write"]
    assert world.read(store, "value") == 7 and world.storage(store) == {0: 7}
    assert world.name(store) == "store" and world.name("bob") == "bob"
    assert world.nonce("alice") == 1 and world.nonce("bob") == 1
    world.transact("bob", store, "set", 0)
    assert world.storage(store) == {}  # Writing zero clears the slot.
    world.transact("bob", store, "put", "k", 3)
    assert world.view(store, "table") == {"k": 3}
    assert world.read(store, "table", "k") == 3


def test_views_leave_no_trace(world):
    store = world.deploy("alice", Store, 1)
    with pytest.raises(ContractError, match="nope"):
        world.view(store, "fail_after_set", 3)
    assert world.view(store, "get") == 1


def test_a_fork_is_independent_of_its_world(world):
    store = world.deploy("alice", Store, 1, name="store")
    world.fund("alice", 10)
    trial = world.fork()
    trial.transact("bob", store, "set", 9)
    trial.transact("alice", "bob", value=4)
    trial.deploy("carol", Store, 2, name="other")
    assert world.view(store, "get") == 1 and trial.view(store, "get") == 9
    assert world.balance("bob") == 0 and trial.balance("bob") == 4
    assert world.nonce("bob") == 0 and trial.nonce("bob") == 1
    assert world.code(create_address("carol", 0)) is None
    assert trial.name(store) == "store" and trial.seed == world.seed


def test_revert_undoes_state_and_events_but_keeps_the_record(world):
    store = world.deploy("alice", Store, 1)
    receipt = world.transact("bob", store, "fail_after_set", 9)
    assert not receipt.success and receipt.error == "nope" and receipt.events == ()
    assert world.view(store, "get") == 1
    assert [call.ok for call in receipt.calls] == [False]


def test_a_caught_sub_call_revert_undoes_only_the_sub_call(world):
    store = world.deploy("alice", Store, 1)
    caller = world.deploy("alice", Caller)
    receipt = world.transact("bob", caller, "try_then_continue", store, 9)
    assert receipt.success and receipt.result == "caught"
    assert world.view(store, "get") == 1 and world.read(caller, "value") == 1
    assert [call.ok for call in receipt.calls] == [True, False]
    assert receipt.calls[1].depth == 1 and receipt.calls[1].sender == caller


def test_python_exceptions_restore_state_and_propagate(world):
    store = world.deploy("alice", Store, 1)
    with pytest.raises(RuntimeError):
        world.transact("bob", store, "crash")
    assert world.view(store, "get") == 1


def test_calls_set_the_sender_and_delegatecall_uses_the_callers_storage(world):
    store = world.deploy("alice", Store, 1)
    caller = world.deploy("alice", Caller)
    receipt = world.transact("bob", caller, "call_set", store, 4)
    assert receipt.success and world.view(store, "get") == 4
    receipt = world.transact("bob", caller, "delegate_set", store, 8)
    assert world.view(store, "get") == 4 and world.read(caller, "value") == 8
    delegated = receipt.calls[1]
    assert (delegated.kind, delegated.to, delegated.context, delegated.sender) == (
        "delegatecall",
        store,
        caller,
        "bob",
    )
    # Delegating to an account without code runs nothing and succeeds.
    assert world.transact("bob", caller, "delegate_set", "nobody", 3).success
    assert world.read(caller, "value") == 8


def test_context_properties(world):
    world.fund("alice", 50)
    context = world.deploy("alice", Context)
    world.advance(blocks=2, seconds=30)
    receipt = world.transact("alice", context, "info", value=5)
    assert receipt.result == ("alice", "alice", 5, 3, 30)
    assert world.view(context, "balances", "alice") == (5, 45)
    assert world.view(context, "code_of", context) is Context
    assert world.view(context, "code_of", "alice") is None
    assert world.view(context, "hash_of", 2) == world.blockhash(2) != 0
    gas = world.transact("alice", context, "gas").result
    assert gas == world.block_gas_limit - GAS_COSTS["transaction"]
    with pytest.raises(KeyError, match="missing"):
        world.transact("alice", context, "bad_write")


def test_dispatch_rules(world):
    store = world.deploy("alice", Store)
    assert world.transact("bob", store, "nothing").error == "Store has no function 'nothing'"
    assert world.transact("bob", store, "_slot").error == "Store has no function '_slot'"
    assert world.transact("bob", store, "read", "value").error == "Store has no function 'read'"
    assert (
        world.transact("bob", store, "constructor").error == "Store has no function 'constructor'"
    )
    world.fund("bob", 5)
    assert world.transact("bob", store, value=1).error == "Store does not accept payments"
    assert world.transact("bob", "nobody", "get").error == "no contract at nobody"
    assert world.transact("bob", "nobody", value=2).success  # A payment to an account.
    assert world.balance("nobody") == 2
    fallback = world.deploy("alice", Fallback)
    assert world.transact("bob", fallback, "anything", 1, 2).result == (1, 2)
    assert world.read(fallback, "last") == "anything"
    assert world.transact("bob", fallback, value=1).result == ()
    assert world.read(fallback, "last") == "payment"
    with pytest.raises(TypeError, match="no constructor"):
        world.deploy("alice", NoConstructor, 1)


def test_value_transfers(world):
    world.fund("alice", 100)
    caller = world.deploy("alice", Caller, value=40)
    assert world.balance(caller) == 40 and world.balance("alice") == 60
    receipt = world.transact("alice", caller, value=1_000)
    assert receipt.error == "insufficient balance" and world.balance("alice") == 60
    assert world.transact("bob", caller, "pay", "carol", 15).result is True
    assert world.balance("carol") == 15
    assert world.transact("bob", caller, "pay", "carol", 1_000).result is False


def test_send_gives_only_the_stipend(world):
    world.fund("alice", 100)
    caller = world.deploy("alice", Caller, value=50)
    store = world.deploy("alice", Fallback)  # Its fallback writes storage: too costly.
    assert GAS_COSTS["write"] > CALL_STIPEND
    receipt = world.transact("bob", caller, "pay", store, 10)
    assert receipt.result is False and world.balance(store) == 0
    assert receipt.calls[1].error == "out of gas"


def test_gas_limits(world):
    store = world.deploy("alice", Store)
    receipt = world.transact("bob", store, "burn", 10_000, gas=25_000)
    assert receipt.error == "out of gas" and receipt.gas_used == 25_000
    caller = world.deploy("alice", Caller)
    receipt = world.transact("bob", caller, "call_with_gas", store, 5_000)
    assert receipt.error == "out of gas" and receipt.calls[1].gas_used == 5_000
    assert world.transact("bob", caller, "call_with_gas", store, 50_000).success
    with pytest.raises(ValueError, match="block gas limit"):
        world.transact("bob", store, "get", gas=world.block_gas_limit + 1)
    with pytest.raises(ValueError):
        world.transact("bob", store, "get", gas=100)


def test_the_call_depth_limit():
    world = World(max_call_depth=20)
    recursor = world.deploy("alice", Recursor)
    assert world.transact("bob", recursor, "down", 20).success
    assert world.read(recursor, "depth") == 21
    receipt = world.transact("bob", recursor, "down", 21)
    assert receipt.error == "call depth limit reached" and world.read(recursor, "depth") == 21
    deep = World()
    recursor = deep.deploy("alice", Recursor)
    assert deep.transact("bob", recursor, "down", MAX_CALL_DEPTH).success


def test_invariants_are_checked_after_every_call(world):
    guarded = world.deploy("alice", Guarded)
    assert world.transact("bob", guarded, "bump", 10).success
    receipt = world.transact("bob", guarded, "bump", 1)
    assert receipt.error == "invariant of Guarded violated"
    assert world.read(guarded, "count") == 10


def test_selfdestruct_removes_code_and_storage(world):
    world.fund("alice", 10)
    destroyer = world.deploy("alice", Destroyer, value=10)
    assert world.transact("bob", destroyer, "destroy", "carol").success
    assert world.code(destroyer) is None and world.balance("carol") == 10
    world.fund("alice", 5)
    again = world.deploy("alice", Destroyer, value=5)
    world.transact("bob", again, "destroy", again)  # Burned: sent to itself.
    assert world.balance(again) == 0


def test_create_and_create2_addresses(world):
    caller = world.deploy("alice", Caller)
    assert caller == create_address("alice", 0)
    child = world.transact("bob", caller, "make", 3).result
    assert child == create_address(caller, 0) and world.view(child, "get") == 3
    salted = world.transact("bob", caller, "make", 4, 7).result
    assert salted == create2_address(caller, 7, Store, 4)
    receipt = world.transact("bob", caller, "make", 4, 7)
    assert "already in use" in receipt.error
    assert receipt.calls[1].kind == "create"
    assert create2_address(caller, 7, Store, 5) != salted  # Arguments are part of the code.
    world.deploy("x", Store, salt=1)
    with pytest.raises(ContractError, match="already in use"):
        world.deploy("x", Store, salt=1)
    assert code_hash(Store, 1) != code_hash(Store, 2)
    with pytest.raises(TypeError):
        code_hash(Contract)
    with pytest.raises(TypeError):
        world.deploy("alice", int)
    with pytest.raises(TypeError, match="deploy contracts"):
        Store()


def test_a_reverting_constructor_deploys_nothing(world):
    class Refuses(Contract):
        layout = ()

        def constructor(self):
            self.require(False, "no")

    with pytest.raises(ContractError, match="no"):
        world.deploy("alice", Refuses)
    assert world.code(create_address("alice", 0)) is None
    assert world.nonce("alice") == 1


def test_blockhash_window(world):
    world.advance(blocks=300)
    assert world.blockhash(world.block_number) == 0
    assert world.blockhash(world.block_number - 257) == 0
    assert world.blockhash(world.block_number - 1) != world.blockhash(world.block_number - 2)
    assert World(seed=1).blockhash(0) != World(seed=2).blockhash(0)


def test_argument_validation(world):
    store = world.deploy("alice", Store)
    with pytest.raises(TypeError):
        world.transact(1, store, "get")
    with pytest.raises(ValueError):
        world.transact("", store, "get")
    with pytest.raises(TypeError):
        world.fund("alice", 1.5)
    with pytest.raises(ValueError, match="layout"):
        world.read("alice", "value")
    assert world.read("alice", "value", layout=Store) == 0
    with pytest.raises(TypeError):
        World(seed="x")
    with pytest.raises(ValueError):
        world.advance(0)
    caller = world.deploy("alice", Caller)
    with pytest.raises(TypeError):
        world.transact("bob", caller, "call_with_gas", store, 1.5)
    context = world.deploy("alice", Context)
    with pytest.raises(TypeError, match="write needs a value"):
        world.transact("alice", context, "no_value")


@given(st.lists(st.integers(0, 50), min_size=1, max_size=8))
def test_transfers_conserve_ether(amounts):
    world = World()
    world.fund("alice", sum(amounts))
    caller = world.deploy("alice", Caller, value=sum(amounts))
    for index, amount in enumerate(amounts):
        world.transact("bob", caller, "pay", f"r{index}", amount)
    paid = sum(world.balance(f"r{index}") for index in range(len(amounts)))
    assert paid + world.balance(caller) == sum(amounts)
    assert bk.contracts.World is World
