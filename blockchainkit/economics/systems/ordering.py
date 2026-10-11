"""Transaction ordering: priority gas auctions (2019) and sandwich attacks (2021).

Whoever orders the transactions of a block can profit from the order. Daian
et al., in *Flash Boys 2.0*, watched arbitrage bots on decentralized
exchanges compete for the same opportunity by repeatedly replacing their
pending transaction with one paying a higher fee, in a *priority gas
auction*. Every bot values the opportunity alike, so the bids climb until
almost all of its value goes to the block producer as fees: they called
this *miner extractable value*.

A *sandwich* exploits a pending swap on a constant-product pool. The
attacker buys just before the victim, which raises the price the victim
pays, then sells just after, at the price the victim's own trade raised.
The victim's slippage limit, the least output it accepts, caps the attack:
Zhou et al. showed how to choose the most profitable front-run the victim
still tolerates, and measured how often it happened on Uniswap. A trade too
small to move the price by more than the attacker's two fees is not worth
sandwiching.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.economics.core.base import GasAuction, SandwichResult
from blockchainkit.economics.systems.amm import FEE_BPS, amount_out

REPLACEMENT_BUMP = 10
"""Percent by which a replacement transaction must raise its fee (go-ethereum's default)."""


def priority_gas_auction(
    opportunity: int,
    bots: Sequence[str],
    *,
    start: int = 1,
    bump: int = REPLACEMENT_BUMP,
    seed: int = 0,
) -> GasAuction:
    """Simulate bots outbidding each other for one opportunity until no one gains by raising.

    At each step a bot other than the leader replaces its transaction with
    one paying at least ``bump`` percent more than the leading fee (and at
    least 1 more). No bot bids more than ``opportunity``, so the auction
    ends when the next raise would exceed it.

    Parameters
    ----------
    opportunity : int
        What the first transaction executed earns.
    bots : sequence of str
        At least two competitors.
    start : int
        The first bid.
    bump : int
        Minimum raise in percent.
    seed : int
        Picks which bot responds at each step.

    Returns
    -------
    GasAuction

    Examples
    --------
    >>> from blockchainkit.economics import priority_gas_auction
    >>> auction = priority_gas_auction(1_000, ["a", "b"])
    >>> auction.price > 900, auction.price + auction.profit
    (True, 1000)
    """
    integer(opportunity, "opportunity", 1)
    integer(start, "start", 1)
    integer(bump, "bump")
    check_seed(seed)
    names = sorted(set(bots))
    if len(names) < 2 or not all(isinstance(name, str) and name for name in names):
        raise ValueError("a gas auction needs at least two named bots")
    if start > opportunity:
        raise ValueError("start must not exceed the opportunity")
    rng = Random(seed)
    leader = rng.choice(names)
    bids = [(leader, start)]
    while True:
        fee = bids[-1][1]
        raised = max(fee + 1, -(-fee * (100 + bump) // 100))
        if raised > opportunity:
            break
        leader = rng.choice([name for name in names if name != leader])
        bids.append((leader, raised))
    winner, price = bids[-1]
    return GasAuction(tuple(bids), winner, price, opportunity - price)


def sandwich_profit(
    reserve_in: int, reserve_out: int, victim_in: int, front_run: int, *, fee_bps: int = FEE_BPS
) -> SandwichResult:
    """Outcome of front-running a swap of ``victim_in`` with ``front_run`` and selling right after.

    Parameters
    ----------
    reserve_in, reserve_out : int
        The pool's reserves of the token the victim sells and the token it buys.
    victim_in : int
        The victim's input.
    front_run : int
        The attacker's input, swapped first, in the same direction.
    fee_bps : int
        The pool's fee.

    Returns
    -------
    SandwichResult

    Examples
    --------
    >>> from blockchainkit.economics import sandwich_profit
    >>> sandwich_profit(10_000, 10_000, 1_000, 0).profit
    0
    """
    integer(front_run, "front_run")
    alone = amount_out(reserve_in, reserve_out, victim_in, fee_bps=fee_bps)
    bought = amount_out(reserve_in, reserve_out, front_run, fee_bps=fee_bps)
    reserve_in, reserve_out = reserve_in + front_run, reserve_out - bought
    victim_out = amount_out(reserve_in, reserve_out, victim_in, fee_bps=fee_bps)
    reserve_in, reserve_out = reserve_in + victim_in, reserve_out - victim_out
    sold = amount_out(reserve_out, reserve_in, bought, fee_bps=fee_bps) if bought else 0
    return SandwichResult(front_run, victim_out, alone, sold - front_run)


def sandwich_attack(
    reserve_in: int,
    reserve_out: int,
    victim_in: int,
    *,
    slippage_bps: int,
    fee_bps: int = FEE_BPS,
    budget: int | None = None,
) -> SandwichResult:
    """The most profitable sandwich that the victim's slippage limit allows.

    The victim accepts any output at least ``1 - slippage_bps / 10000`` of
    what it was quoted. Its output falls as the front-run grows, so a
    bisection finds the largest front-run (at most ``budget``) that still
    lets its swap execute; the profit, which first rises and then falls as
    the attacker's fees and price impact grow, is then maximized over the
    allowed range by a ternary search. If no front-run is profitable, the
    attacker abstains and the result has ``front_run == 0``.

    Examples
    --------
    >>> from blockchainkit.economics import sandwich_attack
    >>> tight = sandwich_attack(100_000, 100_000, 1_000, slippage_bps=10)
    >>> loose = sandwich_attack(100_000, 100_000, 1_000, slippage_bps=500)
    >>> tight.profit, loose.profit, loose.victim_loss
    (0, 34, 49)
    """
    integer(slippage_bps, "slippage_bps")
    if slippage_bps >= 10_000:
        raise ValueError("slippage_bps must be below 10,000")
    quoted = amount_out(reserve_in, reserve_out, victim_in, fee_bps=fee_bps)
    minimum = quoted * (10_000 - slippage_bps) // 10_000
    if budget is None:
        budget = 100 * reserve_in
    integer(budget, "budget")

    def outcome(front_run: int) -> SandwichResult:
        return sandwich_profit(reserve_in, reserve_out, victim_in, front_run, fee_bps=fee_bps)

    low, high = 0, budget
    while low < high:
        middle = (low + high + 1) // 2
        if outcome(middle).victim_out >= minimum:
            low = middle
        else:
            high = middle - 1
    left, right = 0, low
    while right - left > 2:
        third = (right - left) // 3
        if outcome(left + third).profit < outcome(right - third).profit:
            left += third + 1
        else:
            right -= third
    best = max((outcome(a) for a in (*range(left, right + 1), low)), key=lambda r: r.profit)
    return best if best.profit > 0 else outcome(0)
