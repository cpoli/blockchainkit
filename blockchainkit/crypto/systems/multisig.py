"""MuSig key aggregation (Maxwell, Poelstra, Seurin and Wuille, 2018).

Schnorr signatures add: if every signer uses nonce k_i and key x_i, the sum
of their responses is a valid signature for the *sum* of their public keys.
Summing keys naively is unsafe: an attacker who announces
``Q_rogue = xG - Q_honest`` makes the sum equal ``xG``, a key they control
alone. MuSig weights each key by ``a_i = H(L, Q_i)``, a hash of the whole
key list L, so no participant can choose their key to cancel the others.

Teaching simplification: :func:`musig_sign` plays every signer in one
process. Real MuSig exchanges nonce commitments first (or uses MuSig2's two
nonces); without that round, a malicious co-signer can bias the joint nonce.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.constants import MUSIG_DOMAIN
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
from blockchainkit.crypto.systems.signatures import challenge


def musig_coefficients(
    publics: Sequence[tuple[int, int]], curve: Curve = SECP256K1
) -> tuple[int, ...]:
    """Return ``a_i = H(L || Q_i) mod n`` for each key, with L the encoded key list."""
    if not publics:
        raise ValueError("need at least one public key")
    key_list = b"".join(encode_point(q, curve) for q in publics)
    return tuple(
        int.from_bytes(sha256(MUSIG_DOMAIN + key_list + encode_point(q, curve)), "big")
        % curve.order
        for q in publics
    )


def aggregate_public_keys(
    publics: Sequence[tuple[int, int]], curve: Curve = SECP256K1
) -> tuple[int, int]:
    """Return the MuSig aggregate key ``sum(a_i * Q_i)``.

    >>> from blockchainkit.crypto import aggregate_public_keys, public_key
    >>> len(aggregate_public_keys([public_key(3), public_key(5)]))
    2
    """
    total = None
    for a, q in zip(musig_coefficients(publics, curve), publics, strict=True):
        total = add(total, multiply(a, q, curve), curve)
    # A weighted sum of honest keys is the point at infinity only with
    # negligible probability (a hash would have to cancel the keys exactly).
    assert total is not None
    return total


def musig_sign(
    message: bytes,
    privates: Sequence[int],
    nonces: Sequence[int],
    curve: Curve = SECP256K1,
) -> SchnorrSignature:
    """Produce one Schnorr signature valid for the aggregate of the signers' keys.

    Each signer i contributes ``R_i = k_i G`` and ``s_i = k_i + c * a_i * x_i``
    with the shared challenge ``c = H(R, Q_agg, m)``; the signature is
    ``(sum R_i, sum s_i)`` and verifies with :func:`~blockchainkit.crypto.systems.signatures.verify`
    against :func:`aggregate_public_keys`.

    Examples
    --------
    >>> from blockchainkit.crypto import musig_sign, aggregate_public_keys, public_key, verify
    >>> signature = musig_sign(b"m", [3, 5], [11, 13])
    >>> verify(b"m", signature, aggregate_public_keys([public_key(3), public_key(5)]))
    True
    """
    if len(privates) != len(nonces) or not privates:
        raise ValueError("need one nonce per signer, and at least one signer")
    for nonce in nonces:
        integer(nonce, "nonce", 1)
    publics = [public_key(x, curve) for x in privates]
    coefficients = musig_coefficients(publics, curve)
    aggregate = aggregate_public_keys(publics, curve)
    commitment = None
    for nonce in nonces:
        commitment = add(commitment, public_key(nonce, curve), curve)
    if commitment is None:
        raise ValueError("the joint nonce is the point at infinity; choose other nonces")
    c = challenge(message, commitment, aggregate, curve)
    response = sum(k + c * a * x for k, a, x in zip(nonces, coefficients, privates, strict=True))
    return SchnorrSignature(commitment, response % curve.order)
