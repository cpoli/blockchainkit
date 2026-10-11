"""Shamir's IP = PSPACE: an interactive proof for quantified Boolean formulas (1990).

A quantified formula such as "for all x, there exists y: phi(x, y)" is
arithmetized like a CNF, with "for all" becoming a product,
``A f = f(0) f(1)``, and "there exists" a complemented product,
``E f = 1 - (1 - f(0))(1 - f(1))``. The prover convinces the verifier of
the formula's value by sum-check-style rounds, one per operator, peeling
operators from the outside in.

Each product doubles degrees, so after n quantifiers the polynomials
would have degree about 2**n. Shen's linearization operator,
``L_i f = (1 - x_i) f(x_i = 0) + x_i f(x_i = 1)``, which agrees with f on
0/1 inputs and is linear in x_i, is inserted after every quantifier to keep
every polynomial of degree at most max(2, degree of phi).
"""

from random import Random

from blockchainkit import _validation
from blockchainkit.proofs.core.base import QBF, TQBFRound, TQBFRun
from blockchainkit.proofs.systems.sumcheck import _cheat
from blockchainkit.proofs.utils.polynomials import FIELD_PRIME, _check_prime, interpolate, poly_eval


def tqbf_operators(qbf: QBF, *, linearize: bool = True) -> tuple[tuple[str, int], ...]:
    """List the arithmetized operators of a formula from the outside in.

    With linearization, the quantifier on x_i is followed by
    ``L_1, ..., L_i``: the order of Shen's proof.

    >>> from blockchainkit.proofs import CNF, QBF, tqbf_operators
    >>> tqbf_operators(QBF("AE", CNF(2, ((1, 2),))))
    (('A', 1), ('L', 1), ('E', 2), ('L', 1), ('L', 2))
    """
    operators: list[tuple[str, int]] = []
    for i, quantifier in enumerate(qbf.quantifiers, start=1):
        operators.append((quantifier, i))
        if linearize:
            operators.extend(("L", j) for j in range(1, i + 1))
    return tuple(operators)


def _combine(operator: str, low: int, high: int, x: int, prime: int) -> int:
    if operator == "A":
        return low * high % prime
    if operator == "E":
        return (1 - (1 - low) * (1 - high)) % prime
    return ((1 - x) * low + x * high) % prime


def _targets(operator: str, claim: int, honest_high: int, x: int, prime: int) -> tuple[int, int]:
    """Values at 0 and 1 that pass the check for ``claim``, keeping the honest value at 1."""
    h = honest_high
    if operator == "A":
        return (claim * pow(h, -1, prime) % prime, h) if h else (claim, 1)
    if operator == "E":
        return ((claim - h) * pow(1 - h, -1, prime) % prime, h) if h != 1 else (claim, 0)
    if x != 1:
        return ((claim - x * h) * pow(1 - x, -1, prime) % prime, h)
    return (0, claim)


def tqbf_protocol(
    qbf: QBF,
    prime: int = FIELD_PRIME,
    *,
    claim: int | None = None,
    seed: int = 0,
    linearize: bool = True,
) -> TQBFRun:
    """Run the interactive proof of a quantified Boolean formula's value.

    The prover evaluates every inner expression by brute force, which is
    exponential but needs only polynomial space; the verifier does
    polynomial work. A false claim survives with probability at most
    (rounds * degree) / prime.

    Parameters
    ----------
    qbf : QBF
        The formula.
    prime : int
        Field modulus.
    claim : int, optional
        The value the prover asserts, 1 (true) or 0 (false); the true value
        by default. A false claim makes the prover lie as well as it can.
    seed : int
        Seed of the verifier's challenges.
    linearize : bool
        Insert Shen's linearization operators. Without them the protocol
        is still sound but the degrees grow exponentially.

    Returns
    -------
    TQBFRun

    Examples
    --------
    >>> from blockchainkit.proofs import CNF, QBF, tqbf_protocol
    >>> formula = QBF("AE", CNF(2, ((1, 2), (-1, -2))))
    >>> tqbf_protocol(formula).accepted, tqbf_protocol(formula, claim=0).accepted
    (True, False)
    """
    if not isinstance(qbf, QBF):
        raise TypeError("qbf must be a QBF")
    _check_prime(prime)
    _validation.seed(seed)
    n = qbf.formula.num_variables
    operators = tqbf_operators(qbf, linearize=linearize)
    bound = max(2, qbf.formula.degree) if linearize else qbf.formula.degree * 2 ** (n - 1)
    memo: dict[tuple[int, tuple[int, ...]], int] = {}

    def value(k: int, point: tuple[int, ...]) -> int:
        """The expression made of operators k, k+1, ... applied to phi, at ``point``."""
        if k == len(operators):
            return qbf.formula.evaluate(point, prime)
        key = (k, point)
        if key not in memo:
            operator, variable = operators[k]
            i = variable - 1
            low = value(k + 1, (*point[:i], 0, *point[i + 1 :]))
            high = value(k + 1, (*point[:i], 1, *point[i + 1 :]))
            memo[key] = _combine(operator, low, high, point[i], prime)
        return memo[key]

    true_value = value(0, (0,) * n)
    if claim is None:
        claim = true_value
    if claim not in (0, 1):
        raise ValueError("claim must be 0 or 1")
    rng = Random(seed)
    point = [0] * n
    current, rounds, accepted = claim, [], True
    for k, (operator, variable) in enumerate(operators):
        i = variable - 1

        def inner(x: int, k: int = k, i: int = i) -> int:
            return value(k + 1, (*point[:i], x, *point[i + 1 :]))

        message = interpolate([(x, inner(x)) for x in range(bound + 1)], prime)
        low, high = poly_eval(message, 0, prime), poly_eval(message, 1, prime)
        if _combine(operator, low, high, point[i], prime) != current:
            targets = _targets(operator, current, high, point[i], prime)
            message = _cheat(message, targets, bound, prime)
        # The verifier: check the degree and the operator's identity, then draw a challenge.
        low, high = poly_eval(message, 0, prime), poly_eval(message, 1, prime)
        accepted &= len(message) <= bound + 1
        accepted &= _combine(operator, low, high, point[i], prime) == current
        r = rng.randrange(prime)
        rounds.append(TQBFRound(operator, variable, message, r))
        point[i], current = r, poly_eval(message, r, prime)
    accepted &= current == qbf.formula.evaluate(point, prime)
    return TQBFRun(claim, true_value, tuple(rounds), accepted)
