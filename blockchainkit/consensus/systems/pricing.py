"""Pricing via processing (Dwork and Naor 1992): make each message cost computation.

To fight junk mail, Dwork and Naor proposed that a sender compute a
*pricing function*, moderately hard to evaluate but easy to check, for each
message. One of their examples is a square root modulo a prime: computing
it takes an exponentiation, checking it takes one multiplication.
Back's Hashcash later used hash preimages for the same purpose, and
Bitcoin's proof of work descends from that.
"""

from blockchainkit._validation import integer
from blockchainkit.consensus.core.base import SquareRootResult
from blockchainkit.crypto.utils.primes import is_prime


def modular_square_root(value: int, prime: int) -> SquareRootResult:
    """Compute a square root modulo a prime ``p = 3 (mod 4)``, counting multiplications.

    For such primes, ``value**((p + 1) / 4)`` is a square root of any
    quadratic residue. Square-and-multiply needs about ``1.5 log2 p``
    multiplications; checking the answer needs one.

    Raises
    ------
    ValueError
        ``prime`` is not a prime congruent to 3 modulo 4, or ``value`` has no
        square root (it is not a quadratic residue).

    Examples
    --------
    >>> from blockchainkit.consensus import modular_square_root
    >>> result = modular_square_root(4, 7)
    >>> result.root ** 2 % 7
    4
    """
    integer(value, "value")
    integer(prime, "prime", 3)
    if not is_prime(prime) or prime % 4 != 3:
        raise ValueError("prime must be a prime congruent to 3 modulo 4")
    exponent, base, root, multiplications = (prime + 1) // 4, value % prime, 1, 0
    while exponent:
        if exponent & 1:
            root = root * base % prime
            multiplications += 1
        base = base * base % prime
        multiplications += 1
        exponent >>= 1
    if root * root % prime != value % prime:
        raise ValueError("value is not a quadratic residue modulo prime")
    return SquareRootResult(root, multiplications)
