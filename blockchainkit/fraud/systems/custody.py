"""Custodians: Mt. Gox and the malleability excuse (2014), and FTX's commingled funds (2022).

An exchange that holds its customers' coins is a bank without a regulator:
nothing on chain shows what it owes, so it can lose or lend the deposits
and keep paying withdrawals until too many arrive at once.

In February 2014 Mt. Gox halted withdrawals and blamed transaction
malleability: an attacker could change a withdrawal's txid in flight, the
exchange would not find its txid on chain, and it would pay again
(:func:`reissue_missing`). Decker and Wattenhofer found too few malleated
transactions to explain the losses. In November 2022 FTX, then the third
largest exchange, could not meet withdrawals because customer deposits had
been passed to its affiliated trading firm, Alameda Research
(:class:`Custodian`).
"""

from collections.abc import Sequence

from blockchainkit.contracts.systems.world import Contract
from blockchainkit.structures.systems.transaction import Transaction

TRACKING = ("txid", "unsigned_id")
"""How an exchange can recognize its own withdrawals on chain."""


def reissue_missing(
    sent: Sequence[Transaction], confirmed: Sequence[Transaction], *, by: str = "txid"
) -> tuple[Transaction, ...]:
    """The withdrawals an exchange pays again because it cannot find them on chain.

    Parameters
    ----------
    sent : sequence of Transaction
        The withdrawals the exchange signed and broadcast.
    confirmed : sequence of Transaction
        What the chain confirmed: some may be malleated copies, with the
        same payment under a different txid.
    by : str
        ``"txid"``, as Mt. Gox did, or ``"unsigned_id"``, an identifier
        that malleation cannot change (segregated witness's txid).

    Returns
    -------
    tuple of Transaction
        Every withdrawal whose identifier is not among the confirmed ones.
    """
    if by not in TRACKING:
        raise ValueError(f"by must be one of {TRACKING}")
    seen = {getattr(tx, by) for tx in confirmed}
    return tuple(tx for tx in sent if getattr(tx, by) not in seen)


class Custodian(Contract):
    """An exchange holding customer deposits, with a credit line to an affiliate.

    Customers deposit and withdraw ether against balances in the exchange's
    own books. The operator may lend up to ``credit_line`` of the deposits
    to ``affiliate``: the commingling that sank FTX. The books still show
    every balance, so withdrawals succeed until the reserves run out.

    Parameters
    ----------
    affiliate : str
        The account the operator may lend customer funds to.
    credit_line : int
        The most it may lend.
    """

    layout = ("operator", "affiliate", "credit_line", "balances", "liabilities", "lent")

    def constructor(self, affiliate: str = "", credit_line: int = 0) -> None:
        self.require(type(credit_line) is int and credit_line >= 0, "credit line")
        self.write("operator", self.sender)
        self.write("affiliate", affiliate)
        self.write("credit_line", credit_line)

    def deposit(self) -> None:
        """Credit the ether sent to the caller's balance."""
        self.require(self.value > 0, "deposit something")
        self.write("balances", self.sender, self.read("balances", self.sender) + self.value)
        self.write("liabilities", self.read("liabilities") + self.value)

    def withdraw(self, amount: int) -> None:
        """Pay ``amount`` of the caller's balance, if the reserves still hold it."""
        balance = self.read("balances", self.sender)
        self.require(type(amount) is int and 0 < amount <= balance, "insufficient balance")
        self.require(self.ether_balance() >= amount, "withdrawals paused")
        self.write("balances", self.sender, balance - amount)
        self.write("liabilities", self.read("liabilities") - amount)
        self.call(self.sender, None, value=amount)

    def lend_to_affiliate(self, amount: int) -> None:
        """Move ``amount`` of customer deposits to the affiliate; operator only."""
        self.require(self.sender == self.read("operator"), "only the operator")
        lent = self.read("lent")
        self.require(type(amount) is int and amount > 0, "amount must be positive")
        self.require(lent + amount <= self.read("credit_line"), "credit line exceeded")
        self.write("lent", lent + amount)
        self.call(self.read("affiliate"), None, value=amount)

    def repay(self) -> None:
        """Return lent funds with the ether sent; anyone may repay."""
        self.write("lent", max(self.read("lent") - self.value, 0))

    def balance_of(self, customer: str) -> int:
        """What the exchange's books say it owes ``customer``."""
        return int(self.read("balances", customer))

    def balances(self) -> dict[str, int]:
        """Every customer balance in the books: the input to a proof of liabilities."""
        return {str(customer): int(amount) for customer, amount in self.entries("balances").items()}

    def liabilities(self) -> int:
        """Total owed to customers."""
        return int(self.read("liabilities"))

    def reserves(self) -> int:
        """Ether actually held: what a proof of reserves shows."""
        return self.ether_balance()

    def invariant(self) -> bool:
        return bool(self.read("liabilities") == sum(self.entries("balances").values()))
