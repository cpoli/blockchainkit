"""Verified source code, and why a verified source can still deceive (2016).

A contract is deployed as bytecode, which few people can read. Block
explorers let its author publish the source and *verify* it: the explorer
compiles the source and checks that the result matches the code at the
address. Solidity's metadata hash, added in December 2016, makes the match
exact. Users came to read the badge as "this contract is safe".

It certifies less. It says which code runs at one address, not what that
code calls: a proxy's verified source shows only that it forwards every
call to an implementation address held in storage, which its admin can
change at any time. The behavior a buyer checked is then not the behavior
that runs.

:func:`verify_source` is the explorer's check, and :func:`effective_code`
follows an EIP-1967 proxy to the code that actually runs.
:class:`UpgradeableToken` is a token meant to sit behind a proxy, and
:class:`SeizableToken` the upgrade that lets its owner take anyone's
tokens.
"""

from blockchainkit.contracts.systems.proxies import IMPLEMENTATION_SLOT, EIP1967Proxy
from blockchainkit.contracts.systems.world import Contract, World


def verify_source(world: World, address: str, source: type[Contract]) -> bool:
    """A block explorer's check: is the code at ``address`` exactly ``source``?

    Examples
    --------
    >>> from blockchainkit.contracts import ERC20, ERC721, World
    >>> from blockchainkit.fraud import verify_source
    >>> world = World()
    >>> token = world.deploy("alice", ERC20, 100)
    >>> verify_source(world, token, ERC20), verify_source(world, token, ERC721)
    (True, False)
    """
    return world.code(address) is source


def effective_code(world: World, address: str) -> type[Contract] | None:
    """The code that runs when ``address`` is called, following an EIP-1967 proxy."""
    code = world.code(address)
    if code is EIP1967Proxy:
        implementation = world.storage(address).get(IMPLEMENTATION_SLOT, 0)
        return world.code(implementation) if implementation else None
    return code


class UpgradeableToken(Contract):
    """A fixed-supply token to run behind a proxy: ``initialize`` replaces the constructor."""

    layout = ("owner", "total_supply", "balances")

    def initialize(self, supply: int) -> None:
        """Mint ``supply`` to the caller, who becomes the owner; callable once."""
        self.require(self.read("owner") == 0, "already initialized")
        self.require(type(supply) is int and supply > 0, "supply must be positive")
        self.write("owner", self.sender)
        self.write("total_supply", supply)
        self.write("balances", self.sender, supply)

    def balance_of(self, holder: str) -> int:
        """Tokens held by ``holder``."""
        return int(self.read("balances", holder))

    def transfer(self, to: str, amount: int) -> bool:
        """Move ``amount`` from the caller to ``to``."""
        balance = self.read("balances", self.sender)
        self.require(type(amount) is int and 0 <= amount <= balance, "insufficient balance")
        self.write("balances", self.sender, balance - amount)
        self.write("balances", to, self.read("balances", to) + amount)
        return True


class SeizableToken(UpgradeableToken):
    """The same token with one more function: its owner may take anyone's tokens."""

    def seize(self, holder: str, amount: int) -> None:
        """Move ``amount`` of ``holder``'s tokens to the owner; owner only."""
        self.require(self.sender == self.read("owner"), "only the owner")
        balance = self.read("balances", holder)
        self.require(type(amount) is int and 0 <= amount <= balance, "insufficient balance")
        self.write("balances", holder, balance - amount)
        owner = self.read("owner")
        self.write("balances", owner, self.read("balances", owner) + amount)
