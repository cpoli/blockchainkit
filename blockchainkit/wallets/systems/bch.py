"""BCH codes (Hocquenghem, 1959; Bose and Ray-Chaudhuri, 1960).

A binary BCH code of length n = 2**m - 1 treats a word of n bits as a
polynomial over GF(2) and accepts exactly the multiples of a generator g(x)
chosen to vanish at alpha, alpha**2, ..., alpha**(2t) in GF(2**m). Any
nonzero codeword then has at least 2t + 1 nonzero bits (the BCH bound), so
up to t flipped bits are corrected and up to 2t detected. Decoding computes
the syndromes ``S_j = r(alpha**j)``, finds the error-locator polynomial with
the Berlekamp-Massey algorithm, and finds its roots by trying every
position (Chien's search).

Bech32's checksum is a BCH code too, over GF(32) rather than GF(2): see
:mod:`blockchainkit.wallets.systems.bech32`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from blockchainkit._validation import integer
from blockchainkit.wallets.core.base import BCHDecoding
from blockchainkit.wallets.utils.galois import GaloisField


def _multiply_binary(left: int, right: int) -> int:
    """Multiply two polynomials over GF(2), given as bit masks."""
    product = 0
    while right:
        if right & 1:
            product ^= left
        left <<= 1
        right >>= 1
    return product


def _remainder_binary(dividend: int, divisor: int) -> int:
    """The remainder of polynomial division over GF(2)."""
    degree = divisor.bit_length() - 1
    while dividend.bit_length() - 1 >= degree:
        dividend ^= divisor << (dividend.bit_length() - 1 - degree)
    return dividend


def minimal_polynomial(field_: GaloisField, exponent: int) -> int:
    """The minimal polynomial over GF(2) of ``alpha ** exponent``, as a bit mask.

    Its roots are the conjugates ``alpha ** (exponent * 2**j)``, the
    cyclotomic coset of the exponent.

    Examples
    --------
    >>> from blockchainkit.wallets import minimal_polynomial
    >>> from blockchainkit.wallets.utils import GaloisField
    >>> bin(minimal_polynomial(GaloisField(4), 1))
    '0b10011'
    """
    integer(exponent, "exponent")
    coset, e = [], exponent % field_.order
    while e not in coset:
        coset.append(e)
        e = 2 * e % field_.order
    coefficients = [1]  # Lowest degree first, entries in GF(2**m).
    for c in coset:
        root = field_.power(c)
        shifted = [0, *coefficients]
        for i, a in enumerate(coefficients):
            shifted[i] ^= field_.multiply(a, root)
        coefficients = shifted
    return sum(bit << i for i, bit in enumerate(coefficients))


@dataclass(frozen=True)
class BCHCode:
    """A narrow-sense binary BCH code of length ``2**m - 1`` correcting ``t`` errors.

    Parameters
    ----------
    m : int
        Field degree, 3 to 8, so n is 7 to 255.
    t : int
        Errors to correct; the designed distance is ``2t + 1``.

    Examples
    --------
    >>> from blockchainkit.wallets import BCHCode
    >>> code = BCHCode(4, 2)
    >>> code.n, code.k
    (15, 7)
    >>> word = list(code.encode([1, 0, 1, 1, 0, 0, 1]))
    >>> word[0] ^= 1; word[9] ^= 1
    >>> code.decode(word).message
    (1, 0, 1, 1, 0, 0, 1)
    """

    m: int
    t: int
    galois: GaloisField = field(init=False, repr=False, compare=False)
    generator: int = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        integer(self.t, "t", 1)
        field_ = GaloisField(self.m)
        generator, used = 1, set()
        for i in range(1, 2 * self.t + 1):
            factor = minimal_polynomial(field_, i)
            if factor not in used:
                used.add(factor)
                generator = _multiply_binary(generator, factor)
        if generator.bit_length() - 1 >= field_.order:
            raise ValueError("t is too large: no message bits are left")
        object.__setattr__(self, "galois", field_)
        object.__setattr__(self, "generator", generator)

    @property
    def n(self) -> int:
        """Codeword length in bits, ``2**m - 1``."""
        return self.galois.order

    @property
    def k(self) -> int:
        """The message length in bits, n minus the generator's degree."""
        return self.n - (self.generator.bit_length() - 1)

    @property
    def designed_distance(self) -> int:
        """``2t + 1``, a lower bound on the distance between two codewords."""
        return 2 * self.t + 1

    def encode(self, message: Sequence[int]) -> tuple[int, ...]:
        """Append ``n - k`` check bits to ``k`` message bits (systematic encoding).

        The codeword is ``m(x) x**(n-k)`` plus its remainder modulo g(x), a
        multiple of g(x) that starts with the message.
        """
        bits = _bits(message, self.k, "message")
        shifted = _to_int(bits) << (self.n - self.k)
        return _to_bits(shifted ^ _remainder_binary(shifted, self.generator), self.n)

    def is_codeword(self, word: Sequence[int]) -> bool:
        """True if g(x) divides the word."""
        return _remainder_binary(_to_int(_bits(word, self.n, "word")), self.generator) == 0

    def syndromes(self, word: Sequence[int]) -> tuple[int, ...]:
        """``S_j = r(alpha**j)`` for j = 1, ..., 2t; all zero for a codeword."""
        bits = _bits(word, self.n, "word")
        powers = [self.n - 1 - i for i, bit in enumerate(bits) if bit]
        result = []
        for j in range(1, 2 * self.t + 1):
            s = 0
            for p in powers:
                s ^= self.galois.power(j * p)
            result.append(s)
        return tuple(result)

    def decode(self, word: Sequence[int]) -> BCHDecoding:
        """Correct up to t flipped bits with Berlekamp-Massey and Chien's search."""
        bits = list(_bits(word, self.n, "word"))
        syndromes = self.syndromes(bits)
        locator, degree = self._berlekamp_massey(syndromes)
        positions = []
        for p in range(self.n):
            x = self.galois.power(-p)  # A root alpha**(-p) means an error at x**p.
            value, x_power = 0, 1
            for coefficient in locator:
                value ^= self.galois.multiply(coefficient, x_power)
                x_power = self.galois.multiply(x_power, x)
            if value == 0:
                positions.append(self.n - 1 - p)
        if len(positions) != degree:
            return BCHDecoding(tuple(bits[: self.k]), tuple(bits), (), False)
        for i in positions:
            bits[i] ^= 1
        return BCHDecoding(tuple(bits[: self.k]), tuple(bits), tuple(sorted(positions)), True)

    def _berlekamp_massey(self, syndromes: tuple[int, ...]) -> tuple[list[int], int]:
        """The error-locator polynomial, lowest degree first, and its degree L."""
        f = self.galois
        locator, previous = [1], [1]
        length, shift, last = 0, 1, 1
        for step, s in enumerate(syndromes):
            discrepancy = s
            for i in range(1, length + 1):
                discrepancy ^= f.multiply(locator[i], syndromes[step - i])
            if discrepancy == 0:
                shift += 1
                continue
            scale = f.multiply(discrepancy, f.inverse(last))
            updated = locator + [0] * (len(previous) + shift - len(locator))
            for i, coefficient in enumerate(previous):
                updated[i + shift] ^= f.multiply(scale, coefficient)
            if 2 * length <= step:
                previous, length, last, shift = locator, step + 1 - length, discrepancy, 1
            else:
                shift += 1
            locator = updated
        return locator, length


def _bits(values: Sequence[int], length: int, name: str) -> tuple[int, ...]:
    bits = tuple(values)
    if len(bits) != length:
        raise ValueError(f"{name} must have {length} bits")
    if any(type(b) is not int or b not in (0, 1) for b in bits):
        raise ValueError(f"{name} must contain only the integers 0 and 1")
    return bits


def _to_int(bits: Sequence[int]) -> int:
    value = 0
    for bit in bits:
        value = value << 1 | bit
    return value


def _to_bits(value: int, length: int) -> tuple[int, ...]:
    return tuple(value >> (length - 1 - i) & 1 for i in range(length))
