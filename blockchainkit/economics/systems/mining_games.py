"""Mining games (Kiayias et al. 2016): when is honest mining an equilibrium?

The Bitcoin protocol asks every miner to extend the longest chain and
publish each block at once. Kiayias, Koutsoupias, Kyropoulou and
Tselekounis modeled mining as a stochastic game in which miners choose
which block to extend, and showed that when every miner's hashrate is
small, the honest strategy is a best response to the others being honest,
but that a large miner gains by deviating, and other equilibria arise.

This module computes that best response. Against honest miners, a miner of
share ``alpha`` may withhold blocks, publish them to override or match the
public chain, or give up and adopt it. Sapirshtein, Sompolinsky and Zohar
wrote this as a Markov decision process over states ``(a, h, fork)``:
the lengths of the private and public branches since they split, and
whether a tie race is possible (``relevant``) or running (``active``).
The miner maximizes its long-run share of the chain's blocks,

.. math::

   \\rho^* = \\max_\\pi \\lim \\frac{R_{\\text{miner}}}{R_{\\text{miner}} + R_{\\text{others}}},

found by bisection: a share ``rho`` is achievable if and only if the
average reward ``r_miner - rho (r_miner + r_others)`` has a positive optimal
gain. Honest mining is an equilibrium exactly when ``rho* = alpha``.
"""

from blockchainkit._validation import integer, positive, probability

_IRRELEVANT, _RELEVANT, _ACTIVE = 0, 1, 2

# One action: expected miner blocks, expected total blocks, and (probability, next state).
_Action = tuple[float, float, tuple[tuple[float, int], ...]]


def _model(alpha: float, gamma: float, cap: int) -> list[list[_Action]]:
    def index(a: int, h: int, fork: int) -> int:
        return (a * (cap + 1) + h) * 3 + fork

    p, q = alpha, 1 - alpha
    states: list[list[_Action]] = []
    for a in range(cap + 1):
        for h in range(cap + 1):
            for fork in (_IRRELEVANT, _RELEVANT, _ACTIVE):
                outcomes: list[list[tuple[float, float, float, int]]] = []
                # Adopt: give up the private branch; the others' h blocks are final.
                outcomes.append(
                    [(p, 0, h, index(1, 0, _IRRELEVANT)), (q, 0, h, index(0, 1, _RELEVANT))]
                )
                if a > h:  # Override: publish h + 1 blocks, orphaning the public branch.
                    outcomes.append(
                        [
                            (p, h + 1, h + 1, index(a - h, 0, _IRRELEVANT)),
                            (q, h + 1, h + 1, index(a - h - 1, 1, _RELEVANT)),
                        ]
                    )
                if a < cap and h < cap:
                    race = fork == _ACTIVE or (fork == _RELEVANT and 1 <= h <= a)
                    if fork != _ACTIVE:  # Wait: keep mining in private.
                        outcomes.append(
                            [
                                (p, 0, 0, index(a + 1, h, _IRRELEVANT)),
                                (q, 0, 0, index(a, h + 1, _RELEVANT)),
                            ]
                        )
                    if race:  # Match (or keep racing): publish h blocks to tie.
                        outcomes.append(
                            [
                                (p, 0, 0, index(a + 1, h, _ACTIVE)),
                                (gamma * q, h, h, index(a - h, 1, _RELEVANT)),
                                ((1 - gamma) * q, 0, 0, index(a, h + 1, _RELEVANT)),
                            ]
                        )
                actions = []
                for outcome in outcomes:
                    mine = sum(prob * r for prob, r, _, _ in outcome)
                    total = sum(prob * t for prob, _, t, _ in outcome)
                    moves = tuple((prob, nxt) for prob, _, _, nxt in outcome if prob > 0)
                    actions.append((mine, total, moves))
                states.append(actions)
    return states


def _gain_positive(model: list[list[_Action]], rho: float, tolerance: float) -> bool:
    """Whether the optimal average of ``mine - rho * total`` is positive, by value iteration."""
    values = [0.0] * len(model)
    while True:
        updated: list[float] = []
        for actions in model:
            best = -float("inf")
            for mine, total, moves in actions:
                # Aperiodicity transform: stay put with probability 1/2.
                value = 0.5 * (mine - rho * total + sum(p * values[s] for p, s in moves))
                best = max(best, value + 0.5 * values[len(updated)])
            updated.append(best)
        steps = [new - old for new, old in zip(updated, values, strict=True)]
        low, high = min(steps), max(steps)
        if low > 0:
            return True
        if high < tolerance:
            return False
        reference = updated[0]
        values = [value - reference for value in updated]


def optimal_mining_revenue(
    alpha: float, gamma: float, *, max_lead: int = 10, tolerance: float = 1e-4
) -> float:
    """The largest share of the chain a miner of hashrate ``alpha`` can earn against honest miners.

    Parameters
    ----------
    alpha : float
        The miner's hashrate share, in (0, 0.5).
    gamma : float
        Fraction of the others who mine on the miner's block during a tie.
    max_lead : int
        Longest branch the model tracks; a larger bound can only raise the result.
    tolerance : float
        Precision of the bisection on the share.

    Returns
    -------
    float
        At least ``alpha``, which honest mining earns.

    Examples
    --------
    >>> from blockchainkit.economics import optimal_mining_revenue
    >>> optimal_mining_revenue(0.2, 0.0, max_lead=4)
    0.2
    """
    if not 0 < alpha < 0.5:
        raise ValueError("alpha must be in (0, 0.5)")
    probability(gamma, "gamma")
    integer(max_lead, "max_lead", 2)
    positive(tolerance, "tolerance")
    model = _model(alpha, gamma, max_lead)
    low, high = alpha, 1.0
    if not _gain_positive(model, alpha + tolerance, tolerance * 1e-3):
        return alpha
    while high - low > tolerance:
        middle = (low + high) / 2
        if _gain_positive(model, middle, tolerance * 1e-3):
            low = middle
        else:
            high = middle
    return low


def honest_mining_is_equilibrium(
    alpha: float, gamma: float, *, max_lead: int = 10, tolerance: float = 1e-4
) -> bool:
    """True if no withholding strategy beats honest mining for a miner of share ``alpha``.

    Examples
    --------
    >>> from blockchainkit.economics import honest_mining_is_equilibrium
    >>> honest_mining_is_equilibrium(0.1, 0.5, max_lead=4)
    True
    >>> honest_mining_is_equilibrium(0.4, 0.5, max_lead=4)
    False
    """
    revenue = optimal_mining_revenue(alpha, gamma, max_lead=max_lead, tolerance=tolerance)
    return revenue <= alpha
