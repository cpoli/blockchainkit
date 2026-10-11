"""Collateralized lending: MakerDAO's Dai (2017) and oracle manipulation (bZx, 2020).

Dai is a stablecoin backed by ether locked in a contract. A user locks
collateral in a *vault* and draws newly minted Dai against it, as long as
the collateral is worth at least 150% of the debt at the price reported by
an oracle. When the price falls below that, anyone may *liquidate* the
vault: repay its debt and take collateral worth the debt plus a 13% penalty.
The overcollateralization is what keeps each Dai worth a dollar:

.. math::

   \\text{collateral} \\times \\text{price} \\ge 1.5 \\times \\text{debt}.

Every such lender trusts its price oracle. In February 2020, attackers
borrowed from the bZx protocol against collateral whose price came from a
decentralized exchange's spot price, after inflating that price within the
same transaction with a flash loan; the loan was never repaid. An oracle
that reads a price recorded *before* the transaction, such as a
time-weighted average, cannot be moved by a flash loan.
"""

from fractions import Fraction
from typing import ClassVar

from blockchainkit.contracts.systems.tokens import ERC20
from blockchainkit.contracts.systems.world import Contract

LIQUIDATION_RATIO = 150
"""Minimum collateral value, in percent of the debt (Single-Collateral Dai)."""

LIQUIDATION_PENALTY = 13
"""Extra collateral a liquidator receives, in percent of the debt (Single-Collateral Dai)."""


class PriceFeed(Contract):
    """An oracle whose owner reports a price: Dai per unit of ether."""

    layout = ("owner", "price")

    def constructor(self, price: int) -> None:
        self.write("owner", self.sender)
        self.write("price", price)

    def set_price(self, price: int) -> None:
        """Report a new price; owner only."""
        self.require(self.sender == self.read("owner"), "only the owner reports prices")
        self.require(type(price) is int and price > 0, "price must be a positive integer")
        self.write("price", price)

    def price(self) -> int:
        """The latest price."""
        return int(self.read("price"))


class Stablecoin(ERC20):
    """An ERC-20 token that only its minter, the vault engine, creates and destroys."""

    layout: ClassVar[tuple[str, ...]] = (*ERC20.layout, "minter")

    def constructor(self, supply: int = 0) -> None:
        super().constructor(supply)
        self.write("minter", self.sender)

    def mint(self, to: str, amount: int) -> None:
        """Create ``amount`` tokens for ``to``; minter only."""
        self.require(self.sender == self.read("minter"), "only the minter")
        self.write("total_supply", self.read("total_supply") + amount)
        self.write("balances", to, self.read("balances", to) + amount)

    def burn(self, owner: str, amount: int) -> None:
        """Destroy ``amount`` of ``owner``'s tokens; minter only."""
        self.require(self.sender == self.read("minter"), "only the minter")
        balance = self.read("balances", owner)
        self.require(balance >= amount, "insufficient balance")
        self.write("balances", owner, balance - amount)
        self.write("total_supply", self.read("total_supply") - amount)


class VaultEngine(Contract):
    """Single-Collateral Dai: ether vaults that mint a stablecoin.

    Parameters
    ----------
    feed : str
        The :class:`PriceFeed` reporting Dai per ether.
    ratio : int
        Liquidation ratio in percent.
    penalty : int
        Liquidation penalty in percent.
    """

    layout = ("feed", "dai", "ratio", "penalty", "collateral", "debt")

    def constructor(
        self, feed: str, ratio: int = LIQUIDATION_RATIO, penalty: int = LIQUIDATION_PENALTY
    ) -> None:
        self.write("feed", feed)
        self.write("ratio", ratio)
        self.write("penalty", penalty)
        self.write("dai", self.create(Stablecoin))

    def dai(self) -> str:
        """The address of the stablecoin."""
        return str(self.read("dai"))

    def collateral_of(self, owner: str) -> int:
        """Ether locked in ``owner``'s vault."""
        return int(self.read("collateral", owner))

    def debt_of(self, owner: str) -> int:
        """Dai drawn by ``owner``'s vault."""
        return int(self.read("debt", owner))

    def is_safe(self, owner: str) -> bool:
        """True if the vault's collateral covers its debt at the liquidation ratio."""
        price = self.call(self.read("feed"), "price")
        value = self.read("collateral", owner) * price * 100
        return bool(value >= self.read("debt", owner) * self.read("ratio"))

    def lock(self) -> None:
        """Add the ether sent to the caller's vault."""
        self.write("collateral", self.sender, self.read("collateral", self.sender) + self.value)

    def draw(self, amount: int) -> None:
        """Mint ``amount`` Dai to the caller against its vault, if it stays safe."""
        self.require(type(amount) is int and amount > 0, "amount must be positive")
        self.write("debt", self.sender, self.read("debt", self.sender) + amount)
        self.require(self.is_safe(self.sender), "vault would be undercollateralized")
        self.call(self.read("dai"), "mint", self.sender, amount)

    def wipe(self, amount: int) -> None:
        """Repay ``amount`` of the caller's debt, burning its Dai."""
        debt = self.read("debt", self.sender)
        self.require(type(amount) is int and 0 < amount <= debt, "amount exceeds the debt")
        self.call(self.read("dai"), "burn", self.sender, amount)
        self.write("debt", self.sender, debt - amount)

    def free(self, amount: int) -> None:
        """Withdraw ``amount`` ether from the caller's vault, if it stays safe."""
        held = self.read("collateral", self.sender)
        self.require(type(amount) is int and 0 < amount <= held, "amount exceeds the collateral")
        self.write("collateral", self.sender, held - amount)
        self.require(self.is_safe(self.sender), "vault would be undercollateralized")
        self.call(self.sender, None, value=amount)

    def liquidate(self, owner: str) -> int:
        """Repay an unsafe vault's debt with the caller's Dai and take collateral plus the penalty.

        Returns the ether seized; what is left stays in the owner's vault.
        """
        self.require(not self.is_safe(owner), "vault is safe")
        debt = self.read("debt", owner)
        price = self.call(self.read("feed"), "price")
        owed = -(-debt * (100 + self.read("penalty")) // (100 * price))  # Rounded up.
        seized = min(self.read("collateral", owner), owed)
        self.call(self.read("dai"), "burn", self.sender, debt)
        self.write("debt", owner, 0)
        self.write("collateral", owner, self.read("collateral", owner) - seized)
        self.call(self.sender, None, value=seized)
        self.emit("Liquidation", owner=owner, debt=debt, seized=seized)
        return int(seized)


class OracleLender(Contract):
    """Lends one token against another, valuing the collateral with a pool's price.

    The collateral must be the pool's token0 and the loan its token1.

    Parameters
    ----------
    collateral_token, debt_token : str
        The two tokens.
    pool : str
        A :class:`~blockchainkit.economics.systems.amm.ConstantProductPool`.
    delayed : bool
        False: value collateral at the pool's spot price, as bZx did. True:
        at its price before the current block.
    """

    layout = ("collateral_token", "debt_token", "pool", "delayed", "collateral", "debt")

    def constructor(
        self, collateral_token: str, debt_token: str, pool: str, delayed: bool = False
    ) -> None:
        self.write("collateral_token", collateral_token)
        self.write("debt_token", debt_token)
        self.write("pool", pool)
        self.write("delayed", int(delayed))

    def collateral_token(self) -> str:
        """The token accepted as collateral."""
        return str(self.read("collateral_token"))

    def debt_token(self) -> str:
        """The token lent."""
        return str(self.read("debt_token"))

    def collateral_price(self) -> Fraction:
        """The price the lender uses for one unit of collateral."""
        function = "previous_price" if self.read("delayed") else "price"
        return Fraction(self.call(self.read("pool"), function))

    def borrow(self, collateral: int, amount: int) -> None:
        """Deposit ``collateral`` and borrow ``amount``, if collateral covers 150% of the debt."""
        self.call(
            self.read("collateral_token"), "transfer_from", self.sender, self.address, collateral
        )
        held = self.read("collateral", self.sender) + collateral
        debt = self.read("debt", self.sender) + amount
        value = held * self.collateral_price() * 100
        self.require(value >= debt * LIQUIDATION_RATIO, "undercollateralized")
        self.write("collateral", self.sender, held)
        self.write("debt", self.sender, debt)
        self.call(self.read("debt_token"), "transfer", self.sender, amount)


class OracleAttacker(Contract):
    """Flash-borrows the debt token, pumps the collateral's spot price, and over-borrows.

    The attack of February 2020, reduced to its mechanism: the loan is never
    repaid, and the lender keeps collateral worth less than it lent.
    """

    layout = ("owner", "lender", "pool", "victim")

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def attack(self, lender: str, pool: str, victim: str, amount: int) -> None:
        """Flash-borrow ``amount`` from ``lender`` and exploit ``victim``'s oracle on ``pool``."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.write("lender", lender)
        self.write("pool", pool)
        self.write("victim", victim)
        self.call(lender, "flash_loan", amount)
        token = self.call(victim, "debt_token")
        self.call(
            token, "transfer", self.read("owner"), self.call(token, "balance_of", self.address)
        )

    def on_flash_loan(self, token: str, amount: int) -> None:
        """Buy the collateral with the loan, borrow against it at the inflated price, repay."""
        self.require(self.sender == self.read("lender"), "only the lender")
        pool, victim = self.read("pool"), self.read("victim")
        self.call(token, "approve", pool, amount)
        bought = self.call(pool, "swap", token, amount, 0)
        collateral_token = self.call(victim, "collateral_token")
        self.call(collateral_token, "approve", victim, bought)
        price = self.call(pool, "price")
        self.call(victim, "borrow", bought, int(bought * price * 100 // LIQUIDATION_RATIO))
        self.call(token, "transfer", self.read("lender"), amount)
