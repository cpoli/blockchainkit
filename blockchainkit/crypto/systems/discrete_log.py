"""Generic discrete-logarithm algorithms: why group size and structure matter.

Baby-step giant-step (Shanks 1971) solves base**x = target in any cyclic
group of order n with about 2*sqrt(n) multiplications. Pohlig-Hellman (1978)
splits the problem along the prime factors of n, so its cost is governed by
the *largest prime factor*, not by n. Together they explain why
Diffie-Hellman and Schnorr work in a subgroup of large prime order.
"""

from math import isqrt

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import DiscreteLogResult
from blockchainkit.crypto.utils.primes import is_prime

_TRIAL_DIVISION_BOUND = 2**20


def _check(base: int, target: int, modulus: int, order: int) -> None:
    for value, name in ((base, "base"), (target, "target")):
        integer(value, name, 1)
    integer(modulus, "modulus", 3)
    integer(order, "order", 1)
    if base >= modulus or target >= modulus:
        raise ValueError("base and target must be reduced modulo the modulus")
    if pow(base, order, modulus) != 1:
        raise ValueError("base**order must be 1 modulo the modulus")


def _bsgs(base: int, target: int, modulus: int, order: int) -> tuple[int, int]:
    m = isqrt(order - 1) + 1 if order > 1 else 1
    baby: dict[int, int] = {}
    value = 1
    for j in range(m):
        baby.setdefault(value, j)
        value = value * base % modulus
    giant_step = pow(base, -m, modulus)
    gamma = target
    for i in range(m):
        if gamma in baby:
            return (i * m + baby[gamma]) % order, m + i + 1
        gamma = gamma * giant_step % modulus
    raise ValueError("target is not a power of base")


def baby_step_giant_step(base: int, target: int, modulus: int, order: int) -> DiscreteLogResult:
    """Solve ``base**x = target (mod modulus)`` in about ``2*sqrt(order)`` steps.

    Writing ``x = i*m + j`` with ``m = ceil(sqrt(order))``, a table of baby
    steps ``base**j`` is matched against giant steps ``target * base**(-i*m)``.

    Parameters
    ----------
    base : int
        A group element whose order divides ``order``.
    target : int
        The element whose logarithm is wanted.
    modulus : int
        The modulus of the multiplicative group.
    order : int
        A multiple of the order of ``base`` (the subgroup order).

    Returns
    -------
    DiscreteLogResult
        The exponent and the number of table multiplications.

    Raises
    ------
    ValueError
        ``target`` is not a power of ``base``.

    Examples
    --------
    >>> from blockchainkit.crypto import baby_step_giant_step
    >>> baby_step_giant_step(2, pow(2, 77, 1019), 1019, 1018).exponent
    77
    """
    _check(base, target, modulus, order)
    exponent, steps = _bsgs(base, target, modulus, order)
    return DiscreteLogResult(exponent, steps)


def factor_order(n: int) -> dict[int, int]:
    """Factor a group order by trial division up to 2**20.

    A cofactor left over after trial division must itself be prime, which
    is all Pohlig-Hellman needs; otherwise the order is rejected.

    >>> from blockchainkit.crypto.systems.discrete_log import factor_order
    >>> factor_order(8100)
    {2: 2, 3: 4, 5: 2}
    """
    integer(n, "n", 1)
    factors: dict[int, int] = {}
    d = 2
    while d * d <= n and d <= _TRIAL_DIVISION_BOUND:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        if n >= 2**64 or not is_prime(n):
            raise ValueError("cannot factor the order by trial division")
        factors[n] = factors.get(n, 0) + 1
    return factors


def pohlig_hellman(base: int, target: int, modulus: int, order: int) -> DiscreteLogResult:
    """Solve a discrete log by splitting the group order into prime powers.

    For each prime power ``p**e`` dividing ``order``, the problem is mapped
    into the subgroup of order ``p**e`` and solved one base-``p`` digit at a
    time with baby-step giant-step in a subgroup of order ``p``. The Chinese
    Remainder Theorem combines the answers. The cost is about
    ``sum(e * sqrt(p))``, tiny when every prime factor is small.

    Parameters and return value are as for :func:`baby_step_giant_step`.

    Examples
    --------
    >>> from blockchainkit.crypto import pohlig_hellman
    >>> pohlig_hellman(6, pow(6, 4321, 8101), 8101, 8100).exponent
    4321
    """
    _check(base, target, modulus, order)
    # Reduce the given multiple to the exact order of base, prime by prime;
    # otherwise a prime-power subproblem can have a trivial generator.
    factors = factor_order(order)
    for prime in factors:
        while factors[prime] and pow(base, order // prime, modulus) == 1:
            order //= prime
            factors[prime] -= 1
    residues, moduli, operations = [], [], 0
    for prime, power in factors.items():
        if power == 0:
            continue
        cofactor = order // prime**power
        g = pow(base, cofactor, modulus)  # Order divides prime**power.
        h = pow(target, cofactor, modulus)
        generator = pow(g, prime ** (power - 1), modulus)  # Order divides prime.
        digits = 0
        for k in range(power):
            # Strip the digits found so far, then project onto the order-p subgroup.
            residual = h * pow(g, -digits, modulus) % modulus
            projected = pow(residual, prime ** (power - 1 - k), modulus)
            digit, steps = _bsgs(generator, projected, modulus, prime)
            operations += steps
            digits += digit * prime**k
        residues.append(digits)
        moduli.append(prime**power)
    exponent = 0
    for residue, m in zip(residues, moduli, strict=True):
        rest = order // m
        exponent += residue * rest * pow(rest, -1, m)
    return DiscreteLogResult(exponent % order, operations)
