"""A world-state model: accounts, contracts, and the calls between them.

Contracts are short Python classes deriving from :class:`Contract`. Their
public methods are the contract's functions, and they reach the world only
through the methods of :class:`Contract`: storage per contract, ``msg.sender``
and ``msg.value``, ``call`` and ``delegatecall``, ``send`` with its gas
stipend, ``create``, events and ``selfdestruct``. A :class:`World` runs
transactions against them, metering gas and undoing the whole call tree, or
only the failing sub-call, on a revert.

Storage follows Solidity's layout in spirit: field ``i`` of a contract's
``layout`` lives in slot ``i``, and entry ``k`` of a mapping field in slot
``(i, k)``. A ``delegatecall`` runs the callee's code on the caller's
storage, through the *callee's* layout, which is exactly how proxy storage
collisions arise.

This is a model of the EVM's call semantics, not the EVM: values are Python
objects rather than 256-bit words, arithmetic is unbounded (as with
Solidity 0.8's checked arithmetic, but without overflow), functions are
dispatched by name rather than by selector, gas costs are a short teaching
schedule, and ``selfdestruct`` takes effect immediately rather than at the
end of the transaction.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar

from blockchainkit._validation import integer
from blockchainkit._validation import seed as _check_seed
from blockchainkit.constants import BLOCKHASH_DOMAIN, CREATE2_DOMAIN, CREATE_DOMAIN
from blockchainkit.contracts.core.base import CallRecord, ContractError, Event, Receipt
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.utils.encoding import canonical_json

GAS_COSTS: Mapping[str, int] = MappingProxyType(
    {
        "transaction": 21_000,
        "read": 800,
        "write": 5_000,
        "call": 700,
        "create": 32_000,
        "log": 375,
        "selfdestruct": 5_000,
    }
)
"""The teaching gas schedule, rounded from Ethereum's. A storage write costs
5,000 here; Ethereum charges 20,000 to fill an empty slot and 2,900 to change one."""

CALL_STIPEND = 2_300
"""Gas given to the recipient of :meth:`Contract.send`: enough to log an event,
not enough to write storage."""

MAX_CALL_DEPTH = 128
"""Default call-depth limit. Ethereum's is 1024; a lower default keeps nested
Python calls within the interpreter's recursion limit."""

BLOCK_GAS_LIMIT = 30_000_000
"""Default gas limit of a block, and so of one transaction."""

_RESERVED = frozenset({"constructor", "receive", "fallback", "invariant", "layout"})


def _address(digest: bytes) -> str:
    return "0x" + digest[-20:].hex()


def _account(value: str, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an address string, not {type(value).__name__}")
    if not value:
        raise ValueError(f"{name} must be a non-empty address")


def _contract_class(code: object) -> None:
    if not (isinstance(code, type) and issubclass(code, Contract)) or code is Contract:
        raise TypeError("code must be a subclass of Contract")


def code_hash(code: type[Contract], *args: Any) -> bytes:
    """Hash identifying a contract's creation code: its class and constructor arguments.

    Stands in for the hash of EVM init code, which also includes the
    constructor's arguments.
    """
    _contract_class(code)
    return sha256(f"{code.__module__}.{code.__qualname__}{args!r}".encode())


def create_address(deployer: str, nonce: int) -> str:
    """Address of the contract that ``deployer`` creates with its ``nonce``-th creation (CREATE).

    Examples
    --------
    >>> from blockchainkit.contracts import create_address
    >>> create_address("alice", 0) == create_address("alice", 0) != create_address("alice", 1)
    True
    """
    _account(deployer, "deployer")
    integer(nonce, "nonce")
    return _address(sha256(CREATE_DOMAIN + canonical_json([deployer, nonce])))


def create2_address(deployer: str, salt: int, code: type[Contract], *args: Any) -> str:
    """Address of the contract that ``deployer`` creates with ``salt`` (CREATE2, EIP-1014).

    It depends only on the deployer, the salt and the creation code, so it
    is known before anything is deployed.
    """
    _account(deployer, "deployer")
    integer(salt, "salt")
    return _address(
        sha256(CREATE2_DOMAIN + canonical_json([deployer, salt]) + code_hash(code, *args))
    )


@dataclass
class _Frame:
    """The execution context of one call."""

    address: str
    code_address: str
    sender: str
    value: int
    origin: str
    depth: int
    gas: int
    metered: bool = True


class Contract:
    """Base class of every contract: subclass it, declare ``layout``, and write methods.

    Public methods (names not starting with ``_``) are the contract's
    functions. Optional hooks: ``constructor(*args)`` runs once at
    deployment; ``receive()`` runs on a plain payment; ``fallback(function,
    *args)`` runs when no function matches; ``invariant()`` is checked after
    every call and a False result reverts it (Meyer's class invariant).

    A contract never holds state in Python attributes: everything it keeps
    goes through :meth:`read` and :meth:`write`, so that the world can meter,
    roll back and share it.

    Attributes
    ----------
    layout : tuple of str
        Storage field names; field ``i`` lives in slot ``i``.
    """

    layout: ClassVar[tuple[str, ...]] = ()
    _world: World
    _frame: _Frame

    def __init__(self) -> None:
        raise TypeError("deploy contracts with World.deploy or Contract.create")

    # Context ----------------------------------------------------------------

    @property
    def address(self) -> str:
        """The address whose storage and balance this code is using (``address(this)``)."""
        return self._frame.address

    @property
    def sender(self) -> str:
        """The immediate caller (``msg.sender``)."""
        return self._frame.sender

    @property
    def value(self) -> int:
        """Ether sent with this call (``msg.value``)."""
        return self._frame.value

    @property
    def origin(self) -> str:
        """The account that signed the transaction (``tx.origin``)."""
        return self._frame.origin

    @property
    def block_number(self) -> int:
        """Number of the block being built."""
        return self._world.block_number

    @property
    def timestamp(self) -> int:
        """Timestamp of the block being built."""
        return self._world.timestamp

    @property
    def gas_left(self) -> int:
        """Gas remaining in this call."""
        return self._frame.gas

    def blockhash(self, number: int) -> int:
        """Hash of one of the 256 previous blocks as an integer, 0 for any other block."""
        return self._world.blockhash(number)

    # Storage ----------------------------------------------------------------

    def _slot(self, name: str, keys: tuple[Any, ...]) -> int | tuple[Any, ...]:
        return _slot(type(self), name, keys)

    def read(self, name: str, *keys: Any) -> Any:
        """Read field ``name``, or its entry at ``keys`` for a mapping; 0 if never written."""
        self.use_gas(GAS_COSTS["read"])
        return self._world._storage.get(self.address, {}).get(self._slot(name, keys), 0)

    def write(self, name: str, *keys_and_value: Any) -> None:
        """Write field ``name``: ``write("owner", x)``, or ``write("balances", key, x)``."""
        if not keys_and_value:
            raise TypeError("write needs a value")
        *keys, value = keys_and_value
        self.write_slot(self._slot(name, tuple(keys)), value)

    def read_slot(self, slot: int | tuple[Any, ...]) -> Any:
        """Read a raw storage slot, ignoring the layout."""
        self.use_gas(GAS_COSTS["read"])
        return self._world._storage.get(self.address, {}).get(slot, 0)

    def write_slot(self, slot: int | tuple[Any, ...], value: Any) -> None:
        """Write a raw storage slot, ignoring the layout; writing 0 clears it."""
        self.use_gas(GAS_COSTS["write"])
        storage = self._world._storage.setdefault(self.address, {})
        if value == 0:
            storage.pop(slot, None)
        else:
            storage[slot] = value

    def entries(self, name: str) -> dict[Any, Any]:
        """Every nonzero entry of mapping field ``name``, keyed as written.

        The EVM cannot enumerate a mapping; this is for invariants and tests.
        """
        index = type(self).layout.index(name)
        storage = self._world._storage.get(self.address, {})
        found = {}
        for slot, value in storage.items():
            if isinstance(slot, tuple) and slot[0] == index:
                self.use_gas(GAS_COSTS["read"])
                found[slot[1] if len(slot) == 2 else slot[1:]] = value
        return found

    # Ether and calls --------------------------------------------------------

    def ether_balance(self, account: str | None = None) -> int:
        """Ether held by ``account``, by default this contract."""
        self.use_gas(GAS_COSTS["read"])
        return self._world.balance(self.address if account is None else account)

    def code_at(self, account: str) -> type[Contract] | None:
        """The code deployed at ``account``, None for an account without code."""
        self.use_gas(GAS_COSTS["read"])
        return self._world.code(account)

    def call(
        self, to: str, function: str | None, *args: Any, value: int = 0, gas: int | None = None
    ) -> Any:
        """Call ``function`` on ``to``, forwarding at most 63/64 of the remaining gas.

        ``function=None`` makes a plain payment, handled by ``receive``. A
        revert in the callee undoes the callee's changes and propagates, as
        a Solidity high-level call does.
        """
        self.use_gas(GAS_COSTS["call"])
        return self._world._message_call(self._frame, "call", to, function, args, value, gas)

    def delegatecall(self, to: str, function: str | None, *args: Any) -> Any:
        """Run ``to``'s code on this contract's storage, keeping ``msg.sender`` and ``msg.value``.

        If ``to`` has no code, nothing runs and None is returned, as in the EVM.
        """
        self.use_gas(GAS_COSTS["call"])
        return self._world._message_call(self._frame, "delegatecall", to, function, args, 0, None)

    def send(self, to: str, amount: int) -> bool:
        """Pay ``amount`` to ``to`` with a gas stipend of 2,300; return False instead of reverting.

        Solidity's ``send`` and ``transfer``: the stipend is too small for a
        recipient whose ``receive`` writes storage.
        """
        self.use_gas(GAS_COSTS["call"])
        try:
            self._world._message_call(self._frame, "call", to, None, (), amount, None, True)
        except ContractError:
            return False
        return True

    def create(
        self, code: type[Contract], *args: Any, value: int = 0, salt: int | None = None
    ) -> str:
        """Deploy ``code`` from here (CREATE, or CREATE2 with ``salt``) and return its address."""
        self.use_gas(GAS_COSTS["create"])
        return self._world._create(self._frame, code, args, value, salt)

    def selfdestruct(self, beneficiary: str) -> None:
        """Send all of this account's ether to ``beneficiary`` and delete its code and storage."""
        self.use_gas(GAS_COSTS["selfdestruct"])
        self._world._selfdestruct(self.address, beneficiary)

    # Control ----------------------------------------------------------------

    def emit(self, name: str, **fields: Any) -> None:
        """Log an event; it survives only if no enclosing call reverts."""
        self.use_gas(GAS_COSTS["log"])
        self._world._events.append(Event(self.address, name, MappingProxyType(fields)))

    def require(self, condition: object, message: str = "requirement failed") -> None:
        """Revert with ``message`` unless ``condition`` is true."""
        if not condition:
            raise ContractError(message)

    def use_gas(self, amount: int) -> None:
        """Consume gas, reverting with ``"out of gas"`` if too little is left."""
        frame = self._frame
        if not frame.metered:
            return
        if amount > frame.gas:
            frame.gas = 0
            raise ContractError("out of gas")
        frame.gas -= amount

    def invariant(self) -> bool:
        """Override to state what must hold after every call; checked without gas."""
        return True


def _slot(code: type[Contract], name: str, keys: tuple[Any, ...]) -> int | tuple[Any, ...]:
    if name not in code.layout:
        raise KeyError(f"{name!r} is not a field of {code.__name__}.layout")
    index = code.layout.index(name)
    return (index, *keys) if keys else index


_HELPERS = frozenset(vars(Contract))


def _function(code: type[Contract], name: str) -> Any:
    if name.startswith("_") or name in _RESERVED or name in _HELPERS:
        return None
    attribute = getattr(code, name, None)
    return attribute if callable(attribute) else None


def _allowance(gas: int) -> int:
    integer(gas, "gas")
    return gas


def _hook(instance: Contract, name: str) -> Any:
    return getattr(instance, name)


def _defines(code: type[Contract], hook: str) -> bool:
    return getattr(code, hook, None) is not getattr(Contract, hook, None)


class World:
    """Accounts, contract code and storage, and the block the next transaction lands in.

    Parameters
    ----------
    block_gas_limit : int
        The most gas any transaction may use.
    max_call_depth : int
        Calls nested deeper than this revert.
    seed : int
        Seeds the block hashes.

    Examples
    --------
    >>> from blockchainkit.contracts import ERC20, World
    >>> world = World()
    >>> token = world.deploy("alice", ERC20, 1_000)
    >>> world.transact("alice", token, "transfer", "bob", 250).success
    True
    >>> world.view(token, "balance_of", "bob")
    250
    """

    def __init__(
        self,
        *,
        block_gas_limit: int = BLOCK_GAS_LIMIT,
        max_call_depth: int = MAX_CALL_DEPTH,
        seed: int = 0,
    ) -> None:
        integer(block_gas_limit, "block_gas_limit", GAS_COSTS["transaction"])
        integer(max_call_depth, "max_call_depth", 1)
        _check_seed(seed)
        self.block_gas_limit = block_gas_limit
        self.max_call_depth = max_call_depth
        self.seed = seed
        self.block_number = 1
        self.timestamp = 0
        self._balances: dict[str, int] = {}
        self._code: dict[str, type[Contract]] = {}
        self._storage: dict[str, dict[Any, Any]] = {}
        self._nonces: dict[str, int] = {}
        self._names: dict[str, str] = {}
        self._events: list[Event] = []
        self._calls: list[CallRecord | None] = []

    # Inspection -------------------------------------------------------------

    def fund(self, account: str, amount: int) -> None:
        """Credit ``amount`` of new ether to ``account``, like a genesis allocation."""
        _account(account, "account")
        integer(amount, "amount")
        self._balances[account] = self._balances.get(account, 0) + amount

    def balance(self, account: str) -> int:
        """Ether held by ``account``."""
        _account(account, "account")
        return self._balances.get(account, 0)

    def code(self, account: str) -> type[Contract] | None:
        """The contract class deployed at ``account``, or None."""
        return self._code.get(account)

    def storage(self, account: str) -> Mapping[Any, Any]:
        """A read-only copy of ``account``'s storage, slot to value."""
        return MappingProxyType(dict(self._storage.get(account, {})))

    def read(
        self, account: str, name: str, *keys: Any, layout: type[Contract] | None = None
    ) -> Any:
        """Read a storage field of ``account`` without gas, through its code's layout.

        Pass ``layout`` to read through another contract's layout, such as a
        proxy's storage through its implementation's.
        """
        code = self._code.get(account) if layout is None else layout
        if code is None:
            raise ValueError(f"no contract at {account}; pass layout=")
        return self._storage.get(account, {}).get(_slot(code, name, keys), 0)

    def nonce(self, account: str) -> int:
        """Transactions sent by an account, or contracts created by a contract."""
        return self._nonces.get(account, 0)

    def name(self, account: str) -> str:
        """The label given at deployment, or the address itself."""
        return self._names.get(account, account)

    def blockhash(self, number: int) -> int:
        """Hash of block ``number`` as an integer, if it is one of the 256 before the current one.

        Like the EVM's ``BLOCKHASH``, it returns 0 for the current block, for
        future blocks and for older ones.
        """
        integer(number, "number")
        if not self.block_number - 256 <= number < self.block_number:
            return 0
        digest = sha256(BLOCKHASH_DOMAIN + canonical_json([self.seed, number]))
        return int.from_bytes(digest, "big")

    def fork(self) -> World:
        """An independent copy of this world, to try transactions on without changing this one.

        Like a local fork of a live chain, it is how a wallet or a scanner
        can check what a transaction would do before anyone sends it.

        Examples
        --------
        >>> from blockchainkit.contracts import World
        >>> world = World()
        >>> world.fund("alice", 10)
        >>> trial = world.fork()
        >>> trial.transact("alice", "bob", value=10).success
        True
        >>> world.balance("bob"), trial.balance("bob")
        (0, 10)
        """
        other = copy.copy(self)
        other._balances = dict(self._balances)
        other._code = dict(self._code)
        other._storage = {account: dict(slots) for account, slots in self._storage.items()}
        other._nonces = dict(self._nonces)
        other._names = dict(self._names)
        other._events = list(self._events)
        other._calls = list(self._calls)
        return other

    def advance(self, blocks: int = 1, seconds: int | None = None) -> None:
        """Move to a later block; ``seconds`` defaults to 12 per block."""
        integer(blocks, "blocks", 1)
        seconds = 12 * blocks if seconds is None else seconds
        integer(seconds, "seconds")
        self.block_number += blocks
        self.timestamp += seconds

    # Transactions -----------------------------------------------------------

    def transact(
        self,
        sender: str,
        to: str,
        function: str | None = None,
        *args: Any,
        value: int = 0,
        gas: int | None = None,
    ) -> Receipt:
        """Send a transaction calling ``function`` on ``to``; a revert is reported, not raised.

        ``function=None`` makes a plain payment.
        """
        _account(sender, "sender")
        _account(to, "to")
        integer(value, "value")
        gas = self._gas(gas)
        self._nonces[sender] = self._nonces.get(sender, 0) + 1
        self._calls, self._events = [], []
        frame = _Frame(to, to, sender, value, sender, 0, gas - GAS_COSTS["transaction"])
        try:
            result = self._execute("call", frame, function, args)
        except ContractError as exc:
            return Receipt(False, None, str(exc), gas - frame.gas, self._records(), ())
        return Receipt(True, result, None, gas - frame.gas, self._records(), tuple(self._events))

    def deploy(
        self,
        deployer: str,
        code: type[Contract],
        *args: Any,
        value: int = 0,
        salt: int | None = None,
        name: str | None = None,
        gas: int | None = None,
    ) -> str:
        """Deploy ``code`` in a transaction from ``deployer`` and return the new address.

        Parameters
        ----------
        deployer : str
            The sending account.
        code : type
            A subclass of :class:`Contract`.
        *args
            The constructor's arguments.
        value : int
            Ether sent to the new contract.
        salt : int, optional
            Use CREATE2 with this salt instead of CREATE.
        name : str, optional
            A label for traces and plots.
        gas : int, optional
            Gas limit; defaults to the block gas limit.

        Raises
        ------
        ContractError
            The constructor reverted or the address is taken; nothing is deployed.
        """
        _account(deployer, "deployer")
        integer(value, "value")
        gas = self._gas(gas)
        self._calls, self._events = [], []
        frame = _Frame(
            deployer, deployer, deployer, 0, deployer, -1, gas - GAS_COSTS["transaction"]
        )
        address = self._create(frame, code, args, value, salt)
        if name is not None:
            self._names[address] = name
        return address

    def view(self, to: str, function: str, *args: Any) -> Any:
        """Call ``function`` and return its result, then undo everything it did.

        Raises
        ------
        ContractError
            The call reverted.
        """
        _account(to, "to")
        snapshot = self._snapshot()
        calls, events = self._calls, self._events
        frame = _Frame(to, to, to, 0, to, 0, self.block_gas_limit)
        try:
            return self._execute("call", frame, function, args)
        finally:
            self._restore(snapshot)
            self._calls, self._events = calls, events

    # Machinery --------------------------------------------------------------

    def _gas(self, gas: int | None) -> int:
        if gas is None:
            return self.block_gas_limit
        integer(gas, "gas", GAS_COSTS["transaction"])
        if gas > self.block_gas_limit:
            raise ValueError("gas exceeds the block gas limit")
        return gas

    def _records(self) -> tuple[CallRecord, ...]:
        return tuple(record for record in self._calls if record is not None)

    def _snapshot(self) -> tuple[Any, ...]:
        return (
            dict(self._balances),
            dict(self._code),
            {account: dict(slots) for account, slots in self._storage.items()},
            dict(self._nonces),
            len(self._events),
        )

    def _restore(self, snapshot: tuple[Any, ...]) -> None:
        self._balances, self._code, self._storage, self._nonces, events = snapshot
        del self._events[events:]

    def _transfer(self, source: str, destination: str, amount: int) -> None:
        if amount == 0:
            return
        if self._balances.get(source, 0) < amount:
            raise ContractError("insufficient balance")
        self._balances[source] -= amount
        self._balances[destination] = self._balances.get(destination, 0) + amount

    def _message_call(
        self,
        parent: _Frame,
        kind: str,
        to: str,
        function: str | None,
        args: tuple[Any, ...],
        value: int,
        gas: int | None,
        stipend: bool = False,
    ) -> Any:
        _account(to, "to")
        integer(value, "value")
        if kind == "delegatecall":
            context, sender, value = parent.address, parent.sender, parent.value
        else:
            context, sender = to, parent.address
        available = parent.gas - parent.gas // 64
        if stipend:
            allowance = CALL_STIPEND
        else:
            allowance = available if gas is None else min(_allowance(gas), available)
        child = _Frame(context, to, sender, value, parent.origin, parent.depth + 1, allowance)
        try:
            return self._execute(kind, child, function, args)
        finally:
            if not stipend:
                parent.gas -= allowance - child.gas

    def _create(
        self,
        parent: _Frame,
        code: type[Contract],
        args: tuple[Any, ...],
        value: int,
        salt: int | None,
    ) -> str:
        _contract_class(code)
        integer(value, "value")
        deployer = parent.address
        nonce = self._nonces.get(deployer, 0)
        if salt is None:
            address = create_address(deployer, nonce)
        else:
            address = create2_address(deployer, salt, code, *args)
        self._nonces[deployer] = nonce + 1
        allowance = parent.gas - parent.gas // 64
        child = _Frame(
            address, address, deployer, value, parent.origin, parent.depth + 1, allowance
        )
        try:
            self._execute("create", child, "constructor", args, code)
        finally:
            parent.gas -= allowance - child.gas
        return address

    def _execute(
        self,
        kind: str,
        frame: _Frame,
        function: str | None,
        args: tuple[Any, ...],
        new_code: type[Contract] | None = None,
    ) -> Any:
        index = len(self._calls)
        self._calls.append(None)
        start = frame.gas
        snapshot = self._snapshot()
        error: str | None = "exception"
        try:
            if frame.depth > self.max_call_depth:
                raise ContractError("call depth limit reached")
            if new_code is not None:
                if frame.address in self._code or self._nonces.get(frame.address, 0):
                    raise ContractError(f"address {frame.address} is already in use")
                self._code[frame.address] = new_code
            if kind != "delegatecall":
                self._transfer(frame.sender, frame.address, frame.value)
            result = self._dispatch(kind, frame, function, args)
            error = None
            return result
        except ContractError as exc:
            error = str(exc)
            self._restore(snapshot)
            raise
        except BaseException:
            self._restore(snapshot)
            raise
        finally:
            to = frame.code_address
            self._calls[index] = CallRecord(
                max(frame.depth, 0),
                kind,
                frame.sender,
                to,
                frame.address,
                function,
                frame.value,
                start - frame.gas,
                error,
            )

    def _dispatch(
        self, kind: str, frame: _Frame, function: str | None, args: tuple[Any, ...]
    ) -> Any:
        code = self._code.get(frame.code_address)
        if code is None:
            if function is None or kind == "delegatecall":
                return None
            raise ContractError(f"no contract at {self.name(frame.code_address)}")
        instance = object.__new__(code)
        instance._world = self
        instance._frame = frame
        if kind == "create":
            if _defines(code, "constructor"):
                result = _hook(instance, "constructor")(*args)
            elif args:
                raise TypeError(f"{code.__name__} has no constructor but got arguments")
        elif function is None:
            if _defines(code, "receive"):
                result = _hook(instance, "receive")()
            elif _defines(code, "fallback"):
                result = _hook(instance, "fallback")(None)
            else:
                raise ContractError(f"{code.__name__} does not accept payments")
        elif _function(code, function) is not None:
            result = getattr(instance, function)(*args)
        elif _defines(code, "fallback"):
            result = _hook(instance, "fallback")(function, *args)
        else:
            raise ContractError(f"{code.__name__} has no function {function!r}")
        if kind == "create":
            result = None
        if frame.address in self._code:
            with _unmetered(frame):
                held = instance.invariant()
            if not held:
                raise ContractError(f"invariant of {code.__name__} violated")
        return result

    def _selfdestruct(self, account: str, beneficiary: str) -> None:
        _account(beneficiary, "beneficiary")
        amount = self._balances.pop(account, 0)
        if beneficiary != account:
            self._balances[beneficiary] = self._balances.get(beneficiary, 0) + amount
        self._code.pop(account, None)
        self._storage.pop(account, None)


@contextmanager
def _unmetered(frame: _Frame) -> Iterator[None]:
    metered, frame.metered = frame.metered, False
    try:
        yield
    finally:
        frame.metered = metered
