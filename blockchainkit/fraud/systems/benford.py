"""Benford's law (Newcomb 1881, Benford 1938) and testing figures for fabrication.

In many collections of naturally occurring numbers, such as populations,
prices or payment amounts, the leading digit is 1 almost a third of the
time and 9 less than one time in twenty. A quantity spread evenly on a
logarithmic scale over several orders of magnitude has first digit
:math:`d` with probability :math:`\\log_{10}(1 + 1/d)`. People who invent
numbers spread their first digits far more evenly, which is why auditors,
following Nigrini, test reported figures against the law.
"""

import math
from collections.abc import Iterable

from blockchainkit._validation import integer
from blockchainkit.fraud.core.base import BenfordTest

DIGITS = tuple(range(1, 10))
"""The possible leading digits."""


def benford_probability(digit: int) -> float:
    """Probability that the leading digit is ``digit``: :math:`\\log_{10}(1 + 1/d)`.

    Examples
    --------
    >>> from blockchainkit.fraud import benford_probability
    >>> round(benford_probability(1), 3), round(benford_probability(9), 3)
    (0.301, 0.046)
    """
    integer(digit, "digit", 1)
    if digit > 9:
        raise ValueError("digit must be in 1..9")
    return math.log10(1 + 1 / digit)


def first_digit(value: float) -> int:
    """The leading nonzero digit of a positive number.

    Examples
    --------
    >>> from blockchainkit.fraud import first_digit
    >>> first_digit(314.15), first_digit(0.0072)
    (3, 7)
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be a real number")
    if not 0 < value < float("inf"):
        raise ValueError("value must be positive and finite")
    return int(f"{value:.14e}"[0])


def chi_square_survival(statistic: float, degrees: int) -> float:
    """Chance that a chi-square variable with an even number of ``degrees`` exceeds ``statistic``.

    For :math:`2k` degrees of freedom it is
    :math:`e^{-x/2} \\sum_{i<k} (x/2)^i / i!`, a Poisson tail.
    """
    integer(degrees, "degrees", 2)
    if degrees % 2:
        raise ValueError("degrees must be even")
    if statistic < 0:
        raise ValueError("statistic must be non-negative")
    half = statistic / 2
    return math.exp(-half) * sum(half**i / math.factorial(i) for i in range(degrees // 2))


def benford_test(values: Iterable[float]) -> BenfordTest:
    """Compare the leading digits of ``values`` with Benford's law.

    Returns
    -------
    BenfordTest
        Pearson's chi-square statistic and its p-value, and Nigrini's mean
        absolute deviation. Large samples fail the chi-square test for
        small departures, so Nigrini judges conformity by the deviation.

    Examples
    --------
    >>> from blockchainkit.fraud import benford_test
    >>> test = benford_test(2**k for k in range(1, 1001))
    >>> test.counts[0], test.conformity
    (301, 'close')
    """
    counts = [0] * 9
    for value in values:
        counts[first_digit(value) - 1] += 1
    n = sum(counts)
    if n == 0:
        raise ValueError("values must not be empty")
    expected = tuple(benford_probability(d) for d in DIGITS)
    chi_square = sum((c - n * p) ** 2 / (n * p) for c, p in zip(counts, expected, strict=True))
    mad = sum(abs(c / n - p) for c, p in zip(counts, expected, strict=True)) / 9
    return BenfordTest(tuple(counts), expected, chi_square, chi_square_survival(chi_square, 8), mad)
