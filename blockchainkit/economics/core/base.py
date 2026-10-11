"""Result containers for blockchainkit.economics."""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class AuctionResult:
    """Outcome of a sealed-bid auction.

    Attributes
    ----------
    winner : str or None
        The highest bidder, ties broken by name; None if no bid met the reserve.
    price : float
        What the winner pays; 0 if nobody won.
    bids : Mapping
        Every bid, by bidder.
    """

    winner: str | None
    price: float
    bids: Mapping[str, float]

    def utility(self, bidder: str, value: float) -> float:
        """``bidder``'s gain if the item is worth ``value`` to it: value minus price if it won."""
        return value - self.price if bidder == self.winner else 0.0


@dataclass(frozen=True)
class OracleRound:
    """One round of a SchellingCoin oracle.

    Attributes
    ----------
    answer : float
        The median report, which the oracle publishes.
    rewarded : tuple of str
        Reporters between the lower and upper quartile, who earn the reward.
    penalized : tuple of str
        The others, who lose their deposit.
    payouts : Mapping
        Each reporter's gain or loss.
    """

    answer: float
    rewarded: tuple[str, ...]
    penalized: tuple[str, ...]
    payouts: Mapping[str, float]


@dataclass(frozen=True)
class AttackIncentive:
    """Expected income of a miner who mines honestly or attempts a double spend.

    Attributes
    ----------
    success_probability : float
        Chance that the attacker's private chain overtakes the honest one.
    honest : float
        Expected block rewards from mining honestly over the same blocks.
    attack : float
        Expected payment recovered plus block rewards kept by attacking.
    """

    success_probability: float
    honest: float
    attack: float

    @property
    def attack_pays(self) -> bool:
        """True if attacking earns strictly more than playing by the rules."""
        return self.attack > self.honest


@dataclass(frozen=True)
class PendingTransaction:
    """A transaction waiting in the mempool, with the fees its sender offers.

    Attributes
    ----------
    value : int
        What inclusion is worth to the sender, per unit of gas.
    max_fee : int
        The most the sender pays per unit of gas.
    priority_fee : int
        The tip offered to the block producer per unit of gas (EIP-1559 only).
    arrival : int
        The block at which it entered the mempool.
    gas : int
        Gas the transaction uses.
    """

    value: int
    max_fee: int
    priority_fee: int
    arrival: int
    gas: int = 21_000


@dataclass(frozen=True)
class FeeMarketRun:
    """A fee-market simulation, one entry per block.

    Attributes
    ----------
    mechanism : str
        ``"first-price"`` or ``"eip1559"``.
    base_fees : tuple of int
        The base fee in force for each block (all 0 for a first-price auction).
    gas_used : tuple of int
        Gas used by each block.
    burned : tuple of int
        Fees destroyed by each block.
    producer_revenue : tuple of int
        Fees paid to each block's producer.
    mean_price : tuple of float
        Mean fee per gas paid by the block's transactions (0 for an empty block).
    waiting : tuple of int
        Transactions left in the mempool after each block.
    welfare : int
        Total value minus total fees, over every included transaction.
    """

    mechanism: str
    base_fees: tuple[int, ...]
    gas_used: tuple[int, ...]
    burned: tuple[int, ...]
    producer_revenue: tuple[int, ...]
    mean_price: tuple[float, ...]
    waiting: tuple[int, ...]
    welfare: int


@dataclass(frozen=True)
class GasAuction:
    """A priority gas auction between bots competing for one opportunity.

    Attributes
    ----------
    bids : tuple of tuple
        Every ``(bot, fee)`` bid, in the order placed; each one outbids the last.
    winner : str
        The bot whose transaction is mined first.
    price : int
        Its fee, all of which goes to the block producer.
    profit : int
        The opportunity's value minus the price.
    """

    bids: tuple[tuple[str, int], ...]
    winner: str
    price: int
    profit: int


@dataclass(frozen=True)
class SandwichResult:
    """A sandwich attack on one swap in a constant-product pool.

    Attributes
    ----------
    front_run : int
        Input tokens the attacker swaps just before the victim.
    victim_out : int
        What the victim receives once sandwiched.
    victim_out_alone : int
        What the victim would have received without the attack.
    profit : int
        Input tokens the attacker ends with, minus ``front_run``.
    """

    front_run: int
    victim_out: int
    victim_out_alone: int
    profit: int

    @property
    def victim_loss(self) -> int:
        """Output tokens the attack took from the victim."""
        return self.victim_out_alone - self.victim_out


@dataclass(frozen=True)
class PBSRun:
    """Proposer revenue over many slots, with or without proposer-builder separation.

    Attributes
    ----------
    separated : bool
        True if proposers sold their blocks to builders.
    revenue : Mapping
        Total revenue of each validator.
    stakes : Mapping
        Each validator's stake.
    slots : Mapping
        Slots each validator proposed.
    """

    separated: bool
    revenue: Mapping[str, float]
    stakes: Mapping[str, int]
    slots: Mapping[str, int]

    def revenue_per_stake(self, validator: str) -> float:
        """``validator``'s revenue divided by its stake."""
        return self.revenue[validator] / self.stakes[validator]
