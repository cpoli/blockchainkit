"""Capability-based security: authority by reference, not by identity (Miller, 1997-2006).

In an *object-capability* system, the only way to act on an object is to
hold a reference to it, and the only ways to get a reference are to be
given one, to create the object, or to have had it from the start. There
is no ambient authority to look up. Mark Miller's E language built
distributed programs, and money, on this rule: with the :class:`Mint` and
:class:`Purse` of Miller, Morningstar and Frantz (2000), paying someone
means handing them a purse holding exactly the payment, and nothing they do
with it can reach the rest of your funds.

Ambient authority is the root of the *confused deputy* (Hardy, 1988): a
program that acts with authority it holds for one party, on behalf of
another. Ethereum's ``tx.origin`` is ambient authority: a wallet that
trusts it pays out whenever its owner's transaction passes through, even
when the owner was lured into calling an attacker's contract.
:class:`OriginWallet` makes that mistake; :class:`SenderWallet` checks the
immediate caller instead.

Python cannot hide an object's attributes the way E does, so the purses
here keep the discipline by convention rather than by enforcement.
"""

from blockchainkit._validation import integer
from blockchainkit.contracts.systems.world import Contract


class Mint:
    """Creates a currency; holding the mint is the authority to create money in it.

    Examples
    --------
    >>> from blockchainkit.contracts import Mint
    >>> mint = Mint("carol-bucks")
    >>> alice = mint.make_purse(100)
    >>> payment = alice.sprout()
    >>> payment.deposit(10, alice)
    >>> alice.balance, payment.balance
    (90, 10)
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._balances: dict[Purse, int] = {}

    def make_purse(self, balance: int) -> "Purse":
        """A new purse holding ``balance`` of freshly created money."""
        integer(balance, "balance")
        purse = Purse(self)
        self._balances[purse] = balance
        return purse


class Purse:
    """A holder of money in one currency: whoever holds the purse can spend from it."""

    def __init__(self, mint: Mint) -> None:
        self._mint = mint

    @property
    def balance(self) -> int:
        """Money in the purse."""
        return self._mint._balances[self]

    @property
    def currency(self) -> str:
        """The name of the mint's currency."""
        return self._mint.name

    def sprout(self) -> "Purse":
        """A new, empty purse of the same currency, to pay with."""
        return self._mint.make_purse(0)

    def deposit(self, amount: int, source: "Purse") -> None:
        """Move ``amount`` from ``source`` into this purse.

        Holding ``source`` is the authority to take from it: no identity is
        checked. It must be a purse of the same mint, holding enough.
        """
        integer(amount, "amount")
        balances = self._mint._balances
        if not isinstance(source, Purse) or source not in balances:
            raise ValueError("source is not a purse of this currency")
        if balances[source] < amount:
            raise ValueError("insufficient funds in the source purse")
        balances[source] -= amount
        balances[self] += amount


class OriginWallet(Contract):
    """An ether wallet that authorizes withdrawals by ``tx.origin``: a confused deputy."""

    layout = ("owner",)

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def receive(self) -> None:
        pass

    def _authorized(self) -> bool:
        return bool(self.origin == self.read("owner"))

    def withdraw(self, to: str, amount: int) -> None:
        """Pay ``amount`` to ``to``, if the caller is authorized."""
        self.require(self._authorized(), "not the owner")
        self.call(to, None, value=amount)


class SenderWallet(OriginWallet):
    """The same wallet, authorizing by the immediate caller (``msg.sender``)."""

    def _authorized(self) -> bool:
        return bool(self.sender == self.read("owner"))


class AirdropPhisher(Contract):
    """Lures a wallet owner into calling it, then withdraws from the owner's wallet."""

    layout = ("thief",)

    def constructor(self) -> None:
        self.write("thief", self.sender)

    def claim_airdrop(self, wallet: str) -> None:
        """The bait: "claim your free tokens". The call it makes is the theft."""
        self.call(wallet, "withdraw", self.read("thief"), self.ether_balance(wallet))
