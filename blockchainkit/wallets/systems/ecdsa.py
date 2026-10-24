r"""ECDSA on secp256k1, the signature scheme Bitcoin and Ethereum use for accounts.

A signature on message hash z with key x and nonce k is

.. math::

   R = kG, \qquad r = R_x \bmod n, \qquad s = k^{-1}(z + r x) \bmod n,

and it verifies when :math:`(z s^{-1}) G + (r s^{-1}) Q` has x coordinate
r. Unlike Schnorr's :math:`s = k + c x`, the response multiplies the
secret nonce's inverse by the key, so signatures by several parties do not
simply add: see :mod:`blockchainkit.wallets.systems.threshold`. Nonces come
from RFC 6979 by default, and s is normalized to the lower half of
[1, n), as Bitcoin requires since BIP146 to stop third parties from
changing a transaction's ID by negating s.
"""

from blockchainkit._validation import integer
from blockchainkit.crypto.systems.curves import SECP256K1, add, multiply, public_key
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.signatures import deterministic_nonce
from blockchainkit.wallets.core.base import EcdsaSignature
from blockchainkit.wallets.utils.keys import PublicKey

_N = SECP256K1.order


def message_hash(message: bytes) -> int:
    """z: SHA-256 of the message as an integer modulo n."""
    if not isinstance(message, bytes):
        raise TypeError("message must be bytes")
    return int.from_bytes(sha256(message), "big") % _N


def ecdsa_signature(z: int, private: int, nonce: int) -> EcdsaSignature:
    """Assemble a signature from the hash, key and nonce: ``s = k**-1 (z + r x)``, low s."""
    r = public_key(nonce)[0] % _N
    s = pow(nonce, -1, _N) * (z + r * private) % _N
    if r == 0 or s == 0:
        raise ValueError("this nonce gives a degenerate signature; choose another")  # p < 2**-127
    return EcdsaSignature(r, min(s, _N - s))


def ecdsa_sign(message: bytes, private: int, *, nonce: int | None = None) -> EcdsaSignature:
    """Sign ``message`` with ECDSA; the nonce defaults to RFC 6979's.

    Examples
    --------
    >>> from blockchainkit.crypto import public_key
    >>> from blockchainkit.wallets import ecdsa_sign, ecdsa_verify
    >>> signature = ecdsa_sign(b"pay bob 5", 7)
    >>> ecdsa_verify(b"pay bob 5", signature, public_key(7))
    True
    """
    integer(private, "private", 1)
    if private >= _N:
        raise ValueError("private key must be below the curve order")
    if nonce is None:
        nonce = deterministic_nonce(private, message)
    integer(nonce, "nonce", 1)
    if nonce >= _N:
        raise ValueError("nonce must be below the curve order")
    return ecdsa_signature(message_hash(message), private, nonce)


def ecdsa_verify(message: bytes, signature: EcdsaSignature, public: PublicKey) -> bool:
    """Check an ECDSA signature; malformed keys or scalars return False."""
    try:
        r, s = signature.r, signature.s
        integer(r, "r", 1)
        integer(s, "s", 1)
        if r >= _N or s >= _N or not SECP256K1.contains(public) or public is None:
            return False
        w = pow(s, -1, _N)
        z = message_hash(message)
        point = add(
            multiply(z * w % _N, SECP256K1.generator, SECP256K1),
            multiply(r * w % _N, public, SECP256K1),
            SECP256K1,
        )
    except (TypeError, ValueError, AttributeError):
        return False
    return point is not None and point[0] % _N == r
