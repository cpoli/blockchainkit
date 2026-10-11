"""Result containers for blockchainkit.fraud."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PonziRun:
    """A Ponzi scheme simulated period by period, up to its collapse.

    Attributes
    ----------
    deposits : tuple of float
        New money invested in each period.
    paid : tuple of float
        Money paid out to investors in each period.
    cash : tuple of float
        Money the scheme holds at the end of each period.
    owed : tuple of float
        What the scheme owes its investors at the end of each period.
    collapse : int or None
        The first period whose payouts it could not meet; None if it survived.
    """

    deposits: tuple[float, ...]
    paid: tuple[float, ...]
    cash: tuple[float, ...]
    owed: tuple[float, ...]
    collapse: int | None

    @property
    def survived(self) -> bool:
        """True if every payout was met."""
        return self.collapse is None

    @property
    def raised(self) -> float:
        """Total money invested."""
        return float(sum(self.deposits))

    @property
    def repaid(self) -> float:
        """Total money paid back to investors."""
        return float(sum(self.paid))


@dataclass(frozen=True)
class Flow:
    """A transfer of ether between two accounts, as a block explorer lists it.

    Attributes
    ----------
    sender, recipient : str
        The paying and the paid account.
    amount : int
        Ether moved.
    transaction : int
        Index of the transaction it belongs to, in the order given.
    """

    sender: str
    recipient: str
    amount: int
    transaction: int


@dataclass(frozen=True)
class PonziFeatures:
    """How a contract's money moved, measured as Bartoletti et al. classify Ponzi schemes.

    Attributes
    ----------
    investors : int
        Accounts that paid the contract.
    in_profit : int
        Investors who got back more than they paid in.
    paid_from_deposits : float
        Fraction of the ether paid to investors that left in the same
        transaction as a deposit by another investor.
    owner_share : float
        Fraction of the money paid out that went to the contract's owner.
    """

    investors: int
    in_profit: int
    paid_from_deposits: float
    owner_share: float

    @property
    def profit_fraction(self) -> float:
        """Fraction of investors in profit; 0 if there are none."""
        return self.in_profit / self.investors if self.investors else 0.0

    @property
    def looks_like_ponzi(self) -> bool:
        """Most payouts come straight from newer deposits, and most investors lose."""
        return self.paid_from_deposits >= 0.9 and self.profit_fraction < 0.5


@dataclass(frozen=True)
class BenfordTest:
    """A first-digit test of a data set against Benford's law.

    Attributes
    ----------
    counts : tuple of int
        How many values start with each digit 1 to 9.
    expected : tuple of float
        Benford's probability of each first digit.
    chi_square : float
        Pearson's statistic, with 8 degrees of freedom.
    p_value : float
        Chance of a statistic at least this large if the data follow the law.
    mad : float
        Mean absolute deviation between observed and expected proportions,
        Nigrini's measure of conformity, which does not grow with the sample.
    """

    counts: tuple[int, ...]
    expected: tuple[float, ...]
    chi_square: float
    p_value: float
    mad: float

    @property
    def n(self) -> int:
        """Number of values tested."""
        return sum(self.counts)

    @property
    def proportions(self) -> tuple[float, ...]:
        """Observed proportion of each first digit."""
        return tuple(count / self.n for count in self.counts)

    @property
    def conformity(self) -> str:
        """Nigrini's verdict on the mean absolute deviation.

        ``"close"`` up to 0.006, ``"acceptable"`` up to 0.012, ``"marginal"``
        up to 0.015, and ``"nonconformity"`` above.
        """
        for bound, verdict in ((0.006, "close"), (0.012, "acceptable"), (0.015, "marginal")):
            if self.mad <= bound:
                return verdict
        return "nonconformity"


@dataclass(frozen=True)
class SumProofStep:
    """One sibling on the path from a Merkle-sum-tree leaf to the root.

    Attributes
    ----------
    side : str
        ``"left"`` or ``"right"``: where the sibling sits.
    digest : bytes
        The sibling's hash.
    amount : int
        The sum of the balances below the sibling.
    """

    side: str
    digest: bytes
    amount: int


@dataclass(frozen=True)
class SumProof:
    """A customer's proof of inclusion in a Merkle sum tree.

    Attributes
    ----------
    index : int
        Position of the customer's leaf.
    steps : tuple of SumProofStep
        Siblings from the leaf up to the root.
    """

    index: int
    steps: tuple[SumProofStep, ...]


@dataclass(frozen=True)
class AuditResult:
    """Customers checking their inclusion proofs against a published liability tree.

    Attributes
    ----------
    checked : tuple of str
        Customers who asked for their proof.
    complaints : tuple of str
        Checking customers whose balance was missing or wrong.
    """

    checked: tuple[str, ...]
    complaints: tuple[str, ...]

    @property
    def caught(self) -> bool:
        """True if at least one customer found the cheat."""
        return bool(self.complaints)


@dataclass(frozen=True)
class BitRangeProof:
    """A proof that a Pedersen commitment holds a value in ``[0, 2**bits)``.

    Attributes
    ----------
    bit_commitments : tuple of int
        A commitment to each bit, least significant first.
    bit_proofs : tuple of tuple of int
        For each bit, an OR proof ``(c0, c1, z0, z1)`` that it holds 0 or 1.
    """

    bit_commitments: tuple[int, ...]
    bit_proofs: tuple[tuple[int, int, int, int], ...]

    @property
    def bits(self) -> int:
        """Number of bits, so the proven range is ``[0, 2**bits)``."""
        return len(self.bit_commitments)


@dataclass(frozen=True)
class SolvencyProof:
    """An exchange's proof that its assets cover its liabilities, revealing neither.

    Attributes
    ----------
    asset_commitments : tuple of int
        One commitment per address of the anonymity set: to its public
        balance if the exchange owns it, to 0 otherwise.
    asset_proofs : tuple of tuple of int
        For each, an OR proof that it holds 0 or that address's balance.
    liability_commitments : tuple of int
        One commitment per customer balance.
    liability_proofs : tuple of BitRangeProof
        For each, a proof that the balance is not negative.
    surplus_proof : BitRangeProof
        A proof that assets minus liabilities is not negative.
    """

    asset_commitments: tuple[int, ...]
    asset_proofs: tuple[tuple[int, int, int, int], ...]
    liability_commitments: tuple[int, ...]
    liability_proofs: tuple[BitRangeProof, ...]
    surplus_proof: BitRangeProof


@dataclass(frozen=True)
class MarketRun:
    """A daily price series with some days of suspicious trading.

    Attributes
    ----------
    prices : tuple of float
        Closing price of each day, starting with the opening price.
    volumes : tuple of float
        Volume bought by the suspicious trader each day.
    flagged : tuple of int
        Days on which the suspicious trader bought.
    """

    prices: tuple[float, ...]
    volumes: tuple[float, ...]
    flagged: tuple[int, ...]


@dataclass(frozen=True)
class PumpRun:
    """A pump-and-dump on a constant-product market, hour by hour.

    Attributes
    ----------
    prices : tuple of float
        Closing price of the coin each hour, in the quote currency.
    volumes : tuple of float
        Quote currency traded each hour.
    pump_hour : int
        The hour the pump was announced.
    organizer_profit : float
        What the organizers made, in the quote currency.
    participant_profits : tuple of float
        What each participant made, in the order they bought.
    """

    prices: tuple[float, ...]
    volumes: tuple[float, ...]
    pump_hour: int
    organizer_profit: float
    participant_profits: tuple[float, ...]

    @property
    def losing_participants(self) -> int:
        """Participants who lost money."""
        return sum(profit < 0 for profit in self.participant_profits)


@dataclass(frozen=True)
class Trade:
    """One sale of a non-fungible token.

    Attributes
    ----------
    token : int
        The token sold.
    seller, buyer : str
        The two sides.
    price : float
        What the buyer paid.
    """

    token: int
    seller: str
    buyer: str
    price: float


@dataclass(frozen=True)
class TradeHistory:
    """A market's sales, with the ground truth of which ones were wash trades.

    Attributes
    ----------
    trades : tuple of Trade
        Every sale, in order.
    wash : frozenset of int
        Indices of the wash trades.
    """

    trades: tuple[Trade, ...]
    wash: frozenset[int]


@dataclass(frozen=True)
class WashReport:
    """Trades flagged as wash trades, and the rings of accounts behind them.

    Attributes
    ----------
    suspicious : tuple of int
        Indices of the flagged trades.
    rings : tuple of frozenset of str
        Groups of accounts that traded tokens among themselves in a cycle.
    volume_share : float
        Fraction of the total traded value that the flagged trades account for.
    """

    suspicious: tuple[int, ...]
    rings: tuple[frozenset[str], ...]
    volume_share: float


@dataclass(frozen=True)
class LookalikeAddress:
    """An address ground out to resemble a target address.

    Attributes
    ----------
    address : str
        The look-alike address.
    target : str
        The address it imitates.
    trials : int
        Candidate addresses generated to find it.
    matched : int
        Hex characters matched at the start plus at the end.
    """

    address: str
    target: str
    trials: int
    matched: int
