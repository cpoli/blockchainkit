r"""Account abstraction without a consensus change (Buterin et al., ERC-4337, 2021).

On Ethereum an account is either a key pair, which can start transactions
but whose rules are fixed (one ECDSA key, pay gas in ether), or a contract,
whose rules are code but which cannot start a transaction. ERC-4337 lets a
contract account act like a key pair without changing the protocol. The
owner signs a *user operation* and sends it to an alternative mempool.
A *bundler* collects operations and submits them in one ordinary
transaction to a singleton *EntryPoint* contract, which for each operation

#. asks the account to validate it, checking the signature and nonce by
   whatever rule the account's code chooses, and to pay its fee;
#. then runs it, and pays the bundler the fees collected.

A failing validation reverts the whole bundle, at the bundler's cost, so a
bundler first simulates each operation on a copy of the state and drops
those that fail. A failing execution only marks its operation failed: the
fee is still paid. The account's rule can be anything: key rotation,
multisig, social recovery, session keys, or another signature scheme. The
operation hash binds the EntryPoint and the chain,

.. math::

   h = \mathrm{SHA256}(\text{domain} \,\|\, \text{EntryPoint} \,\|\,
   \text{chain} \,\|\, \text{operation}),

so a signed operation cannot be replayed elsewhere.

Teaching differences: the fee is a fixed amount rather than gas used times
a gas price, there are no paymasters, aggregators or factories, accounts
sign with this package's Schnorr signatures, and the validation-phase
restrictions on storage access are not enforced.
"""

import dataclasses
from collections.abc import Sequence
from typing import Any

from blockchainkit.constants import DEFAULT_CHAIN_ID, USER_OPERATION_DOMAIN
from blockchainkit.contracts.core.base import ContractError
from blockchainkit.contracts.systems.world import Contract, World
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.signatures import deterministic_nonce, sign, verify
from blockchainkit.structures.utils.encoding import canonical_json
from blockchainkit.wallets.core.base import UserOperation


def user_operation_hash(
    operation: UserOperation, entry_point: str, chain_id: str = DEFAULT_CHAIN_ID
) -> bytes:
    """The hash an owner signs: every field but the signature, with the EntryPoint and chain."""
    fields = [
        entry_point,
        chain_id,
        operation.sender,
        operation.nonce,
        operation.function,
        list(operation.args),
        operation.fee,
    ]
    return sha256(USER_OPERATION_DOMAIN + canonical_json(fields))


def sign_user_operation(
    operation: UserOperation, private: int, entry_point: str, chain_id: str = DEFAULT_CHAIN_ID
) -> UserOperation:
    """Return ``operation`` signed by ``private``, with an RFC 6979 nonce."""
    digest = user_operation_hash(operation, entry_point, chain_id)
    signature = sign(digest, private, nonce=deterministic_nonce(private, digest))
    return dataclasses.replace(operation, signature=signature)


class EntryPoint(Contract):
    """The singleton that validates and runs user operations, holding each account's deposit."""

    layout = ("deposits",)

    def receive(self) -> None:
        self.write("deposits", self.sender, self.read("deposits", self.sender) + self.value)

    def deposit_to(self, account: str) -> None:
        """Add the ether sent to ``account``'s deposit, from which its fees are paid."""
        self.write("deposits", account, self.read("deposits", account) + self.value)

    def balance_of(self, account: str) -> int:
        """``account``'s deposit."""
        return int(self.read("deposits", account))

    def handle_ops(self, operations: Sequence[UserOperation], beneficiary: str) -> tuple[bool, ...]:
        """Validate every operation, then run each, then pay the fees to ``beneficiary``.

        Returns whether each operation's execution succeeded. Any failed
        validation reverts the whole call.
        """
        collected = 0
        for operation in operations:
            digest = user_operation_hash(operation, self.address)
            deposit = self.read("deposits", operation.sender)
            missing = max(0, operation.fee - deposit)
            try:
                self.call(operation.sender, "validate_user_operation", operation, digest, missing)
            except ContractError as exc:
                raise ContractError(f"validation failed for {operation.sender}: {exc}") from exc
            deposit = self.read("deposits", operation.sender)
            self.require(deposit >= operation.fee, "the account did not pay its fee")
            self.write("deposits", operation.sender, deposit - operation.fee)
            collected += operation.fee
        results = []
        for operation in operations:
            try:
                self.call(operation.sender, operation.function, *operation.args)
                success = True
            except ContractError:
                success = False
            self.emit("UserOperationEvent", sender=operation.sender, success=success)
            results.append(success)
        self.call(beneficiary, None, value=collected)
        return tuple(results)


class SmartAccount(Contract):
    """A contract account owned by a Schnorr key, which it can rotate.

    Parameters
    ----------
    entry_point : str
        The only caller it accepts operations from.
    owner : tuple of int
        The owner's public key.
    """

    layout = ("entry_point", "owner", "nonce")

    def constructor(self, entry_point: str, owner: tuple[int, int]) -> None:
        self.write("entry_point", entry_point)
        self.write("owner", (owner[0], owner[1]))

    def receive(self) -> None:
        pass

    def _only_entry_point(self) -> None:
        self.require(self.sender == self.read("entry_point"), "only the EntryPoint")

    def nonce(self) -> int:
        """The nonce the next operation must carry."""
        return int(self.read("nonce"))

    def validate_user_operation(
        self, operation: UserOperation, digest: bytes, missing: int
    ) -> None:
        """Check the nonce and the owner's signature, and top up the deposit by ``missing``."""
        self._only_entry_point()
        self.require(operation.nonce == self.read("nonce"), "bad nonce")
        signature = operation.signature
        self.require(
            signature is not None and verify(digest, signature, self.read("owner")),
            "bad signature",
        )
        self.write("nonce", operation.nonce + 1)
        if missing:
            self.call(self.sender, "deposit_to", self.address, value=missing)

    def execute(self, to: str, amount: int, function: str | None = None, *args: Any) -> Any:
        """Call ``to`` with ``amount`` of ether; only through the EntryPoint."""
        self._only_entry_point()
        return self.call(to, function, *args, value=amount)

    def execute_batch(self, calls: Sequence[tuple[str, int]]) -> None:
        """Several payments in one operation, all or none."""
        self._only_entry_point()
        for to, amount in calls:
            self.call(to, None, value=amount)

    def rotate_owner(self, owner: tuple[int, int]) -> None:
        """Replace the owner's key; operations signed by the old key then fail."""
        self._only_entry_point()
        self.write("owner", (owner[0], owner[1]))


def simulate_validation(
    world: World, entry_point: str, operation: UserOperation, bundler: str = "bundler"
) -> bool:
    """What a bundler checks before including ``operation``: does it validate, on a fork?"""
    return world.fork().transact(bundler, entry_point, "handle_ops", [operation], bundler).success


def bundle(
    world: World, entry_point: str, operations: Sequence[UserOperation], bundler: str = "bundler"
) -> tuple[UserOperation, ...]:
    """The operations a bundler keeps: those that validate when simulated alone.

    Examples
    --------
    >>> from blockchainkit.contracts import World
    >>> from blockchainkit.crypto import public_key
    >>> from blockchainkit.wallets import (
    ...     EntryPoint, SmartAccount, UserOperation, bundle, sign_user_operation)
    >>> world = World()
    >>> entry = world.deploy("deployer", EntryPoint)
    >>> account = world.deploy("deployer", SmartAccount, entry, public_key(7))
    >>> world.fund("alice", 100)
    >>> world.transact("alice", account, value=100).success
    True
    >>> op = UserOperation(account, 0, "execute", ("bob", 10), fee=2)
    >>> good, forged = sign_user_operation(op, 7, entry), sign_user_operation(op, 8, entry)
    >>> bundle(world, entry, [good, forged]) == (good,)
    True
    """
    return tuple(op for op in operations if simulate_validation(world, entry_point, op, bundler))
