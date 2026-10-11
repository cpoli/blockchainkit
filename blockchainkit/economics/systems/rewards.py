"""Block rewards: Nakamoto's incentive (2008) and the halving schedule (2009).

Section 6 of the Bitcoin paper pays the creator of each block in new coins,
which both distributes the currency and rewards the work that secures it;
transaction fees add to the reward and, once a fixed supply is issued,
replace it. The incentive also discourages attacks: a miner who could
outpace the network "ought to find it more profitable to play by the rules
... than to undermine the system and the validity of his own wealth."

Bitcoin's release (2009) fixed the schedule. Block ``h`` creates
``50 BTC >> (h // 210000)``: the subsidy halves every 210,000 blocks, about
every four years, and the right shift rounds down to whole satoshis, so
issuance stops after 33 halvings, just short of 21 million coins.
"""

from blockchainkit._validation import integer, positive, probability
from blockchainkit.consensus.systems.catch_up import attacker_success_probability
from blockchainkit.economics.core.base import AttackIncentive

COIN = 100_000_000
"""Satoshis per bitcoin."""

INITIAL_SUBSIDY = 50 * COIN
"""The subsidy of the first era, in satoshis."""

HALVING_INTERVAL = 210_000
"""Blocks between halvings."""


def block_subsidy(height: int) -> int:
    """New satoshis created by the block at ``height``, as Bitcoin Core's ``GetBlockSubsidy``.

    Examples
    --------
    >>> from blockchainkit.economics import block_subsidy
    >>> block_subsidy(0), block_subsidy(210_000), block_subsidy(840_000)
    (5000000000, 2500000000, 312500000)
    """
    integer(height, "height")
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:  # A right shift by 64 or more is undefined in C++.
        return 0
    return INITIAL_SUBSIDY >> halvings


def issued_supply(blocks: int) -> int:
    """Satoshis created by the first ``blocks`` blocks (heights 0 to ``blocks - 1``).

    The genesis block's 50 BTC count here, although Bitcoin can never spend them.

    Examples
    --------
    >>> from blockchainkit.economics import issued_supply
    >>> issued_supply(10**8) / 10**8  # In bitcoins.
    20999999.9769
    """
    integer(blocks, "blocks")
    total, era = 0, 0
    while blocks > 0 and era < 64:
        in_era = min(blocks, HALVING_INTERVAL)
        total += in_era * (INITIAL_SUBSIDY >> era)
        blocks -= in_era
        era += 1
    return total


def block_reward(height: int, fees: int = 0) -> int:
    """What the miner of the block at ``height`` may claim: its subsidy plus the fees."""
    integer(fees, "fees")
    return block_subsidy(height) + fees


def double_spend_incentive(
    attacker_fraction: float,
    *,
    reward: float,
    payment: float,
    confirmations: int,
    devaluation: float = 0.0,
) -> AttackIncentive:
    """Compare mining honestly with attempting a double spend, in Nakamoto's model.

    The attacker pays a merchant, who waits for ``confirmations`` blocks,
    while it mines a private chain in which the payment is absent. It finds
    blocks at the same rate either way; call it ``m = confirmations + 1``
    blocks for the race. Mined honestly, they earn ``m * reward``. Spent on
    the attack, they earn ``payment + m * reward`` if the private chain
    overtakes, with probability ``P`` from
    :func:`~blockchainkit.consensus.systems.catch_up.attacker_success_probability`,
    and nothing if it does not. ``devaluation`` is the fraction of the
    rewards' worth lost when a successful attack shakes confidence in the
    coin: Nakamoto's "validity of his own wealth".

    Parameters
    ----------
    attacker_fraction : float
        The attacker's share of the hashrate, in [0, 1].
    reward : float
        Reward per block.
    payment : float
        The amount the attacker would recover.
    confirmations : int
        Blocks the merchant waits for.
    devaluation : float
        Fraction of the attacker's rewards lost if the attack succeeds.

    Returns
    -------
    AttackIncentive

    Examples
    --------
    >>> from blockchainkit.economics import double_spend_incentive
    >>> double_spend_incentive(0.1, reward=50, payment=1_000, confirmations=6).attack_pays
    False
    >>> double_spend_incentive(0.6, reward=50, payment=1_000, confirmations=6).attack_pays
    True
    """
    probability(attacker_fraction, "attacker_fraction")
    positive(reward, "reward")
    positive(payment, "payment")
    probability(devaluation, "devaluation")
    p = attacker_success_probability(attacker_fraction, confirmations)
    blocks = confirmations + 1
    honest = blocks * reward
    attack = p * (payment + (1 - devaluation) * blocks * reward)
    return AttackIncentive(p, float(honest), float(attack))
