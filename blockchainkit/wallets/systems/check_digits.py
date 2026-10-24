r"""Check digits: Luhn's (1954) and Verhoeff's (1969).

A check digit is appended so that a number typed with a mistake fails a
test. Verhoeff's study of Dutch post-office data found that single wrong
digits and swaps of two adjacent digits make up most typing errors (about
80% and 10%). A sum modulo 10 catches every single error but no swap,
because addition commutes. Luhn's scheme, used on payment cards, doubles
every second digit, which catches every swap but one: 09 and 90.

Verhoeff's scheme catches them all, by computing in a group that does not
commute: the dihedral group D5 of the ten symmetries of a pentagon, with
the digits 0-4 as rotations and 5-9 as reflections. Digit i (counting from
the right, check digit at i = 0) is first permuted by
:math:`\sigma^i`, where :math:`\sigma` is a fixed permutation, and the
number is valid when the product is the identity:

.. math::

   \sigma^{0}(a_0) * \sigma^{1}(a_1) * \cdots * \sigma^{k}(a_k) = 0 .
"""

from collections.abc import Callable

from blockchainkit._validation import integer
from blockchainkit.wallets.core.base import DetectionRates


def _dihedral(a: int, b: int) -> int:
    """Compose two symmetries of the pentagon: 0-4 are rotations, 5-9 reflections."""
    if a < 5 and b < 5:
        return (a + b) % 5
    if a < 5:
        return 5 + (a + b - 5) % 5
    if b < 5:
        return 5 + (a - 5 - b) % 5
    return (a - b) % 5


_SIGMA = (1, 5, 7, 6, 2, 8, 3, 0, 9, 4)
_PERMUTATIONS = [tuple(range(10))]
for _ in range(7):
    _PERMUTATIONS.append(tuple(_SIGMA[d] for d in _PERMUTATIONS[-1]))
del _
_INVERSE = tuple(next(b for b in range(10) if _dihedral(a, b) == 0) for a in range(10))


def _digits(number: str) -> list[int]:
    if not isinstance(number, str):
        raise TypeError("number must be a string of digits")
    if not number or not number.isascii() or not number.isdigit():
        raise ValueError("number must be a non-empty string of digits 0-9")
    return [int(c) for c in number]


def verhoeff_digit(number: str) -> str:
    """The Verhoeff check digit to append to ``number``.

    Examples
    --------
    >>> from blockchainkit.wallets import verhoeff_digit, verhoeff_valid
    >>> verhoeff_digit("236")
    '3'
    >>> verhoeff_valid("2363"), verhoeff_valid("2633")
    (True, False)
    """
    c = 0
    for i, d in enumerate(reversed(_digits(number))):
        c = _dihedral(c, _PERMUTATIONS[(i + 1) % 8][d])
    return str(_INVERSE[c])


def verhoeff_valid(number: str) -> bool:
    """True if ``number`` ends with its correct Verhoeff check digit."""
    c = 0
    for i, d in enumerate(reversed(_digits(number))):
        c = _dihedral(c, _PERMUTATIONS[i % 8][d])
    return c == 0


def _luhn_sum(digits: list[int], doubled_parity: int) -> int:
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == doubled_parity:
            d = 2 * d - 9 if d > 4 else 2 * d
        total += d
    return total


def luhn_digit(number: str) -> str:
    """The Luhn check digit to append to ``number``, as on payment cards.

    Examples
    --------
    >>> from blockchainkit.wallets import luhn_digit
    >>> luhn_digit("7992739871")
    '3'
    """
    return str(-_luhn_sum(_digits(number), 0) % 10)


def luhn_valid(number: str) -> bool:
    """True if ``number`` ends with its correct Luhn check digit."""
    return _luhn_sum(_digits(number), 1) % 10 == 0


def sum_digit(number: str) -> str:
    """The digit that makes the digit sum a multiple of 10: catches no swap."""
    return str(-sum(_digits(number)) % 10)


def sum_valid(number: str) -> bool:
    """True if the digits of ``number`` add up to a multiple of 10."""
    return sum(_digits(number)) % 10 == 0


CHECK_SCHEMES: dict[str, tuple[Callable[[str], str], Callable[[str], bool]]] = {
    "sum": (sum_digit, sum_valid),
    "luhn": (luhn_digit, luhn_valid),
    "verhoeff": (verhoeff_digit, verhoeff_valid),
}
"""dict: Each scheme's name, with its check-digit and validation functions."""


def detection_rates(scheme: str, length: int = 3) -> DetectionRates:
    """Measure a scheme on every number of ``length`` digits, against every error.

    Each number gets its check digit; then every single wrong digit and
    every swap of two adjacent different digits, check digit included, is
    tried on it.

    Examples
    --------
    >>> from blockchainkit.wallets import detection_rates
    >>> detection_rates("verhoeff", 2)
    DetectionRates(scheme='verhoeff', single_errors=1.0, transpositions=1.0)
    >>> round(detection_rates("luhn", 2).transpositions, 3)
    0.978
    """
    if scheme not in CHECK_SCHEMES:
        raise ValueError(f"scheme must be one of {sorted(CHECK_SCHEMES)}")
    integer(length, "length", 1)
    if length > 4:
        raise ValueError("length is at most 4: every number is tried")
    check, valid = CHECK_SCHEMES[scheme]
    singles = [0, 0]
    swaps = [0, 0]
    for value in range(10**length):
        number = f"{value:0{length}d}"
        word = number + check(number)
        for i, c in enumerate(word):
            for d in "0123456789":
                if d != c:
                    singles[0] += not valid(word[:i] + d + word[i + 1 :])
                    singles[1] += 1
        for i in range(len(word) - 1):
            if word[i] != word[i + 1]:
                swapped = word[:i] + word[i + 1] + word[i] + word[i + 2 :]
                swaps[0] += not valid(swapped)
                swaps[1] += 1
    return DetectionRates(scheme, singles[0] / singles[1], swaps[0] / swaps[1])
