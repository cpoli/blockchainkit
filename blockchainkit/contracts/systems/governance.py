"""Flash loans and governance attacks: Beanstalk (2022).

A *flash loan* lends any amount with no collateral, provided it is repaid
before the transaction ends; otherwise the whole transaction, loan
included, reverts. Within one transaction, anyone can briefly be as rich as
the lender.

Beanstalk let token holders pass a proposal at once, by an
``emergencyCommit`` with two thirds of the voting power, one day after it
was submitted. In April 2022 an attacker submitted a proposal sending the
treasury to itself, waited the day, then in one transaction flash-borrowed
about a billion dollars of assets, converted them into voting power, voted,
committed the proposal, and repaid the loans, netting about 80 million.

The defense is to count votes at a *snapshot*: the balances at the block
the proposal was made, as Compound's governance token records them. No flash
loan can change the past.
"""

from typing import ClassVar

from blockchainkit.contracts.systems.tokens import ERC20
from blockchainkit.contracts.systems.world import Contract

PROPOSAL_DELAY = 86_400
"""Seconds between a proposal and its earliest emergency commit (one day)."""


class VotesToken(ERC20):
    """An ERC-20 token that also records every balance change by block, for snapshot votes."""

    layout: ClassVar[tuple[str, ...]] = (*ERC20.layout, "checkpoints")

    def constructor(self, supply: int) -> None:
        super().constructor(supply)
        self._checkpoint(self.sender)

    def _checkpoint(self, account: str) -> None:
        history = self.read("checkpoints", account) or ()
        entry = (self.block_number, self.read("balances", account))
        if history and history[-1][0] == self.block_number:
            history = history[:-1]
        self.write("checkpoints", account, (*history, entry))

    def _move(self, source: str, destination: str, amount: int) -> None:
        super()._move(source, destination, amount)
        self._checkpoint(source)
        self._checkpoint(destination)

    def balance_at(self, account: str, block: int) -> int:
        """``account``'s balance at the end of block ``block``."""
        balance = 0
        for number, value in self.read("checkpoints", account) or ():
            if number <= block:
                balance = value
        return int(balance)


class FlashLender(Contract):
    """Lends its tokens within one transaction; the borrower's callback must repay them."""

    layout = ("token",)

    def constructor(self, token: str) -> None:
        self.write("token", token)

    def flash_loan(self, amount: int) -> None:
        """Lend ``amount``, call the borrower's ``on_flash_loan``, and require the tokens back."""
        token = self.read("token")
        before = self.call(token, "balance_of", self.address)
        self.call(token, "transfer", self.sender, amount)
        self.call(self.sender, "on_flash_loan", token, amount)
        after = self.call(token, "balance_of", self.address)
        self.require(after >= before, "flash loan not repaid")


class Governance(Contract):
    """Token-weighted governance holding an ether treasury.

    Parameters
    ----------
    token : str
        The :class:`VotesToken` whose holders vote.
    snapshot : bool
        False: a vote weighs the voter's current balance, as Beanstalk's
        voting power was in effect. True: its balance at the end of the
        block before the proposal.
    """

    layout = ("token", "snapshot", "count", "proposals", "votes", "voted", "executed")

    def constructor(self, token: str, snapshot: bool = False) -> None:
        self.write("token", token)
        self.write("snapshot", int(snapshot))

    def receive(self) -> None:
        pass

    def propose(self, beneficiary: str, amount: int) -> int:
        """Propose paying ``amount`` of the treasury to ``beneficiary``; returns the proposal id."""
        pid = self.read("count")
        self.write("proposals", pid, (beneficiary, amount, self.block_number, self.timestamp))
        self.write("count", pid + 1)
        return int(pid)

    def vote(self, pid: int) -> int:
        """Vote for proposal ``pid`` with the caller's weight; returns the weight."""
        proposal = self.read("proposals", pid)
        self.require(proposal != 0, "no such proposal")
        self.require(not self.read("voted", pid, self.sender), "already voted")
        token = self.read("token")
        if self.read("snapshot"):
            weight = self.call(token, "balance_at", self.sender, proposal[2] - 1)
        else:
            weight = self.call(token, "balance_of", self.sender)
        self.write("voted", pid, self.sender, 1)
        self.write("votes", pid, self.read("votes", pid) + weight)
        return int(weight)

    def emergency_commit(self, pid: int) -> None:
        """Execute ``pid`` at once if a day has passed and two thirds of the supply voted for it."""
        proposal = self.read("proposals", pid)
        self.require(proposal != 0, "no such proposal")
        self.require(not self.read("executed", pid), "already executed")
        self.require(self.timestamp >= proposal[3] + PROPOSAL_DELAY, "too early")
        supply = self.call(self.read("token"), "total_supply")
        self.require(3 * self.read("votes", pid) >= 2 * supply, "below the two-thirds majority")
        self.write("executed", pid, 1)
        beneficiary, amount = proposal[0], proposal[1]
        self.call(beneficiary, None, value=amount)


class GovernanceAttacker(Contract):
    """Borrows voting power with a flash loan, passes its own proposal, and repays."""

    layout = ("owner", "lender", "governance", "pid")

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def receive(self) -> None:
        pass

    def attack(self, lender: str, governance: str, pid: int, amount: int) -> None:
        """Borrow ``amount`` tokens from ``lender`` and use them to pass proposal ``pid``."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.write("lender", lender)
        self.write("governance", governance)
        self.write("pid", pid)
        self.call(lender, "flash_loan", amount)
        self.call(self.read("owner"), None, value=self.ether_balance())

    def on_flash_loan(self, token: str, amount: int) -> None:
        """Vote, commit, and repay, all inside the loan."""
        lender = self.read("lender")
        self.require(self.sender == lender, "only the lender")
        governance, pid = self.read("governance"), self.read("pid")
        self.call(governance, "vote", pid)
        self.call(governance, "emergency_commit", pid)
        self.call(token, "transfer", lender, amount)
