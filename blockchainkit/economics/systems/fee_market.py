"""Transaction fee markets: first-price auctions and EIP-1559 (2021, analyzed by Roughgarden 2020).

Block space is scarce, so users bid for it. Bitcoin and, until 2021,
Ethereum sold it by a *first-price auction*: each user names a fee, the
producer includes the highest bids, and every user pays its own bid. No
bid is obviously right: a user who overbids overpays, one who underbids
waits, and the fee paid swings with every burst of demand.

EIP-1559 sets a *base fee* per unit of gas, adjusted after each block
toward a target of half the block's capacity,

.. math::

   b_{t+1} = b_t \\left(1 + \\frac{1}{8}\\,\\frac{g_t - g^*}{g^*}\\right),

which every included transaction pays and which is *burned*, plus a small
tip to the producer. Roughgarden showed that, outside sudden rises in
demand, bidding the base fee plus a tip is optimal for users, so that
fees become easy to set; that a myopic producer has no reason to deviate
from the protocol; and that off-chain deals between users and producers
cannot beat it, because the base fee goes to nobody.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.economics.core.base import FeeMarketRun, PendingTransaction

BASE_FEE_MAX_CHANGE_DENOMINATOR = 8
"""The base fee changes by at most 1/8 per block (EIP-1559)."""

ELASTICITY_MULTIPLIER = 2
"""A block may use up to twice the gas target (EIP-1559)."""

TRANSFER_GAS = 21_000
"""Gas used by each simulated transaction, a plain transfer."""


def next_base_fee(base_fee: int, gas_used: int, gas_target: int) -> int:
    """The base fee of the next block, computed exactly as the EIP-1559 specification does.

    Integer arithmetic rounds the change down, except that a block above
    target always raises the fee by at least 1.

    Examples
    --------
    >>> from blockchainkit.economics import next_base_fee
    >>> next_base_fee(1_000, 30_000_000, 15_000_000)  # A full block: +12.5%.
    1125
    >>> next_base_fee(1_000, 0, 15_000_000)  # An empty block: -12.5%.
    875
    """
    integer(base_fee, "base_fee")
    integer(gas_target, "gas_target", 1)
    integer(gas_used, "gas_used")
    if gas_used > ELASTICITY_MULTIPLIER * gas_target:
        raise ValueError("gas_used exceeds the block gas limit")
    if gas_used > gas_target:
        delta = base_fee * (gas_used - gas_target) // gas_target // BASE_FEE_MAX_CHANGE_DENOMINATOR
        return base_fee + max(delta, 1)
    delta = base_fee * (gas_target - gas_used) // gas_target // BASE_FEE_MAX_CHANGE_DENOMINATOR
    return base_fee - delta


def simulate_fee_market(
    arrivals: Sequence[int],
    *,
    mechanism: str = "eip1559",
    gas_target: int = 20 * TRANSFER_GAS,
    base_fee: int = 100,
    values: tuple[int, int] = (50, 500),
    tip: int = 2,
    shading: float = 0.8,
    patience: int = 20,
    seed: int = 0,
) -> FeeMarketRun:
    """Simulate a mempool and the blocks that empty it, one block per entry of ``arrivals``.

    Before block ``t``, ``arrivals[t]`` transfers join the mempool, each
    worth a value per gas drawn uniformly from ``values``. Transactions
    that waited ``patience`` blocks are abandoned.

    With ``"first-price"``, every user bids ``shading`` times its value; the
    producer fills a block of ``gas_target`` gas with the highest bids,
    each paying its own bid. With ``"eip1559"``, users set ``max_fee`` to
    their value and offer ``tip``; a transaction is eligible if its max fee
    covers the base fee, the producer fills up to twice the target by
    effective tip, each pays the base fee (burned) plus its effective tip
    (to the producer), and the base fee is updated by :func:`next_base_fee`.

    Parameters
    ----------
    arrivals : sequence of int
        New transactions before each block.
    mechanism : str
        ``"first-price"`` or ``"eip1559"``.
    gas_target : int
        Target gas per block; first-price blocks hold exactly this much.
    base_fee : int
        Initial base fee per gas.
    values : tuple of int
        Inclusive range of values per gas.
    tip : int
        Priority fee per gas offered under EIP-1559.
    shading : float
        Fraction of its value a first-price bidder bids.
    patience : int
        Blocks a transaction waits before its sender gives up.
    seed : int
        Simulation seed.

    Returns
    -------
    FeeMarketRun
    """
    if mechanism not in ("first-price", "eip1559"):
        raise ValueError('mechanism must be "first-price" or "eip1559"')
    for count in arrivals:
        integer(count, "arrivals")
    integer(gas_target, "gas_target", TRANSFER_GAS)
    integer(base_fee, "base_fee")
    low, high = values
    integer(low, "values")
    integer(high, "values", low)
    integer(tip, "tip")
    probability(shading, "shading")
    integer(patience, "patience", 1)
    check_seed(seed)
    rng = Random(seed)
    eip1559 = mechanism == "eip1559"
    limit = ELASTICITY_MULTIPLIER * gas_target if eip1559 else gas_target
    pool: list[PendingTransaction] = []
    base_fees, used_gas, burned, revenue, prices, waiting = [], [], [], [], [], []
    welfare = 0
    for block, count in enumerate(arrivals):
        for _ in range(count):
            value = rng.randint(low, high)
            if eip1559:
                pool.append(PendingTransaction(value, value, tip, block))
            else:
                pool.append(PendingTransaction(value, int(value * shading), 0, block))
        pool = [tx for tx in pool if block - tx.arrival < patience]
        fee = base_fee if eip1559 else 0
        if eip1559:
            eligible = [tx for tx in pool if tx.max_fee >= fee]
            eligible.sort(key=lambda tx: (-min(tx.priority_fee, tx.max_fee - fee), tx.arrival))
        else:
            eligible = sorted(pool, key=lambda tx: (-tx.max_fee, tx.arrival))
        included, gas = [], 0
        for tx in eligible:
            if gas + tx.gas > limit:
                break
            included.append(tx)
            gas += tx.gas
        chosen = {id(tx) for tx in included}
        pool = [tx for tx in pool if id(tx) not in chosen]
        if eip1559:
            paid = [fee + min(tx.priority_fee, tx.max_fee - fee) for tx in included]
        else:
            paid = [tx.max_fee for tx in included]
        base_fees.append(fee)
        used_gas.append(gas)
        burned.append(fee * gas)
        revenue.append(
            sum((price - fee) * tx.gas for price, tx in zip(paid, included, strict=True))
        )
        prices.append(sum(paid) / len(paid) if paid else 0.0)
        waiting.append(len(pool))
        welfare += sum(
            (tx.value - price) * tx.gas for price, tx in zip(paid, included, strict=True)
        )
        if eip1559:
            base_fee = next_base_fee(base_fee, gas, gas_target)
    return FeeMarketRun(
        mechanism,
        tuple(base_fees),
        tuple(used_gas),
        tuple(burned),
        tuple(revenue),
        tuple(prices),
        tuple(waiting),
        welfare,
    )
