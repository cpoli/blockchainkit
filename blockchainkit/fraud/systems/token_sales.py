"""ICO exit scams and the DAICO (2017-2018).

In an initial coin offering, a team sells tokens for ether to fund a
project that does not exist yet. Nothing stops it from taking the ether and
disappearing, an *exit scam*: in December 2017 the SEC's new Cyber Unit
froze the PlexCoin sale, whose promoters had promised a 1,354% return
within a month.

Buterin's DAICO (January 2018) puts the raised ether in a contract that
releases it to the team at a capped rate, the *tap*, and lets the
contributors vote to refund what is left. A team that vanishes then gets
away with only what the tap has released.
"""

from blockchainkit.contracts.systems.world import Contract


class TokenSale(Contract):
    """A token sale whose proceeds the team withdraws, freely or through a tap.

    Contributors receive one token per unit of ether. With ``tap = 0`` the
    team may withdraw everything at any time; with ``tap > 0`` (a DAICO) at
    most ``tap`` per second since deployment, and once contributors holding
    more than half of the tokens vote for it, the remaining ether is
    refunded in proportion to their contributions.

    Parameters
    ----------
    tap : int
        Ether per second the team may withdraw; 0 for no limit.
    """

    layout = (
        "team",
        "tap",
        "start",
        "withdrawn",
        "contributions",
        "raised",
        "votes",
        "voted",
        "refunding",
        "pool",
    )

    def constructor(self, tap: int = 0) -> None:
        self.require(type(tap) is int and tap >= 0, "tap must be a non-negative integer")
        self.write("team", self.sender)
        self.write("tap", tap)
        self.write("start", self.timestamp)

    def buy(self) -> None:
        """Contribute the ether sent, for as many tokens."""
        self.require(not self.read("refunding"), "the sale is refunding")
        self.require(self.value > 0, "contribute something")
        held = self.read("contributions", self.sender)
        self.write("contributions", self.sender, held + self.value)
        self.write("raised", self.read("raised") + self.value)

    def tokens_of(self, account: str) -> int:
        """Tokens held by ``account``."""
        return int(self.read("contributions", account))

    def available(self) -> int:
        """Ether the team may withdraw now."""
        if self.read("refunding"):
            return 0
        tap = self.read("tap")
        if not tap:
            return self.ether_balance()
        released = tap * (self.timestamp - self.read("start")) - self.read("withdrawn")
        return int(min(released, self.ether_balance()))

    def withdraw(self, amount: int) -> None:
        """Pay ``amount`` to the team; team only, within what the tap has released."""
        self.require(self.sender == self.read("team"), "only the team")
        self.require(type(amount) is int and 0 < amount <= self.available(), "above the tap")
        self.write("withdrawn", self.read("withdrawn") + amount)
        self.call(self.sender, None, value=amount)

    def vote_refund(self) -> None:
        """Vote, with all one's tokens, to stop the project and refund the rest."""
        self.require(self.read("tap") > 0, "this sale has no refund vote")
        held = self.read("contributions", self.sender)
        self.require(held > 0 and not self.read("voted", self.sender), "cannot vote")
        self.write("voted", self.sender, 1)
        votes = self.read("votes") + held
        self.write("votes", votes)
        if 2 * votes > self.read("raised") and not self.read("refunding"):
            self.write("refunding", 1)
            self.write("pool", self.ether_balance())

    def refund(self) -> None:
        """Take back one's share of the ether left when the refund passed."""
        self.require(self.read("refunding"), "no refund was voted")
        held = self.read("contributions", self.sender)
        self.require(held > 0, "nothing to refund")
        self.write("contributions", self.sender, 0)
        self.call(self.sender, None, value=held * self.read("pool") // self.read("raised"))
