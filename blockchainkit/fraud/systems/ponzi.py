"""Ponzi schemes: Ponzi (1920), Ethereum's Ponzi contracts (2017), and BitConnect (2018).

A Ponzi scheme pays its early investors with the money of later ones. It
survives only while new deposits grow at least as fast as the returns it
promised, and since no population grows forever, it always collapses,
leaving the last investors with the losses.

:func:`simulate_ponzi` is Ponzi's own scheme, which promised 50% in 45
days; :func:`simulate_lending_ponzi` is a "lending platform" in the style of
BitConnect, which promised a daily compounding interest and paid referral
commissions down several levels (:func:`referral_commissions`).
:class:`ChainPonzi` is a chain-shaped Ponzi contract, the commonest kind
that Bartoletti et al. found on Ethereum, and :func:`ponzi_features`
measures, from the transfers a block explorer lists, how its money moves.
"""

from collections.abc import Iterable, Mapping, Sequence

from blockchainkit._validation import integer, probability
from blockchainkit.contracts.core.base import Receipt
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.fraud.core.base import Flow, PonziFeatures, PonziRun


def _amounts(values: Sequence[float], name: str) -> tuple[float, ...]:
    amounts = tuple(values)
    for amount in amounts:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError(f"{name} must be real numbers")
        if not 0 <= amount < float("inf"):
            raise ValueError(f"{name} must be non-negative and finite")
    return amounts


def _rate(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    if not 0 <= value < float("inf"):
        raise ValueError(f"{name} must be non-negative and finite")


def breakeven_growth(promised_return: float, term: int = 1, skim: float = 0.0) -> float:
    """The growth rate of new deposits per period that a Ponzi scheme needs to pay its promises.

    A deposit :math:`D` made ``term`` periods ago is owed :math:`(1 + r) D`
    today and is paid from today's deposits, of which the operator keeps a
    fraction :math:`s`. Deposits growing by :math:`g` per period cover it
    exactly when :math:`(1 - s)(1 + g)^\\tau = 1 + r`.

    Examples
    --------
    >>> from blockchainkit.fraud import breakeven_growth
    >>> breakeven_growth(0.5)
    0.5
    """
    _rate(promised_return, "promised_return")
    integer(term, "term", 1)
    probability(skim, "skim")
    if skim == 1:
        raise ValueError("an operator who keeps everything can pay nothing")
    return float(((1 + promised_return) / (1 - skim)) ** (1 / term) - 1)


def simulate_ponzi(
    deposits: Sequence[float], *, promised_return: float = 0.5, term: int = 1, skim: float = 0.0
) -> PonziRun:
    """Run a scheme that repays each deposit with ``promised_return`` after ``term`` periods.

    Payouts come only from the cash held, which is the deposits less the
    operator's ``skim``. In the first period whose payout exceeds the cash,
    the scheme pays what it holds and collapses; the run stops there.

    Parameters
    ----------
    deposits : sequence of float
        New money invested in each period.
    promised_return : float
        Return promised on each deposit; Ponzi's was 50% in 45 days.
    term : int
        Periods until a deposit is repaid.
    skim : float
        Fraction of every deposit that the operator keeps, in [0, 1].

    Returns
    -------
    PonziRun

    Examples
    --------
    >>> from blockchainkit.fraud import simulate_ponzi
    >>> run = simulate_ponzi([100, 150, 225, 100])
    >>> run.collapse, run.paid
    (3, (0.0, 150.0, 225.0, 200.0))
    """
    amounts = _amounts(deposits, "deposits")
    _rate(promised_return, "promised_return")
    integer(term, "term", 1)
    probability(skim, "skim")
    cash = owed = 0.0
    paid, held, debts = [], [], []
    collapse = None
    for period, deposit in enumerate(amounts):
        cash += deposit * (1 - skim)
        owed += deposit * (1 + promised_return)
        due = (1 + promised_return) * amounts[period - term] if period >= term else 0.0
        payout = min(due, cash)
        cash -= payout
        owed -= payout
        paid.append(payout)
        held.append(cash)
        debts.append(owed)
        if payout < due:
            collapse = period
            break
    return PonziRun(amounts[: len(paid)], tuple(paid), tuple(held), tuple(debts), collapse)


def simulate_lending_ponzi(
    deposits: Sequence[float],
    *,
    daily_rate: float = 0.01,
    withdrawal_rate: float = 0.05,
    referral_rates: Sequence[float] = (0.07, 0.03, 0.02, 0.01),
) -> PonziRun:
    """Run a lending platform that credits interest daily and pays it from new deposits.

    Each day every balance grows by ``daily_rate``, the day's deposits are
    added, recruiters are paid ``sum(referral_rates)`` of the new deposits,
    and investors withdraw ``withdrawal_rate`` of their balances. Nothing is
    ever invested: when the cash cannot cover a day's commissions and
    withdrawals, the platform pays what it holds and collapses.

    Parameters
    ----------
    deposits : sequence of float
        New money deposited each day.
    daily_rate : float
        Interest credited per day; 1% a day is 3,778% a year.
    withdrawal_rate : float
        Fraction of their balances that investors withdraw each day.
    referral_rates : sequence of float
        Commission paid to the recruiter at each level above a new investor.

    Returns
    -------
    PonziRun
        ``owed`` holds the balances credited to investors.

    Examples
    --------
    >>> from blockchainkit.fraud import simulate_lending_ponzi
    >>> simulate_lending_ponzi([100] * 30).survived
    True
    >>> simulate_lending_ponzi([100] * 30 + [0] * 30).collapse
    45
    """
    amounts = _amounts(deposits, "deposits")
    _rate(daily_rate, "daily_rate")
    probability(withdrawal_rate, "withdrawal_rate")
    rates = _amounts(referral_rates, "referral_rates")
    if sum(rates) > 1:
        raise ValueError("referral commissions cannot exceed the deposits")
    cash = owed = 0.0
    paid, held, debts = [], [], []
    collapse = None
    for day, deposit in enumerate(amounts):
        owed = owed * (1 + daily_rate) + deposit
        cash += deposit
        commission = deposit * sum(rates)
        withdrawal = withdrawal_rate * owed
        payout = min(commission + withdrawal, cash)
        cash -= payout
        owed -= max(payout - commission, 0.0)
        paid.append(payout)
        held.append(cash)
        debts.append(owed)
        if payout < commission + withdrawal:
            collapse = day
            break
    return PonziRun(amounts[: len(paid)], tuple(paid), tuple(held), tuple(debts), collapse)


def referral_commissions(
    sponsors: Mapping[str, str | None],
    deposits: Mapping[str, float],
    rates: Sequence[float] = (0.07, 0.03, 0.02, 0.01),
) -> dict[str, float]:
    """Commissions each recruiter earns from the deposits of the investors below it.

    The recruiter of an investor earns ``rates[0]`` of its deposit, that
    recruiter's own recruiter ``rates[1]``, and so on up the tree.

    Parameters
    ----------
    sponsors : Mapping
        Each investor's recruiter; None, or absent, for the top of the tree.
    deposits : Mapping
        What each investor deposited.
    rates : sequence of float
        Commission rate at each level.

    Returns
    -------
    dict
        Commission earned by every recruiter who earned one.

    Examples
    --------
    >>> from blockchainkit.fraud import referral_commissions
    >>> referral_commissions({"b": "a", "c": "b"}, {"b": 100, "c": 100}, rates=(0.1, 0.05))
    {'a': 15.0, 'b': 10.0}
    """
    levels = _amounts(rates, "rates")
    _amounts(list(deposits.values()), "deposits")
    earned: dict[str, float] = {}
    for investor, amount in deposits.items():
        upline = sponsors.get(investor)
        for rate in levels:
            if upline is None:
                break
            earned[upline] = earned.get(upline, 0.0) + rate * amount
            upline = sponsors.get(upline)
    return earned


class ChainPonzi(Contract):
    """A chain-shaped Ponzi contract: each deposit pays the oldest unpaid investors.

    Every investor is owed ``multiplier_percent`` of its deposit, paid in
    order of arrival out of later deposits, and the owner takes
    ``fee_percent`` of each deposit. This is the scheme of contracts such as
    Doubler and Rubixi.

    Parameters
    ----------
    multiplier_percent : int
        What each investor is promised, as a percentage of its deposit.
    fee_percent : int
        The owner's cut of each deposit.
    """

    layout = ("owner", "multiplier", "fee", "investors", "owed", "count", "next")

    def constructor(self, multiplier_percent: int = 200, fee_percent: int = 10) -> None:
        self.require(type(multiplier_percent) is int and multiplier_percent > 100, "multiplier")
        self.require(type(fee_percent) is int and 0 <= fee_percent < 100, "fee")
        self.write("owner", self.sender)
        self.write("multiplier", multiplier_percent)
        self.write("fee", fee_percent)

    def receive(self) -> None:
        self.invest()

    def invest(self) -> None:
        """Join the queue with the ether sent, then pay whoever the balance now covers."""
        self.require(self.value > 0, "invest something")
        count = self.read("count")
        self.write("investors", count, self.sender)
        self.write("owed", count, self.value * self.read("multiplier") // 100)
        self.write("count", count + 1)
        fee = self.value * self.read("fee") // 100
        self.call(self.read("owner"), None, value=fee)
        payee = self.read("next")
        while payee <= count and self.ether_balance() >= self.read("owed", payee):
            self.call(self.read("investors", payee), None, value=self.read("owed", payee))
            payee += 1
        self.write("next", payee)

    def investors(self) -> int:
        """Investors who have joined."""
        return int(self.read("count"))

    def paid(self) -> int:
        """Investors who have been paid in full."""
        return int(self.read("next"))


def value_flows(receipts: Iterable[Receipt]) -> tuple[Flow, ...]:
    """Every transfer of ether that took effect, transaction by transaction.

    A block explorer's list of transactions and internal transactions: it
    skips failed transactions, failed calls and everything nested in them.
    """
    flows = []
    for index, receipt in enumerate(receipts):
        if not receipt.success:
            continue
        reverted_at: int | None = None
        for record in receipt.calls:
            if reverted_at is not None and record.depth > reverted_at:
                continue
            reverted_at = None if record.ok else record.depth
            if record.ok and record.value > 0 and record.kind != "delegatecall":
                flows.append(Flow(record.sender, record.context, record.value, index))
    return tuple(flows)


def ponzi_features(flows: Iterable[Flow], contract: str, owner: str | None = None) -> PonziFeatures:
    """Measure how money moves through ``contract`` (Bartoletti et al., 2017).

    Parameters
    ----------
    flows : iterable of Flow
        Transfers, such as those from :func:`value_flows`.
    contract : str
        The contract under suspicion.
    owner : str, optional
        Its owner, counted apart from the investors.

    Returns
    -------
    PonziFeatures
    """
    flows = tuple(flows)
    invested: dict[str, int] = {}
    received: dict[str, int] = {}
    depositors: dict[int, set[str]] = {}
    for flow in flows:
        if flow.recipient == contract and flow.sender != owner:
            invested[flow.sender] = invested.get(flow.sender, 0) + flow.amount
            depositors.setdefault(flow.transaction, set()).add(flow.sender)
        elif flow.sender == contract:
            received[flow.recipient] = received.get(flow.recipient, 0) + flow.amount
    payouts = [f for f in flows if f.sender == contract and f.recipient in invested]
    from_deposits = sum(
        f.amount for f in payouts if depositors.get(f.transaction, set()) - {f.recipient}
    )
    to_investors = sum(f.amount for f in payouts)
    paid_out = sum(received.values())
    return PonziFeatures(
        investors=len(invested),
        in_profit=sum(received.get(a, 0) > amount for a, amount in invested.items()),
        paid_from_deposits=from_deposits / to_investors if to_investors else 0.0,
        owner_share=received.get(owner, 0) / paid_out if owner is not None and paid_out else 0.0,
    )
