"""Bitcoin without the block reward (Carlsten, Kalodner, Weinberg and Narayanan 2016).

Once the subsidy has run out, a block earns only the fees of the
transactions it includes. Fees arrive steadily while blocks arrive at
exponentially distributed intervals, so a block's reward is proportional to
the time since the last one: highly variable, and near zero right after a
block. Two instabilities follow.

*The mining gap.* Just after a block, the mempool is nearly empty and the
expected reward of the next block is less than the cost of the electricity
to find it, so rational miners pause until enough fees accumulate.

*Undercutting.* When the tip block claimed more fees than are left in the
mempool, a miner gains by forking it: it mines a competing block that
claims only part of those fees, leaving the rest unclaimed as a bribe for
whoever extends its block rather than the original.

A subsidy that is large next to the fees makes every block worth about the
same and removes both incentives, which is why Bitcoin's security budget
after the halvings is an open question.
"""

from random import Random

from blockchainkit._validation import integer, positive, probability
from blockchainkit._validation import seed as check_seed


def _amount(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    if not 0 <= value < float("inf"):
        raise ValueError(f"{name} must be non-negative and finite")


def simulate_block_rewards(
    subsidy: float, fee_rate: float, *, blocks: int, interval: float = 600.0, seed: int = 0
) -> tuple[float, ...]:
    """The reward of each of ``blocks`` blocks when each one claims every fee since the last.

    Block intervals are exponential with mean ``interval`` seconds, and fees
    arrive at ``fee_rate`` per second, so block ``i`` earns
    ``subsidy + fee_rate * interval_i``.

    Examples
    --------
    >>> from blockchainkit.economics import simulate_block_rewards
    >>> simulate_block_rewards(6.25, 0.0, blocks=3)
    (6.25, 6.25, 6.25)
    """
    _amount(subsidy, "subsidy")
    _amount(fee_rate, "fee_rate")
    integer(blocks, "blocks", 1)
    positive(interval, "interval")
    check_seed(seed)
    rng = Random(seed)
    return tuple(subsidy + fee_rate * rng.expovariate(1 / interval) for _ in range(blocks))


def mining_gap(subsidy: float, fee_rate: float, cost_per_block: float) -> float:
    """Seconds after a block before mining the next one pays for itself.

    A miner's expected income per second of hashing is proportional to the
    reward of the block it is working on, ``subsidy + fee_rate * t`` after
    ``t`` seconds, and its cost to ``cost_per_block``, what it spends per
    block it expects to find. It mines once the first reaches the second:
    after :math:`\\max(0, (c - S) / f)` seconds.

    Examples
    --------
    >>> from blockchainkit.economics import mining_gap
    >>> mining_gap(6.25, 0.001, 5.0), mining_gap(0.0, 0.001, 0.3)
    (0.0, 300.0)
    """
    _amount(subsidy, "subsidy")
    positive(fee_rate, "fee_rate")
    _amount(cost_per_block, "cost_per_block")
    return float(max(0.0, (cost_per_block - subsidy) / fee_rate))


def undercutting_payoffs(
    attacker_fraction: float,
    tip_fees: float,
    pending_fees: float,
    *,
    kept: float,
    subsidy: float = 0.0,
) -> dict[str, float]:
    """Expected income of extending the tip honestly, or of forking it and undercutting.

    The tip block claimed ``tip_fees``, and ``pending_fees`` are waiting in
    the mempool. Honest: the miner wins the next block with probability
    ``a`` (its hashrate share) and earns ``subsidy + pending_fees``.
    Undercut: it re-mines the tip's height, claiming a fraction ``kept`` of
    all the fees ``F = tip_fees + pending_fees`` and leaving the rest. Other
    miners, choosing the branch whose next block pays more, switch to it if
    ``(1 - kept) F > pending_fees``; the miner then needs only to find that
    one block, earning ``a (subsidy + kept F)``. Otherwise it must find two
    blocks in a row, earning ``a**2 (2 subsidy + F)``.

    Parameters
    ----------
    attacker_fraction : float
        The deviating miner's hashrate share.
    tip_fees : float
        Fees claimed by the current tip.
    pending_fees : float
        Fees waiting in the mempool.
    kept : float
        Fraction of all available fees the undercutting block claims, in [0, 1].
    subsidy : float
        New coins per block.

    Returns
    -------
    dict
        The expected income of ``"honest"`` and ``"undercut"``.

    Examples
    --------
    >>> from blockchainkit.economics import undercutting_payoffs
    >>> undercutting_payoffs(0.1, 10.0, 1.0, kept=0.5)
    {'honest': 0.1, 'undercut': 0.55}
    """
    probability(attacker_fraction, "attacker_fraction")
    _amount(tip_fees, "tip_fees")
    _amount(pending_fees, "pending_fees")
    probability(kept, "kept")
    _amount(subsidy, "subsidy")
    a, total = attacker_fraction, tip_fees + pending_fees
    honest = a * (subsidy + pending_fees)
    if (1 - kept) * total > pending_fees:
        undercut = a * (subsidy + kept * total)
    else:
        undercut = a * a * (2 * subsidy + total)
    return {"honest": float(honest), "undercut": float(undercut)}
