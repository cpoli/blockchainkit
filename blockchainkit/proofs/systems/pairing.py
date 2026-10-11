"""A toy bilinear pairing on a supersingular curve, the engine of KZG, Groth16 and PLONK.

A pairing is a map e from two copies of a group of prime order r into a
third, with ``e(aP, bQ) = e(P, Q)**(a b)``. It lets a verifier check one
multiplication between hidden exponents, which is what every
pairing-based SNARK needs.

The curve ``y**2 = x**3 + x`` over F_p, with p = 3 mod 4, is supersingular:
it has p + 1 points, and its pairing values live in F_(p**2), the
complex-like numbers ``a + b i`` with ``i**2 = -1``. The distortion map
``(x, y) -> (-x, i y)`` makes the reduced Tate pairing, computed by
Miller's algorithm, symmetric and nondegenerate on the subgroup of order
r. This is the Boneh-Franklin construction (2001) with r = 2013265921,
the BabyBear prime, and p = 12 r - 1, a 35-bit prime. Discrete logarithms
in a group that small take seconds, so this curve teaches the algebra and
nothing about security; deployed systems use BN254 or BLS12-381.
"""

from blockchainkit.crypto.core.base import Point
from blockchainkit.crypto.systems.curves import Curve, add, multiply
from blockchainkit.proofs.utils.polynomials import FIELD_PRIME

GTElement = tuple[int, int]
"""An element ``a + b i`` of F_(p**2), as ``(a, b)``."""

PAIRING_CURVE = Curve(24159191051, 1, 0, (4010265589, 9478310149), FIELD_PRIME, "toy-pairing")
"""Curve: ``y**2 = x**3 + x`` over the prime 12 * 2013265921 - 1, with a generator of
order 2013265921 (the BabyBear field prime, so scalars are elements of
:data:`~blockchainkit.proofs.utils.polynomials.FIELD_PRIME`)."""


def _mul(a: GTElement, b: GTElement, p: int) -> GTElement:
    return (a[0] * b[0] - a[1] * b[1]) % p, (a[0] * b[1] + a[1] * b[0]) % p


def _power(a: GTElement, exponent: int, p: int) -> GTElement:
    result = (1, 0)
    while exponent:
        if exponent & 1:
            result = _mul(result, a, p)
        a = _mul(a, a, p)
        exponent >>= 1
    return result


def _check_curve(curve: Curve) -> None:
    if not isinstance(curve, Curve):
        raise TypeError("curve must be a Curve")
    if curve.a != 1 or curve.b != 0 or curve.p % 4 != 3 or (curve.p + 1) % curve.order:
        raise ValueError("need y**2 = x**3 + x over p = 3 mod 4 with the order dividing p + 1")


def _check_point(point: Point, curve: Curve) -> None:
    if not curve.contains(point):
        raise ValueError("points must lie on the curve")
    if multiply(curve.order, point, curve) is not None:
        raise ValueError("points must lie in the subgroup of prime order")


def pairing(left: Point, right: Point, curve: Curve = PAIRING_CURVE) -> GTElement:
    """Compute the reduced Tate pairing ``e(left, distort(right))``.

    Parameters
    ----------
    left, right : Point
        Points of the order-r subgroup; the point at infinity pairs to 1.
    curve : Curve
        A supersingular curve ``y**2 = x**3 + x`` with p = 3 mod 4.

    Returns
    -------
    GTElement
        An r-th root of unity in F_(p**2).

    Examples
    --------
    >>> from blockchainkit.proofs import PAIRING_CURVE as E, pairing, gt_power
    >>> from blockchainkit.crypto import multiply
    >>> G = E.generator
    >>> pairing(multiply(3, G, E), multiply(5, G, E)) == gt_power(pairing(G, G), 15)
    True
    """
    _check_curve(curve)
    _check_point(left, curve)
    _check_point(right, curve)
    if left is None or right is None:
        return (1, 0)
    p = curve.p
    xq, yq = right
    f: GTElement = (1, 0)
    t: Point = left
    for bit in bin(curve.order)[3:]:
        for step in ("double", "add") if bit == "1" else ("double",):
            assert t is not None
            xt, yt = t
            other = t if step == "double" else left
            if other[0] == xt and (other[1] + yt) % p == 0:
                t = None  # A vertical line: its value lies in F_p, and the final power kills it.
                continue
            if step == "double":
                slope = (3 * xt * xt + curve.a) * pow(2 * yt, -1, p) % p
                f = _mul(f, f, p)
            else:
                slope = (other[1] - yt) * pow(other[0] - xt, -1, p) % p
            # The line through t and other, evaluated at the distorted point (-xq, i yq).
            f = _mul(f, ((slope * (xq + xt) - yt) % p, yq), p)
            t = add(t, other, curve)
    return _power(f, (p * p - 1) // curve.order, p)


def gt_multiply(left: GTElement, right: GTElement, curve: Curve = PAIRING_CURVE) -> GTElement:
    """Multiply two pairing values in F_(p**2)."""
    _check_curve(curve)
    return _mul(left, right, curve.p)


def gt_power(element: GTElement, exponent: int, curve: Curve = PAIRING_CURVE) -> GTElement:
    """Raise a pairing value to an integer power, reduced modulo the group order."""
    _check_curve(curve)
    if type(exponent) is not int:
        raise TypeError(f"exponent must be an integer, not {type(exponent).__name__}")
    return _power(element, exponent % curve.order, curve.p)
