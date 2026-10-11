"""Token standards: ERC-20 (2015) and ERC-721 (2018).

ERC-20 fixed one interface for fungible tokens (``transfer``, ``approve``,
``transfer_from``, ``balance_of``), so that any wallet or exchange could hold
any token. Its ``approve`` *overwrites* an allowance, which opens a race:
a spender who sees the owner lower an allowance from N to M can spend N
first, then M as well. :meth:`ERC20.increase_allowance` and
:meth:`ERC20.decrease_allowance` change it relative to its current value
instead.

ERC-721 gives each token its own identity, for collectibles and deeds.
``safe_transfer_from`` asks a contract recipient to confirm, through
``on_erc721_received``, that it can handle the token, so that tokens are not
locked forever in a contract that cannot move them.

Function names are written in Python style (``balance_of`` for
``balanceOf``), amounts are unbounded integers, and functions are matched by
name rather than by 4-byte selector.
"""

from typing import ClassVar

from blockchainkit.contracts.systems.world import Contract

ERC721_RECEIVED = "on_erc721_received"
"""What ``on_erc721_received`` returns to accept a token (the selector in ERC-721)."""


def _amount(contract: Contract, amount: object) -> None:
    contract.require(type(amount) is int and amount >= 0, "amount must be a non-negative integer")


class ERC20(Contract):
    """A fungible token: the creator receives the whole fixed ``supply``.

    The invariant ``total_supply == sum of balances`` is checked after every call.
    """

    layout: ClassVar[tuple[str, ...]] = ("total_supply", "balances", "allowances")

    def constructor(self, supply: int) -> None:
        _amount(self, supply)
        self.write("total_supply", supply)
        self.write("balances", self.sender, supply)
        self.emit("Transfer", sender=None, to=self.sender, amount=supply)

    def total_supply(self) -> int:
        """Tokens in existence."""
        return int(self.read("total_supply"))

    def balance_of(self, owner: str) -> int:
        """Tokens held by ``owner``."""
        return int(self.read("balances", owner))

    def allowance(self, owner: str, spender: str) -> int:
        """Tokens ``spender`` may still move out of ``owner``'s balance."""
        return int(self.read("allowances", owner, spender))

    def _move(self, source: str, destination: str, amount: int) -> None:
        _amount(self, amount)
        balance = self.read("balances", source)
        self.require(balance >= amount, "insufficient balance")
        self.write("balances", source, balance - amount)
        self.write("balances", destination, self.read("balances", destination) + amount)
        self.emit("Transfer", sender=source, to=destination, amount=amount)

    def transfer(self, to: str, amount: int) -> bool:
        """Move ``amount`` from the caller to ``to``."""
        self._move(self.sender, to, amount)
        return True

    def approve(self, spender: str, amount: int) -> bool:
        """Set ``spender``'s allowance over the caller's tokens to ``amount``, whatever it was."""
        _amount(self, amount)
        self.write("allowances", self.sender, spender, amount)
        self.emit("Approval", owner=self.sender, spender=spender, amount=amount)
        return True

    def increase_allowance(self, spender: str, added: int) -> bool:
        """Raise ``spender``'s allowance by ``added``."""
        _amount(self, added)
        current = self.read("allowances", self.sender, spender)
        return self.approve(spender, current + added)

    def decrease_allowance(self, spender: str, subtracted: int) -> bool:
        """Lower ``spender``'s allowance by ``subtracted``, reverting below zero.

        If the spender has already spent part of it, the call reverts
        instead of granting the old allowance on top.
        """
        _amount(self, subtracted)
        current = self.read("allowances", self.sender, spender)
        self.require(current >= subtracted, "allowance below zero")
        return self.approve(spender, current - subtracted)

    def transfer_from(self, owner: str, to: str, amount: int) -> bool:
        """Move ``amount`` of ``owner``'s tokens to ``to``, spending the caller's allowance."""
        _amount(self, amount)
        allowed = self.read("allowances", owner, self.sender)
        self.require(allowed >= amount, "allowance exceeded")
        self.write("allowances", owner, self.sender, allowed - amount)
        self._move(owner, to, amount)
        return True

    def invariant(self) -> bool:
        return bool(self.read("total_supply") == sum(self.entries("balances").values()))


class ERC721(Contract):
    """A non-fungible token: each ``token_id`` has exactly one owner.

    Only the deployer (the *minter*) creates tokens.
    """

    layout = ("minter", "owners", "balances", "approvals")

    def constructor(self) -> None:
        self.write("minter", self.sender)

    def mint(self, to: str, token_id: int) -> None:
        """Create ``token_id`` for ``to``."""
        self.require(self.sender == self.read("minter"), "only the minter mints")
        self.require(self.read("owners", token_id) == 0, "token already exists")
        self.write("owners", token_id, to)
        self.write("balances", to, self.read("balances", to) + 1)
        self.emit("Transfer", sender=None, to=to, token_id=token_id)

    def owner_of(self, token_id: int) -> str:
        """The owner of ``token_id``."""
        owner = self.read("owners", token_id)
        self.require(owner != 0, "no such token")
        return str(owner)

    def balance_of(self, owner: str) -> int:
        """Number of tokens ``owner`` holds."""
        return int(self.read("balances", owner))

    def approve(self, spender: str, token_id: int) -> None:
        """Let ``spender`` transfer ``token_id`` once."""
        self.require(self.sender == self.owner_of(token_id), "only the owner approves")
        self.write("approvals", token_id, spender)

    def transfer_from(self, owner: str, to: str, token_id: int) -> None:
        """Move ``token_id`` from ``owner`` to ``to``, whatever ``to`` is."""
        self.require(self.owner_of(token_id) == owner, "not the owner")
        allowed = self.sender == owner or self.sender == self.read("approvals", token_id)
        self.require(allowed, "not authorized")
        self.write("approvals", token_id, 0)
        self.write("owners", token_id, to)
        self.write("balances", owner, self.read("balances", owner) - 1)
        self.write("balances", to, self.read("balances", to) + 1)
        self.emit("Transfer", sender=owner, to=to, token_id=token_id)

    def safe_transfer_from(self, owner: str, to: str, token_id: int) -> None:
        """Like :meth:`transfer_from`, but a contract recipient must accept the token.

        The recipient's ``on_erc721_received`` must return
        :data:`ERC721_RECEIVED`; a contract without the function makes the
        call, and so the transfer, revert.
        """
        self.transfer_from(owner, to, token_id)
        if self.code_at(to) is not None:
            answer = self.call(to, "on_erc721_received", self.sender, owner, token_id)
            self.require(answer == ERC721_RECEIVED, "recipient rejected the token")


class NFTVault(Contract):
    """A contract that accepts ERC-721 tokens and lets its owner send them on."""

    layout = ("owner",)

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def on_erc721_received(self, operator: str, owner: str, token_id: int) -> str:
        """Accept any token."""
        return ERC721_RECEIVED

    def send_token(self, token: str, to: str, token_id: int) -> None:
        """Move a held token to ``to``; owner only."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.call(token, "transfer_from", self.address, to, token_id)
