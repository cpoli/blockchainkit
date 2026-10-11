"""The sum-check protocol of Lund, Fortnow, Karloff and Nisan (1990).

A prover claims that a polynomial ``f`` in n variables sums to ``H`` over
the Boolean cube {0, 1}**n. Summing directly takes 2**n evaluations. In
round i, the prover instead sends the univariate polynomial

    g_i(X) = sum of f(r_1, ..., r_{i-1}, X, b_{i+1}, ..., b_n) over the bs,

the verifier checks g_i(0) + g_i(1) against the previous claim and fixes
X to a random r_i. After n rounds the verifier evaluates f once, at
(r_1, ..., r_n). A false claim survives each round with probability at
most d / p (Schwartz-Zippel), so with probability at most n d / p.
"""

from collections.abc import Callable, Sequence
from itertools import product
from random import Random

from blockchainkit import _validation
from blockchainkit._validation import integer
from blockchainkit.proofs.core.base import Polynomial, SumcheckRun
from blockchainkit.proofs.utils.polynomials import (
    FIELD_PRIME,
    _check_prime,
    interpolate,
    poly_add,
    poly_eval,
    polynomial,
)


def multilinear_extension(
    values: Sequence[int], point: Sequence[int], prime: int = FIELD_PRIME
) -> int:
    """Evaluate the multilinear extension of a table of 2**n values at a field point.

    The extension is the unique polynomial of degree at most one in each
    variable that takes ``values[b]`` at each Boolean vector b, read as a
    binary number with the first variable most significant.

    >>> from blockchainkit.proofs import multilinear_extension
    >>> multilinear_extension([3, 5, 7, 9], [1, 0], 97)  # the table entry at b = 10
    7
    >>> multilinear_extension([3, 5, 7, 9], [2, 0], 97)  # 3 + 4 * x1 + 2 * x2, beyond the cube
    11
    """
    _check_prime(prime)
    table = [v % prime for v in values]
    if len(table) != 2 ** len(point) or not table:
        raise ValueError("need 2**n values for a point with n coordinates")
    for x in point:
        half = len(table) // 2
        table = [
            (lo + x * (hi - lo)) % prime for lo, hi in zip(table[:half], table[half:], strict=True)
        ]
    return table[0]


def _evaluate(f: Callable[[Sequence[int]], int], point: tuple[int, ...], prime: int) -> int:
    value = f(point)
    if type(value) is not int:
        raise TypeError("f must return integers")
    return value % prime


def _cheat(honest: Polynomial, targets: tuple[int, int], degree: int, prime: int) -> Polynomial:
    """Shift ``honest`` so it takes ``targets`` at 0 and 1, keeping roots at 2, ..., degree.

    The lie then vanishes again if the verifier happens to pick one of
    those points: the best a cheating prover can do, with probability
    ``degree / prime`` per round.
    """
    points = [
        (0, targets[0] - poly_eval(honest, 0, prime)),
        (1, targets[1] - poly_eval(honest, 1, prime)),
    ]
    points += [(k, 0) for k in range(2, degree + 1)]
    return poly_add(honest, interpolate(points, prime), prime)


def sumcheck(
    f: Callable[[Sequence[int]], int],
    num_variables: int,
    degree: int,
    prime: int = FIELD_PRIME,
    *,
    claim: int | None = None,
    seed: int = 0,
) -> SumcheckRun:
    """Run the sum-check protocol for the sum of ``f`` over {0, 1}**n.

    The prover is honest when ``claim`` is the true sum (the default).
    Given a false claim, it lies as well as it can: each round's polynomial
    is consistent with the previous claim and differs from the true one
    by a polynomial with ``degree`` roots, in case the verifier picks one.

    Parameters
    ----------
    f : callable
        A polynomial function of ``num_variables`` field elements, of degree
        at most ``degree`` in each variable.
    num_variables : int
        Number of variables n.
    degree : int
        The degree bound the verifier enforces on each round's polynomial.
    prime : int
        Field modulus.
    claim : int, optional
        The sum the prover asserts.
    seed : int
        Seed of the verifier's random challenges.

    Returns
    -------
    SumcheckRun

    Examples
    --------
    >>> from blockchainkit.proofs import CNF, sumcheck
    >>> formula = CNF(3, ((1, 2), (-2, 3)))
    >>> run = sumcheck(lambda x: formula.evaluate(x, 97), 3, formula.degree, 97)
    >>> run.claim, run.accepted
    (4, True)
    >>> sumcheck(lambda x: formula.evaluate(x, 97), 3, formula.degree, 97, claim=5).accepted
    False
    """
    _check_prime(prime)
    integer(num_variables, "num_variables", 1)
    integer(degree, "degree", 1)
    _validation.seed(seed)
    true_sum = sum(_evaluate(f, b, prime) for b in product((0, 1), repeat=num_variables)) % prime
    if claim is None:
        claim = true_sum
    integer(claim, "claim")
    claim %= prime
    rng = Random(seed)
    current = claim
    prefix: tuple[int, ...] = ()
    polynomials: list[Polynomial] = []
    challenges: list[int] = []
    for i in range(num_variables):
        rest = num_variables - i - 1
        sums = [
            sum(_evaluate(f, (*prefix, x, *b), prime) for b in product((0, 1), repeat=rest))
            for x in range(degree + 1)
        ]
        message = interpolate(list(enumerate(sums)), prime)
        if (sums[0] + sums[1] - current) % prime:
            message = _cheat(message, ((current - sums[1]) % prime, sums[1]), degree, prime)
        r = rng.randrange(prime)  # Drawn only after the prover has sent this round's message.
        polynomials.append(message)
        challenges.append(r)
        current, prefix = poly_eval(message, r, prime), (*prefix, r)
    accepted = verify_sumcheck(f, claim, polynomials, challenges, degree, prime)
    return SumcheckRun(claim, true_sum, tuple(polynomials), tuple(challenges), accepted)


def verify_sumcheck(
    f: Callable[[Sequence[int]], int],
    claim: int,
    polynomials: Sequence[Sequence[int]],
    challenges: Sequence[int],
    degree: int,
    prime: int = FIELD_PRIME,
) -> bool:
    """Check a sum-check transcript: the verifier's side of :func:`sumcheck`.

    Each polynomial must have degree at most ``degree`` and satisfy
    ``g_i(0) + g_i(1) = g_{i-1}(r_{i-1})`` (the claim for i = 1); finally
    ``g_n(r_n)`` must equal ``f(r_1, ..., r_n)``, the one evaluation of f
    the verifier makes. The verifier is sound only if each challenge was
    drawn after its polynomial was sent.
    """
    _check_prime(prime)
    integer(degree, "degree", 1)
    if len(polynomials) != len(challenges) or not polynomials:
        raise ValueError("need one challenge per round, and at least one round")
    current = claim % prime
    for message, r in zip(polynomials, challenges, strict=True):
        g = polynomial(message, prime)
        if len(g) > degree + 1:
            return False
        if (poly_eval(g, 0, prime) + poly_eval(g, 1, prime) - current) % prime:
            return False
        current = poly_eval(g, r, prime)
    return current == _evaluate(f, tuple(c % prime for c in challenges), prime)
