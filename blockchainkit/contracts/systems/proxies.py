"""Upgradeable proxies and storage collisions (2018).

Contract code cannot change, so upgradeable contracts split in two: a
*proxy* that holds the address, the ether and the storage, and forwards
every call by ``DELEGATECALL`` to an *implementation* holding the code.
Upgrading points the proxy at a new implementation, and the state stays.

Both contracts then read the same storage through different layouts. If
the proxy keeps its implementation address in slot 0 and the
implementation keeps its owner there, setting the owner overwrites the
implementation pointer: a *storage collision*. EIP-1967 (2019) moved the
proxy's own fields to slots derived from a hash, ``keccak256(label) - 1``,
where no compiled layout will ever land. A new implementation version must
also keep the old fields in the same order and only append new ones;
reordering them silently reinterprets the stored values.

Slots here are derived with SHA-256 rather than Keccak-256.
"""

from typing import Any, ClassVar

from blockchainkit.constants import EIP1967_ADMIN_LABEL, EIP1967_IMPLEMENTATION_LABEL
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.crypto.systems.hashing import sha256

IMPLEMENTATION_SLOT = int.from_bytes(sha256(EIP1967_IMPLEMENTATION_LABEL), "big") - 1
"""Storage slot of an :class:`EIP1967Proxy`'s implementation address."""

ADMIN_SLOT = int.from_bytes(sha256(EIP1967_ADMIN_LABEL), "big") - 1
"""Storage slot of an :class:`EIP1967Proxy`'s admin address."""


class NaiveProxy(Contract):
    """A proxy keeping its implementation in slot 0 and its admin in slot 1."""

    layout = ("implementation", "admin")

    def constructor(self, implementation: str) -> None:
        self.write("implementation", implementation)
        self.write("admin", self.sender)

    def upgrade_to(self, implementation: str) -> None:
        """Point the proxy at new code; admin only."""
        self.require(self.sender == self.read("admin"), "only the admin upgrades")
        self.write("implementation", implementation)

    def fallback(self, function: str | None, *args: Any) -> Any:
        return self.delegatecall(self.read("implementation"), function, *args)


class EIP1967Proxy(Contract):
    """A proxy keeping its fields in hashed slots that no implementation layout reaches."""

    layout = ()

    def constructor(self, implementation: str) -> None:
        self.write_slot(IMPLEMENTATION_SLOT, implementation)
        self.write_slot(ADMIN_SLOT, self.sender)

    def upgrade_to(self, implementation: str) -> None:
        """Point the proxy at new code; admin only."""
        self.require(self.sender == self.read_slot(ADMIN_SLOT), "only the admin upgrades")
        self.write_slot(IMPLEMENTATION_SLOT, implementation)

    def fallback(self, function: str | None, *args: Any) -> Any:
        return self.delegatecall(self.read_slot(IMPLEMENTATION_SLOT), function, *args)


class BoxV1(Contract):
    """An implementation storing one value that only its owner may set.

    Behind a proxy there is no constructor call, so ``initialize`` sets the owner.
    """

    layout: ClassVar[tuple[str, ...]] = ("owner", "value", "initialized")

    def initialize(self) -> None:
        """Make the caller the owner, once."""
        self.require(not self.read("initialized"), "already initialized")
        self.write("initialized", 1)
        self.write("owner", self.sender)

    def owner(self) -> Any:
        """The owner, as this layout reads it."""
        return self.read("owner")

    def store(self, value: int) -> None:
        """Set the value; owner only."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.write("value", value)

    def retrieve(self) -> Any:
        """The stored value."""
        return self.read("value")


class BoxV2(BoxV1):
    """A compatible upgrade: the old fields keep their slots and a new one is appended."""

    layout: ClassVar[tuple[str, ...]] = (*BoxV1.layout, "changes")

    def store(self, value: int) -> None:
        """Set the value and count the change; owner only."""
        super().store(value)
        self.write("changes", self.read("changes") + 1)

    def changes(self) -> int:
        """How many times the value was set since the upgrade."""
        return int(self.read("changes"))


class BoxV2Reordered(BoxV1):
    """An incompatible upgrade: the same fields declared in another order."""

    layout = ("value", "owner", "initialized")
