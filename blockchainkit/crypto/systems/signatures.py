"""Educational Schnorr signatures and interactive proof transcripts.

This is a domain-separated teaching scheme, not Bitcoin BIP-340. Python
curve arithmetic is variable-time. Explicit nonces exist for experiments;
reusing a nonce reveals the private key.
"""

import secrets

from blockchainkit._validation import integer
from blockchainkit.constants import SCHNORR_DOMAIN
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.curves import (
    SECP256K1,
    Curve,
    add,
    encode_point,
    multiply,
    public_key,
)
from blockchainkit.crypto.systems.hashing import sha256


def challenge(
    message: bytes,
    commitment: tuple[int, int],
    public: tuple[int, int],
    curve: Curve = SECP256K1,
) -> int:
    """Hash the curve parameters, public key, commitment, and message to a scalar."""
    if not isinstance(message, bytes):
        raise TypeError("message must be bytes")
    domain = f"{SCHNORR_DOMAIN}:{curve.p}:{curve.a}:{curve.b}:{curve.order}:".encode()
    framed = domain + encode_point(curve.generator, curve)
    framed += encode_point(commitment, curve) + encode_point(public, curve) + message
    return int.from_bytes(sha256(framed), "big") % curve.order


def sign(
    message: bytes,
    private: int,
    *,
    nonce: int | None = None,
    curve: Curve = SECP256K1,
) -> SchnorrSignature:
    """Sign with s = k + H(R, Q, m)*x modulo the subgroup order.

    Parameters
    ----------
    message : bytes
        Exact bytes to authenticate.
    private : int
        Secret scalar x.
    nonce : int, optional
        Experiment-only scalar k. Defaults to system randomness.
    curve : Curve
        Defaults to secp256k1; tiny curves illustrate algebra, not security.

    Returns
    -------
    SchnorrSignature
        Commitment R=kG and response s.

    Examples
    --------
    >>> from blockchainkit.crypto import sign, verify, public_key
    >>> signature = sign(b"lesson", 7, nonce=11)
    >>> verify(b"lesson", signature, public_key(7))
    True
    """
    public = public_key(private, curve)
    if nonce is None:
        nonce = secrets.randbelow(curve.order - 1) + 1
    commitment = public_key(nonce, curve)
    c = challenge(message, commitment, public, curve)
    return SchnorrSignature(commitment, (nonce + c * private) % curve.order)


def verify_transcript(
    public: tuple[int, int],
    commitment: tuple[int, int],
    challenge_scalar: int,
    response: int,
    curve: Curve = SECP256K1,
) -> bool:
    """Check the interactive Schnorr equation sG = R + cQ.

    An accepting transcript is not itself proof of a live interaction:
    choosing c and s first permits simulation via R=sG-cQ. Soundness needs
    an unpredictable verifier challenge after the prover commits to R.
    """
    for scalar in (challenge_scalar, response):
        if type(scalar) is not int or not 0 <= scalar < curve.order:
            return False
    for point in (public, commitment):
        if point is None or not curve.contains(point):
            return False
        if multiply(curve.order, point, curve) is not None:
            return False
    return multiply(response, curve.generator, curve) == add(
        commitment, multiply(challenge_scalar, public, curve), curve
    )


def verify(
    message: bytes,
    signature: SchnorrSignature,
    public: tuple[int, int],
    curve: Curve = SECP256K1,
) -> bool:
    """Verify a Schnorr signature; malformed points or scalars return False."""
    try:
        c = challenge(message, signature.commitment, public, curve)
        return verify_transcript(public, signature.commitment, c, signature.response, curve)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return False


def recover_reused_nonce_key(
    first: SchnorrSignature,
    second: SchnorrSignature,
    first_challenge: int,
    second_challenge: int,
    order: int = SECP256K1.order,
) -> int:
    """Recover x=(s1-s2)/(c1-c2) when two signatures reuse their nonce.

    This demonstrates special soundness and why nonce reuse is catastrophic.
    The caller supplies the actual challenges derived from the two messages.
    """
    integer(order, "order", 2)
    if first.commitment != second.commitment:
        raise ValueError("commitments must be identical")
    for scalar in (first.response, second.response, first_challenge, second_challenge):
        integer(scalar, "scalar")
        if scalar >= order:
            raise ValueError("scalar must be below order")
    delta = (first_challenge - second_challenge) % order
    if delta == 0:
        raise ValueError("challenges must differ modulo order")
    return (first.response - second.response) * pow(delta, -1, order) % order
