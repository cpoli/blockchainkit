r"""The finite fields GF(2**m) behind BCH codes.

An element is an integer below ``2**m`` whose bits are the coefficients of
a polynomial over GF(2); addition is XOR, and multiplication is modulo a
fixed primitive polynomial, so that :math:`\alpha = x` generates every
nonzero element. Tables of powers and logarithms make multiplication a
lookup.
"""

from dataclasses import dataclass, field

from blockchainkit._validation import integer

PRIMITIVE_POLYNOMIALS = {
    3: 0b1011,
    4: 0b10011,
    5: 0b100101,
    6: 0b1000011,
    7: 0b10001001,
    8: 0b100011101,
}
"""dict: A primitive polynomial of each degree m from 3 to 8, as a bit mask."""


@dataclass(frozen=True)
class GaloisField:
    """GF(2**m) for 3 <= m <= 8, with the primitive element alpha = x.

    Examples
    --------
    >>> from blockchainkit.wallets.utils import GaloisField
    >>> field = GaloisField(4)
    >>> field.multiply(field.power(3), field.power(14)) == field.power(2)
    True
    """

    m: int
    _exp: tuple[int, ...] = field(init=False, repr=False, compare=False)
    _log: tuple[int, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        integer(self.m, "m", 3)
        if self.m not in PRIMITIVE_POLYNOMIALS:
            raise ValueError("m must be between 3 and 8")
        modulus = PRIMITIVE_POLYNOMIALS[self.m]
        exp, log = [], [0] * (1 << self.m)
        value = 1
        for i in range(self.order):
            exp.append(value)
            log[value] = i
            value <<= 1
            if value >> self.m:
                value ^= modulus
        object.__setattr__(self, "_exp", tuple(exp))
        object.__setattr__(self, "_log", tuple(log))

    @property
    def order(self) -> int:
        """The number of nonzero elements, ``2**m - 1``: the multiplicative group's order."""
        return (1 << self.m) - 1

    def power(self, exponent: int) -> int:
        """``alpha ** exponent``, for any integer exponent."""
        return self._exp[exponent % self.order]

    def log(self, value: int) -> int:
        """The exponent e with ``alpha ** e == value``, for a nonzero element."""
        if not 0 < value <= self.order:
            raise ValueError("only nonzero field elements have a logarithm")
        return self._log[value]

    def multiply(self, left: int, right: int) -> int:
        """Multiply two field elements."""
        if left == 0 or right == 0:
            return 0
        return self._exp[(self._log[left] + self._log[right]) % self.order]

    def inverse(self, value: int) -> int:
        """The multiplicative inverse of a nonzero element."""
        return self.power(-self.log(value))
