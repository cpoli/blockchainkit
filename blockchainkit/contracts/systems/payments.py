"""Paying out safely: unchecked sends and unbounded loops (2016).

*King of the Ether* sold a throne: each claimant paid more than the last,
and the deposed king received the payment. The contract paid with ``send``,
which gives the recipient only 2,300 gas and returns False on failure
instead of reverting. A king whose wallet was itself a contract, with a
``receive`` that wrote storage, could not be paid in 2,300 gas; the contract
ignored the False and crowned the next king anyway, keeping the money.
Checking the result instead lets any king who refuses payment block the
throne forever. The fix is the *pull-payment* pattern: record what is owed
and let each recipient withdraw it.

*GovernMental* was a Ponzi game that paid its jackpot to the last investor
after 12 hours of silence, then cleared its list of creditors in a loop. By
April 2016 the list was so long that clearing it needed more gas than a
block allowed, so the payout could never execute. Any loop over a list that
users can grow is a denial of service waiting to happen.
"""

from blockchainkit.contracts.systems.world import Contract

COMMISSION_PERCENT = 1
"""King of the Ether's cut of each claim."""

GOVERNMENTAL_TIMEOUT = 43_200
"""Seconds without investment (12 hours) after which GovernMental pays its jackpot."""


class KingOfTheEther(Contract):
    """The 2016 throne game, paying the deposed king with an unchecked ``send``.

    Each claim must pay at least the current price; the old king receives
    the claim minus a 1% commission, and the price rises by half.
    """

    layout = ("king", "price", "owed")

    def constructor(self, price: int) -> None:
        self.write("king", self.sender)
        self.write("price", price)

    def king(self) -> str:
        """The current king."""
        return str(self.read("king"))

    def price(self) -> int:
        """What the next claim must pay at least."""
        return int(self.read("price"))

    def claim_throne(self) -> None:
        """Pay at least the price to become king; the old king is compensated."""
        self.require(self.value >= self.read("price"), "pay at least the price")
        deposed = self.read("king")
        self._pay(deposed, self.value * (100 - COMMISSION_PERCENT) // 100)
        self.write("king", self.sender)
        self.write("price", self.value * 3 // 2)
        self.emit("NewKing", king=self.sender, deposed=deposed)

    def _pay(self, recipient: str, amount: int) -> None:
        self.send(recipient, amount)  # The bug: a failed send is ignored.


class CheckedKingOfTheEther(KingOfTheEther):
    """Reverts the claim when paying the old king fails: a king refusing payment reigns forever."""

    def _pay(self, recipient: str, amount: int) -> None:
        self.require(self.send(recipient, amount), "payment to the deposed king failed")


class PullKingOfTheEther(KingOfTheEther):
    """Records what each deposed king is owed; they withdraw it themselves (pull payment)."""

    def _pay(self, recipient: str, amount: int) -> None:
        self.write("owed", recipient, self.read("owed", recipient) + amount)

    def owed(self, account: str) -> int:
        """Compensation waiting for ``account``."""
        return int(self.read("owed", account))

    def withdraw(self) -> None:
        """Send the caller what it is owed, with all the gas it needs."""
        amount = self.read("owed", self.sender)
        self.require(amount > 0, "nothing owed")
        self.write("owed", self.sender, 0)
        self.call(self.sender, None, value=amount)


class ContractWallet(Contract):
    """A wallet that is a contract, as Mist's were: its ``receive`` counts deposits in storage.

    Writing storage costs more than the 2,300-gas stipend of ``send``, so
    ``send`` to this wallet always fails.
    """

    layout = ("owner", "deposits")

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def receive(self) -> None:
        self.write("deposits", self.read("deposits") + 1)

    def forward(self, to: str, function: str, amount: int) -> None:
        """Call ``function`` on ``to`` with ``amount`` of the wallet's ether; owner only."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.call(to, function, value=amount)


class Usurper(Contract):
    """Claims a throne from a contract that refuses every payment, so it cannot be deposed."""

    layout = ()

    def claim(self, throne: str) -> None:
        """Claim ``throne`` with all the ether sent to this call."""
        self.call(throne, "claim_throne", value=self.value)

    def receive(self) -> None:
        self.require(False, "no refunds")


class GovernMental(Contract):
    """The 2016 Ponzi game: the last investor wins the jackpot after 12 quiet hours.

    Parameters
    ----------
    lazy_reset : bool
        False: the payout clears every creditor, one storage write each.
        True: it starts a new round instead, at a constant cost.
    """

    layout = ("creditors", "count", "last_investment", "round", "lazy_reset")

    def constructor(self, lazy_reset: bool = False) -> None:
        self.write("lazy_reset", int(lazy_reset))
        self.write("last_investment", self.timestamp)

    def creditors(self) -> int:
        """Investors in the current round."""
        return int(self.read("count"))

    def invest(self) -> None:
        """Join the round; the whole investment goes to the jackpot."""
        self.require(self.value > 0, "invest something")
        count = self.read("count")
        self.write("creditors", self.read("round"), count, self.sender)
        self.write("count", count + 1)
        self.write("last_investment", self.timestamp)

    def payout(self) -> None:
        """After 12 hours without investment, pay the jackpot to the last investor and reset."""
        self.require(
            self.timestamp >= self.read("last_investment") + GOVERNMENTAL_TIMEOUT, "too early"
        )
        count = self.read("count")
        self.require(count > 0, "no investors")
        current = self.read("round")
        winner = self.read("creditors", current, count - 1)
        if self.read("lazy_reset"):
            self.write("round", current + 1)
        else:
            for index in range(count):
                self.write("creditors", current, index, 0)
        self.write("count", 0)
        self.call(winner, None, value=self.ether_balance())
