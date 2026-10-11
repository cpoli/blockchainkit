"""Honeypot contracts that trap would-be thieves (Torres, Steichen and State, 2019).

A honeypot is a contract that seems to leak its balance to anyone who reads
its source closely enough to spot the flaw. The reader sends ether to
exploit it, and the flaw turns out to be a trap: the ether stays with the
contract, where only its creator can reach it. Torres et al. found 690
honeypots on Ethereum and classified their techniques.

Three rest on EVM semantics or on what a block explorer shows, and are
modelled directly:

- *balance disorder* (:class:`MultiplicatorX3`): ``this.balance`` already
  includes the ether sent with the call;
- *hidden state update* (:class:`GiftBox`): the explorer lists internal
  calls only when they carry ether, so a state change made through a
  contract with no ether goes unseen (:func:`explorer_view`);
- *straw man contract* (:class:`PrivateBank`): the source shows a logger,
  but the deployed address holds different code (:class:`TrapLog`).

Four are quirks of the Solidity language or compiler, reproduced here by
their effect rather than by compiling anything:

- *inheritance disorder* (:class:`KingOfTheHill`): a child contract's
  ``owner`` is a different variable from its parent's;
- *uninitialised storage struct* (:class:`GuessNumber`): a local struct
  declared without ``memory`` points at storage slot 0 and overwrites it;
- *type deduction overflow* (:class:`ForTest`): ``var i = 0`` is a ``uint8``,
  so a loop meant to double the deposit wraps around after 255;
- *skipped empty string literal* (:class:`DividendDistributor`): before
  Solidity 0.4.12 the encoder dropped a ``""`` argument, shifting the
  others, so a refund was paid to the owner.
"""

from collections.abc import Iterable
from typing import Any, ClassVar

from blockchainkit.contracts.core.base import CallRecord, Receipt
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.crypto.systems.hashing import sha256


def explorer_view(receipts: Iterable[Receipt], address: str) -> tuple[CallRecord, ...]:
    """The calls to ``address`` that a 2018 block explorer listed.

    It listed every transaction sent to the address, but an internal call
    from another contract only if it carried ether.
    """
    return tuple(
        record
        for receipt in receipts
        for record in receipt.calls
        if record.to == address and (record.depth == 0 or record.value > 0)
    )


class Relay(Contract):
    """Forwards calls, with their ether, for its owner: how a honeypot's creator hides a call."""

    layout: ClassVar[tuple[str, ...]] = ("owner",)

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def forward(self, target: str, function: str, *args: Any) -> Any:
        """Call ``function`` on ``target`` with the ether sent; owner only."""
        self.require(self.sender == self.read("owner"), "only the owner")
        return self.call(target, function, *args, value=self.value)


class Honeypot(Contract):
    """Base of the honeypots here: it accepts bait, and only its creator can take it out."""

    layout: ClassVar[tuple[str, ...]] = ("owner",)

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def receive(self) -> None:
        pass

    def withdraw(self) -> None:
        """Take the whole balance; creator only."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.call(self.sender, None, value=self.ether_balance())


class MultiplicatorX3(Honeypot):
    """Balance disorder: pays ``this.balance + msg.value`` if the deposit covers the balance.

    The reader expects that sending at least the current balance wins it all
    back with interest. By the time the condition runs, ``this.balance``
    already includes the deposit, so it can never be covered.
    """

    def multiplicate(self, beneficiary: str) -> None:
        """Pay out ``this.balance + msg.value`` if ``msg.value >= this.balance``."""
        if self.value >= self.ether_balance():
            self.call(beneficiary, None, value=self.ether_balance() + self.value)


class GiftBox(Honeypot):
    """Hidden state update: whoever sets the password may claim the gift.

    The creator closes the box through a :class:`Relay` with no ether, a call
    the explorer does not list. Later ``set_pass`` calls keep their ether
    and change nothing.

    Parameters
    ----------
    price : int
        The least ether ``set_pass`` must carry.
    """

    layout: ClassVar[tuple[str, ...]] = ("owner", "hash_pass", "closed", "setter", "price")

    def constructor(self, price: int = 1_000) -> None:
        super().constructor()
        self.write("price", price)

    def set_pass(self, digest: bytes) -> None:
        """Set the password's hash, if the box is open and enough ether is sent."""
        if not self.read("closed") and self.value >= self.read("price"):
            self.write("hash_pass", digest)
            self.write("setter", self.sender)

    def get_gift(self, password: bytes) -> None:
        """Take the whole balance with the password whose hash was set."""
        if self.read("hash_pass") == sha256(password):
            self.call(self.sender, None, value=self.ether_balance())

    def pass_has_been_set(self, digest: bytes) -> None:
        """Close the box; only whoever set the current password can."""
        if self.sender == self.read("setter") and digest == self.read("hash_pass"):
            self.write("closed", 1)


class Log(Contract):
    """The logger that :class:`PrivateBank`'s source shows: it records every message."""

    layout: ClassVar[tuple[str, ...]] = ("count",)

    def add_message(self, account: str, amount: int, data: str) -> None:
        """Record a message."""
        self.write("count", self.read("count") + 1)
        self.emit("Message", account=account, amount=amount, data=data)


class TrapLog(Log):
    """The logger actually deployed: it reverts every cash-out but its creator's."""

    layout: ClassVar[tuple[str, ...]] = ("count", "owner")

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def add_message(self, account: str, amount: int, data: str) -> None:
        """Record a message, reverting a cash-out by anyone but the creator."""
        self.require(data != "CashOut" or account == self.read("owner"), "")
        super().add_message(account, amount, data)


class PrivateBank(Contract):
    """Straw man contract: a bank that pays before it updates the balance, and logs both.

    It looks open to reentrancy, but the logger passed to the constructor is
    a :class:`TrapLog`, which reverts every cash-out and with it the payment.

    Parameters
    ----------
    log : str
        Address of the logger.
    minimum : int
        The least deposit that counts.
    """

    layout: ClassVar[tuple[str, ...]] = ("balances", "log", "minimum")

    def constructor(self, log: str, minimum: int = 100) -> None:
        self.write("log", log)
        self.write("minimum", minimum)

    def deposit(self) -> None:
        """Credit a deposit of at least ``minimum``."""
        if self.value >= self.read("minimum"):
            balance = self.read("balances", self.sender)
            self.write("balances", self.sender, balance + self.value)
            self.call(self.read("log"), "add_message", self.sender, self.value, "Deposit")

    def cash_out(self, amount: int) -> None:
        """Pay ``amount`` of the caller's balance, then update and log it."""
        if amount <= self.read("balances", self.sender):
            self.call(self.sender, None, value=amount)
            balance = self.read("balances", self.sender)
            self.write("balances", self.sender, balance - amount)
            self.call(self.read("log"), "add_message", self.sender, amount, "CashOut")

    def balance_of(self, account: str) -> int:
        """The deposit credited to ``account``."""
        return int(self.read("balances", account))


class KingOfTheHill(Honeypot):
    """Inheritance disorder: whoever outbids the jackpot becomes ``owner`` and may take it.

    The ``owner`` the bidder becomes is the child's variable; the
    ``only_owner`` check in the parent reads the parent's, the creator.
    """

    layout: ClassVar[tuple[str, ...]] = ("owner", "king", "jackpot")

    def receive(self) -> None:
        if self.value > self.read("jackpot"):
            self.write("king", self.sender)
        self.write("jackpot", self.read("jackpot") + self.value)

    def owner(self) -> str:
        """The ``owner`` the source declares public: the last highest bidder."""
        return str(self.read("king"))

    def take_all(self) -> None:
        """Take the jackpot; only the parent's owner passes the check."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.write("jackpot", 0)
        self.call(self.sender, None, value=self.ether_balance())


class GuessNumber(Honeypot):
    """Uninitialised storage struct: guess the number in storage and win the balance.

    The number is "private", but storage is public, so the reader reads it.
    Recording the guess in an uninitialised struct writes the player's
    address over slot 0, the number, before it is compared.

    Parameters
    ----------
    number : int
        The secret, between 1 and 10.
    minimum : int
        The least bet.
    """

    layout: ClassVar[tuple[str, ...]] = ("number", "last_played", "minimum", "owner")

    def constructor(self, number: int = 7, minimum: int = 100) -> None:
        self.require(type(number) is int and 1 <= number <= 10, "number must be in 1..10")
        self.write("number", number)
        self.write("minimum", minimum)
        super().constructor()

    def guess(self, number: int) -> None:
        """Pay the whole balance for the right number."""
        self.require(self.value >= self.read("minimum") and number <= 10, "bad bet")
        self.write_slot(0, self.sender)  # guessHistory.player: slot 0 is the number.
        self.write_slot(1, number)  # guessHistory.number: slot 1 is last_played.
        # The source's `if (_number == randomNumber) msg.sender.transfer(this.balance)`
        # compares with the address now in slot 0, so the prize is always 0.
        prize = self.ether_balance() if number == self.read("number") else 0
        self.call(self.sender, None, value=prize)
        self.write("last_played", self.timestamp)


class ForTest(Honeypot):
    """Type deduction overflow: send more than ``threshold`` and get twice it back.

    The loop that computes the payout runs on a ``uint8`` counter, so the
    doubled counter wraps to 0 at 128 and the loop stops with a payout of 254.

    Parameters
    ----------
    threshold : int
        The least deposit that is doubled.
    """

    layout: ClassVar[tuple[str, ...]] = ("owner", "threshold")

    def constructor(self, threshold: int = 1_000) -> None:
        super().constructor()
        self.write("threshold", threshold)

    def test(self) -> None:
        """Pay back what the loop computes for a deposit above ``threshold``."""
        if self.value > self.read("threshold"):
            multi = payout = i = 0
            while i < 2 * self.value:
                multi = i * 2 % 256  # i is a uint8, so i * 2 wraps too.
                if multi < payout:
                    break
                payout = multi
                i = (i + 1) % 256
            self.call(self.sender, None, value=payout)


class DividendDistributor(Honeypot):
    """Skipped empty string literal: invest, and divest whenever you like.

    ``divest`` calls ``loggedTransfer(amount, "", msg.sender, owner)``. The
    old compiler dropped the empty string, so ``msg.sender`` became the
    message and the owner the recipient.
    """

    layout: ClassVar[tuple[str, ...]] = ("owner", "investments")

    def invest(self) -> None:
        """Record an investment."""
        self.require(self.value > 0, "invest something")
        held = self.read("investments", self.sender)
        self.write("investments", self.sender, held + self.value)

    def divest(self, amount: int) -> None:
        """Withdraw ``amount`` of the caller's investment."""
        held = self.read("investments", self.sender)
        self.require(type(amount) is int and 0 < amount <= held, "nothing to divest")
        self.write("investments", self.sender, held - amount)
        # The source reads _logged_transfer(amount, "", self.sender, owner).
        self._logged_transfer(amount, self.sender, self.read("owner"), 0)

    def _logged_transfer(self, amount: int, message: Any, target: str, owner: Any) -> None:
        self.call(target, None, value=amount)
        self.emit("Transfer", amount=amount, message=message, target=target, owner=owner)

    def investment_of(self, account: str) -> int:
        """What ``account`` has invested."""
        return int(self.read("investments", account))
