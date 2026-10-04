"""The nothing-at-stake problem (Buterin 2014): voting on every fork is free.

A proof-of-work miner must split its hashrate between forks. A proof-of-stake
validator can sign blocks on every fork at no cost, and collect the reward
whichever fork wins. If everyone does, forks never resolve. The remedy,
first proposed in Buterin's Slasher, is a penalty: evidence of signing two
conflicting blocks destroys the validator's deposit.
"""


def fork_voting_payoffs(
    fork_a_probability: float, reward: float, penalty: float
) -> dict[str, float]:
    """Expected payoff of voting for fork A, fork B, or both.

    Parameters
    ----------
    fork_a_probability : float
        Chance that fork A becomes canonical.
    reward : float
        Reward for having voted on the winning fork.
    penalty : float
        Deposit destroyed when a validator is caught voting on both (slashing).

    Returns
    -------
    dict
        Expected payoff of the strategies ``"A"``, ``"B"`` and ``"both"``.

    Examples
    --------
    >>> from blockchainkit.consensus import fork_voting_payoffs
    >>> fork_voting_payoffs(0.5, 1.0, 0.0)
    {'A': 0.5, 'B': 0.5, 'both': 1.0}
    """
    if not 0 <= fork_a_probability <= 1:
        raise ValueError("fork_a_probability must be in [0, 1]")
    if reward < 0 or penalty < 0:
        raise ValueError("reward and penalty must be non-negative")
    return {
        "A": fork_a_probability * reward,
        "B": (1 - fork_a_probability) * reward,
        "both": reward - penalty,
    }
