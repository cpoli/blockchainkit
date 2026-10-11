"""Proposer-builder separation and MEV-Boost (2022).

Extracting the value of transaction ordering takes searchers, private order
flow and fast infrastructure. A validator that has them earns more per unit
of stake than one that does not, and so attracts more stake: MEV pushes
proof of stake toward centralization.

Proposer-builder separation splits the roles. Specialized *builders*
assemble whole blocks and bid for the right to have theirs proposed; the
proposer, any validator, simply signs the highest bid. Competition between
builders hands the proposer nearly all the value of the block, so a solo
validator earns as much per slot as a sophisticated one. Flashbots'
MEV-Boost, launched with Ethereum's move to proof of stake in September
2022, runs this auction outside the protocol through trusted relays.
"""

from collections.abc import Collection, Mapping
from random import Random
from types import MappingProxyType

from blockchainkit._validation import integer, positive, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.consensus.systems.pos import StakeSampler
from blockchainkit.economics.core.base import PBSRun
from blockchainkit.economics.systems.auctions import second_price_auction


def simulate_pbs(
    stakes: Mapping[str, int],
    *,
    sophisticated: Collection[str],
    builders: Mapping[str, float],
    slots: int,
    fees: float = 1.0,
    mev: float = 1.0,
    separated: bool = True,
    seed: int = 0,
) -> PBSRun:
    """Total revenue of each validator over ``slots`` slots, with or without a builder market.

    Each slot, :class:`~blockchainkit.consensus.systems.pos.StakeSampler`
    picks the proposer by stake. The block holds ``fees`` in ordinary fees
    and an exponentially distributed MEV opportunity with mean ``mev``.
    Without separation, a proposer earns the fees, plus the MEV only if it
    is ``sophisticated``. With separation, each builder ``b`` values the
    block at ``fees + skill_b * MEV`` and the builders bid in a
    second-price auction, Vickrey's, in which bidding one's value is
    dominant; the proposer earns the price, or what it would build itself if
    that is more.

    Parameters
    ----------
    stakes : Mapping
        Each validator's stake.
    sophisticated : collection of str
        Validators able to extract MEV themselves.
    builders : Mapping
        Each builder's skill: the fraction of the MEV it captures, in [0, 1].
    slots : int
        Slots to simulate.
    fees : float
        Ordinary fees per block.
    mev : float
        Mean MEV per block.
    separated : bool
        Whether proposers sell their blocks to builders.
    seed : int
        Seeds both the proposer choice and the MEV.

    Returns
    -------
    PBSRun

    Examples
    --------
    >>> from blockchainkit.economics import simulate_pbs
    >>> options = dict(sophisticated={"pro"}, builders={"b1": 1.0, "b2": 0.9}, slots=100)
    >>> alone = simulate_pbs({"pro": 10, "solo": 10}, separated=False, **options)
    >>> boosted = simulate_pbs({"pro": 10, "solo": 10}, **options)
    >>> alone.revenue["solo"] < boosted.revenue["solo"]
    True
    >>> alone.revenue["pro"] == boosted.revenue["pro"]
    True
    """
    sampler = StakeSampler(stakes, seed=seed)
    unknown = set(sophisticated) - set(stakes)
    if unknown:
        raise ValueError(f"unknown validators: {sorted(unknown)}")
    if separated and len(builders) < 2:
        raise ValueError("a builder market needs at least two builders")
    for skill in builders.values():
        probability(skill, "skill")
    integer(slots, "slots", 1)
    positive(fees, "fees")
    positive(mev, "mev")
    check_seed(seed)
    rng = Random(seed)
    revenue = dict.fromkeys(stakes, 0.0)
    proposed = dict.fromkeys(stakes, 0)
    for _ in range(slots):
        proposer = sampler.choose()
        value = rng.expovariate(1 / mev)
        own = fees + (value if proposer in sophisticated else 0.0)
        if separated:
            bids = {name: fees + skill * value for name, skill in builders.items()}
            own = max(own, second_price_auction(bids).price)
        revenue[proposer] += own
        proposed[proposer] += 1
    return PBSRun(
        separated,
        MappingProxyType(revenue),
        MappingProxyType(dict(stakes)),
        MappingProxyType(proposed),
    )
