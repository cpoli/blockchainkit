"""Textbook Diffie--Hellman, RSA, and RSA blinding for small experiments.

These deliberately expose the mathematics. They are not encryption APIs
for sensitive data: textbook RSA has no padding and DH has no authentication.
"""

from dataclasses import dataclass
from math import gcd

from blockchainkit._validation import integer
from blockchainkit.crypto.utils.primes import is_prime


@dataclass(frozen=True)
class DHGroup:
    """A prime-order subgroup of the multiplicative group modulo ``p``.

    Parameters
    ----------
    p, q : int
        Small primes (below 2**64) with q dividing p-1.
    g : int
        Nonidentity generator of order q.

    Examples
    --------
    >>> from blockchainkit.crypto import DHGroup
    >>> group = DHGroup()
    >>> group.shared(group.public(7), 3) == group.shared(group.public(3), 7)
    True
    """

    p: int = 23
    q: int = 11
    g: int = 2

    def __post_init__(self) -> None:
        if not is_prime(self.p) or not is_prime(self.q) or (self.p - 1) % self.q:
            raise ValueError("p and q must be primes with q dividing p-1")
        integer(self.g, "g", 2)
        if self.g >= self.p or pow(self.g, self.q, self.p) != 1:
            raise ValueError("g must generate the subgroup of order q")

    def public(self, private: int) -> int:
        """Return g**private modulo p, for private in [1, q)."""
        integer(private, "private", 1)
        if private >= self.q:
            raise ValueError("private must be below q")
        return pow(self.g, private, self.p)

    def shared(self, peer_public: int, private: int) -> int:
        """Derive a shared group element after validating subgroup membership.

        This is not a key derivation function and does not authenticate peers.
        """
        self.public(private)
        integer(peer_public, "peer_public", 2)
        if peer_public >= self.p or pow(peer_public, self.q, self.p) != 1:
            raise ValueError("invalid peer public element")
        return pow(peer_public, private, self.p)


@dataclass(frozen=True)
class RSAKeyPair:
    """Textbook RSA exponents: modulus n, public e, and private d.

    Construct with :func:`rsa_keypair`; tiny factors make the algebra visible.
    """

    n: int
    e: int
    d: int

    def encrypt(self, message: int) -> int:
        """Apply the public exponent to an integer in [0, n)."""
        return _rsa_apply(message, self.e, self.n)

    def decrypt(self, ciphertext: int) -> int:
        """Apply the private exponent; no padding or timing protections."""
        return _rsa_apply(ciphertext, self.d, self.n)


def _rsa_apply(value: int, exponent: int, modulus: int) -> int:
    integer(value, "value")
    if value >= modulus:
        raise ValueError("value must be below n")
    return pow(value, exponent, modulus)


def rsa_keypair(p: int = 61, q: int = 53, e: int = 17) -> RSAKeyPair:
    """Build a textbook key pair from distinct primes below 2**64.

    >>> from blockchainkit.crypto import rsa_keypair
    >>> key = rsa_keypair()
    >>> key.encrypt(65), key.decrypt(2790)
    (2790, 65)
    """
    if not is_prime(p) or not is_prime(q) or p == q:
        raise ValueError("p and q must be distinct primes below 2**64")
    phi = (p - 1) * (q - 1)
    integer(e, "e", 2)
    if e >= phi or gcd(e, phi) != 1:
        raise ValueError("e must be below phi(n) and coprime to it")
    return RSAKeyPair(p * q, e, pow(e, -1, phi))


def rsa_blind(message: int, factor: int, key: RSAKeyPair) -> int:
    """Return m*r**e mod n for a caller-selected invertible blinding factor.

    The signer applies its private exponent to this blinded integer.
    """
    _rsa_apply(message, key.e, key.n)
    integer(factor, "factor", 1)
    if factor >= key.n or gcd(factor, key.n) != 1:
        raise ValueError("factor must be invertible modulo n and below n")
    return message * pow(factor, key.e, key.n) % key.n


def rsa_unblind(blind_signature: int, factor: int, key: RSAKeyPair) -> int:
    """Remove blinding so signature**e mod n equals the original message."""
    rsa_blind(blind_signature, factor, key)
    return blind_signature * pow(factor, -1, key.n) % key.n
