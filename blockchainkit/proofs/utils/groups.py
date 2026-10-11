"""Group helpers for the commitment schemes: independent generators and linear combinations."""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.constants import IPA_GENERATOR_DOMAIN
from blockchainkit.crypto.core.base import Point
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.curves import Curve, add, multiply
from blockchainkit.crypto.systems.hashing import sha256


def independent_generators(
    count: int, label: str, group: DHGroup = TEACHING_GROUP
) -> tuple[int, ...]:
    """Derive ``count`` generators of the order-q subgroup whose mutual logs nobody knows.

    Each one hashes the group, a label and an index into the subgroup, as
    :func:`~blockchainkit.crypto.systems.commitments.pedersen_generators`
    does for one. Vector commitments need them: whoever knew a relation
    between two generators could open a commitment two ways.

    >>> from blockchainkit.proofs import independent_generators
    >>> len(set(independent_generators(8, "demo")))
    8
    """
    integer(count, "count", 1)
    if not isinstance(label, str):
        raise TypeError("label must be a string")
    generators: list[int] = []
    counter = 0
    while len(generators) < count:
        seed = IPA_GENERATOR_DOMAIN + f"{group.p}:{group.q}:{label}:{counter}".encode()
        candidate = int.from_bytes(sha256(seed), "big") % group.p
        h = pow(candidate, (group.p - 1) // group.q, group.p)
        if h not in (0, 1) and h not in generators:
            generators.append(h)
        counter += 1
    return tuple(generators)


def multi_exponent(bases: Sequence[int], exponents: Sequence[int], group: DHGroup) -> int:
    """Return the product of ``base**exponent`` modulo p: a vector commitment."""
    if len(bases) != len(exponents):
        raise ValueError("need as many exponents as bases")
    result = 1
    for base, exponent in zip(bases, exponents, strict=True):
        result = result * pow(base, exponent % group.q, group.p) % group.p
    return result


def linear_combination(scalars: Sequence[int], points: Sequence[Point], curve: Curve) -> Point:
    """Return the sum of ``scalar * point`` on a curve (a multi-scalar multiplication)."""
    if len(scalars) != len(points):
        raise ValueError("need as many scalars as points")
    result: Point = None
    for scalar, point in zip(scalars, points, strict=True):
        if scalar % curve.order:
            result = add(result, multiply(scalar % curve.order, point, curve), curve)
    return result
