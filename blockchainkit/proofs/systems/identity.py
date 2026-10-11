"""The Schwartz-Zippel lemma: testing polynomial identities at random points (1980).

Two different polynomials of total degree at most d agree on at most a
d / p fraction of the points of F^n. To test whether two expressions
define the same polynomial, evaluate both at a random point: if they are
equal the test always passes, and if not it fails with probability at least
1 - d / p. Every proof system in this subpackage reduces its statement to
such a test.
"""

from collections.abc import Callable, Sequence
from random import Random

from blockchainkit import _validation
from blockchainkit._validation import integer
from blockchainkit.proofs.core.base import IdentityTest
from blockchainkit.proofs.utils.polynomials import FIELD_PRIME, _check_prime


def schwartz_zippel_bound(total_degree: int, field_size: int) -> float:
    """Return d / p, the most that two distinct polynomials agree on a random point.

    >>> from blockchainkit.proofs import schwartz_zippel_bound
    >>> schwartz_zippel_bound(3, 97)
    0.030927835051546393
    """
    integer(total_degree, "total_degree")
    integer(field_size, "field_size", 1)
    return min(total_degree / field_size, 1.0)


def identity_test(
    left: Callable[[Sequence[int]], int],
    right: Callable[[Sequence[int]], int],
    num_variables: int,
    prime: int = FIELD_PRIME,
    *,
    trials: int = 1,
    seed: int = 0,
) -> IdentityTest:
    """Test whether two polynomial functions are equal by evaluating them at random points.

    Parameters
    ----------
    left, right : callable
        Each takes a sequence of ``num_variables`` field elements and
        returns an integer; they are compared modulo ``prime``.
    num_variables : int
        Number of variables.
    prime : int
        Field modulus.
    trials : int
        Independent random points to try.
    seed : int
        Seed of the verifier's randomness.

    Returns
    -------
    IdentityTest
        ``equal`` is ``False`` as soon as a point separates them.

    Examples
    --------
    >>> from blockchainkit.proofs import identity_test
    >>> square = lambda v: (v[0] + v[1]) ** 2
    >>> expanded = lambda v: v[0] ** 2 + 2 * v[0] * v[1] + v[1] ** 2
    >>> identity_test(square, expanded, 2).equal
    True
    >>> identity_test(square, lambda v: v[0] ** 2 + v[1] ** 2, 2).equal
    False
    """
    _check_prime(prime)
    integer(num_variables, "num_variables", 1)
    integer(trials, "trials", 1)
    _validation.seed(seed)
    rng = Random(seed)
    for trial in range(1, trials + 1):
        point = tuple(rng.randrange(prime) for _ in range(num_variables))
        a, b = left(point), right(point)
        if type(a) is not int or type(b) is not int:
            raise TypeError("the functions must return integers")
        if (a - b) % prime:
            return IdentityTest(False, trial, point)
    return IdentityTest(True, trials, None)
