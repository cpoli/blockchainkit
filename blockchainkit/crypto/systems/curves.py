"""Readable elliptic-curve group arithmetic, not constant-time cryptography.

Points are ``(x, y)`` tuples; ``None`` denotes the point at infinity.
The curve equation is y**2 = x**3 + a*x + b modulo p.
"""

from dataclasses import dataclass
from math import isqrt

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import Point
from blockchainkit.crypto.utils.primes import is_prime

_SECP_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


@dataclass(frozen=True)
class Curve:
    """A nonsingular prime-field curve with a prime-order generator.

    Parameters
    ----------
    p, a, b : int
        Field modulus and reduced curve coefficients.
    generator : tuple of int
        Affine coordinates of the base point.
    order : int
        Prime order of the base point.
    name : str
        Human-readable label.

    Notes
    -----
    Custom field/order primes must be below 2**64, which bounds the
    educational primality check. secp256k1's own field prime and group
    order are also accepted, each only in its own role.
    """

    p: int
    a: int
    b: int
    generator: tuple[int, int]
    order: int
    name: str = "custom"

    def __post_init__(self) -> None:
        for value, known in ((self.p, _SECP_P), (self.order, _SECP_N)):
            integer(value, "prime", 3)
            if value == known:
                continue
            if value >= 2**64:
                raise ValueError("custom primes must be below 2**64")
            if not is_prime(value):
                raise ValueError("field modulus and generator order must be prime")
        for value in (self.a, self.b):
            integer(value, "coefficient")
            if value >= self.p:
                raise ValueError("coefficients must be reduced modulo p")
        if (4 * self.a**3 + 27 * self.b**2) % self.p == 0:
            raise ValueError("singular curve")
        if self.generator is None or not self.contains(self.generator):
            raise ValueError("generator must be a finite point on the curve")
        if multiply(self.order, self.generator, self) is not None:
            raise ValueError("generator does not have the claimed order")

    def contains(self, point: Point) -> bool:
        """Return whether point is infinity or a canonical affine curve point."""
        if point is None:
            return True
        if not isinstance(point, tuple) or len(point) != 2:
            return False
        x, y = point
        return (
            type(x) is int
            and type(y) is int
            and 0 <= x < self.p
            and 0 <= y < self.p
            and (y * y - x**3 - self.a * x - self.b) % self.p == 0
        )

    @property
    def cofactor_is_one(self) -> bool:
        """Whether the generator's subgroup is provably the whole curve group.

        Hasse's theorem bounds the number of points: #E <= p + 1 + 2*sqrt(p).
        The subgroup order n divides #E, so if 2n exceeds that bound the
        cofactor #E/n must be 1. Every on-curve point then lies in the
        subgroup, and verifiers can skip the n*P = O membership check.
        """
        return 2 * self.order > self.p + 1 + 2 * (isqrt(self.p) + 1)


def _add(left: Point, right: Point, curve: Curve) -> Point:
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    p = curve.p
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if left == right:
        slope = (3 * x1 * x1 + curve.a) * pow(2 * y1, -1, p) % p
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (slope * slope - x1 - x2) % p
    return x3, (slope * (x1 - x3) - y1) % p


def add(left: Point, right: Point, curve: Curve) -> Point:
    """Add two validated points, including infinity and inverse pairs."""
    if not curve.contains(left) or not curve.contains(right):
        raise ValueError("points must lie on the curve")
    return _add(left, right, curve)


def multiply(scalar: int, point: Point, curve: Curve) -> Point:
    """Multiply a point by a signed integer using double-and-add.

    Scalars are not reduced modulo the generator order: this also allows
    checking subgroup membership for arbitrary points on a custom curve.
    """
    if type(scalar) is not int:
        raise TypeError(f"scalar must be an integer, not {type(scalar).__name__}")
    if not curve.contains(point):
        raise ValueError("point must lie on the curve")
    if scalar < 0:
        point = None if point is None else (point[0], -point[1] % curve.p)
        scalar = -scalar
    result = None
    while scalar:
        if scalar & 1:
            result = _add(result, point, curve)
        point = _add(point, point, curve)
        scalar >>= 1
    return result


TOY_CURVE = Curve(17, 2, 2, (5, 1), 19, "toy17")
SECP256K1 = Curve(
    _SECP_P,
    0,
    7,
    (
        0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
        0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
    ),
    _SECP_N,
    "secp256k1",
)


def public_key(private: int, curve: Curve = SECP256K1) -> tuple[int, int]:
    """Derive private*G for 1 <= private < generator order.

    >>> from blockchainkit.crypto import public_key, TOY_CURVE
    >>> public_key(2, TOY_CURVE)
    (6, 3)
    """
    integer(private, "private", 1)
    if private >= curve.order:
        raise ValueError("private key must be below generator order")
    point = multiply(private, curve.generator, curve)
    assert point is not None
    return point


def encode_point(point: Point, curve: Curve = SECP256K1) -> bytes:
    """Return fixed-width uncompressed encoding (0x04 || x || y)."""
    if point is None or not curve.contains(point):
        raise ValueError("expected a finite on-curve point")
    width = (curve.p.bit_length() + 7) // 8
    return b"\x04" + point[0].to_bytes(width, "big") + point[1].to_bytes(width, "big")
