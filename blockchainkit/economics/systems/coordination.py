"""Focal points (Schelling 1960): coordinating without communicating.

Two strangers must meet in New York on a given day, with no way to agree on
a place or time. Every choice is an equilibrium, as long as both make the
same one, yet most people Schelling asked chose noon at Grand Central
Station. A *focal point* is an equilibrium that stands out, by convention,
salience or uniqueness, and players coordinate on it because each expects
the others to.

Oracle and voting games on blockchains rely on the same idea: when voters
are paid for agreeing with the majority, the truth is the focal answer,
the one each voter expects the others to give.
"""

from random import Random

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed


def coordination_probability(players: int, options: int, salience: float) -> float:
    """Chance that every player picks the same option.

    Each player independently picks the focal option with probability
    ``salience``, and otherwise picks uniformly among all ``options``. The
    focal option is then chosen with probability
    :math:`p = s + (1 - s)/n` and each other one with :math:`q = (1-s)/n`,
    so all ``k`` players coincide with probability :math:`p^k + (n-1) q^k`.

    Parameters
    ----------
    players : int
        Number of players, at least 2.
    options : int
        Number of equally good options, at least 1.
    salience : float
        How strongly the focal option stands out, in [0, 1].

    Returns
    -------
    float

    Examples
    --------
    >>> from blockchainkit.economics import coordination_probability
    >>> round(coordination_probability(2, 10, 0.0), 6)
    0.1
    >>> coordination_probability(2, 10, 1.0)
    1.0
    """
    integer(players, "players", 2)
    integer(options, "options", 1)
    probability(salience, "salience")
    focal = salience + (1 - salience) / options
    other = (1 - salience) / options
    return float(focal**players + (options - 1) * other**players)


def play_coordination(
    players: int, options: int, salience: float, *, rounds: int, seed: int = 0
) -> float:
    """Simulate the coordination game and return the fraction of rounds in which all matched.

    Players choose as in :func:`coordination_probability`; option 0 is the focal one.

    Examples
    --------
    >>> from blockchainkit.economics import play_coordination
    >>> play_coordination(3, 5, 1.0, rounds=10)
    1.0
    """
    integer(players, "players", 2)
    integer(options, "options", 1)
    probability(salience, "salience")
    integer(rounds, "rounds", 1)
    check_seed(seed)
    rng = Random(seed)
    matched = 0
    for _ in range(rounds):
        choices = {0 if rng.random() < salience else rng.randrange(options) for _ in range(players)}
        matched += len(choices) == 1
    return matched / rounds
