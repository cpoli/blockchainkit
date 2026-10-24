r"""Threshold ECDSA (Gennaro and Goldfeder, 2018).

A multisig script shows its policy on chain and costs one signature per
signer. A threshold signature is a single ordinary signature under a single
key, made by any t of n parties who each hold a Shamir share of a private
key that nobody ever computes. For Schnorr this is easy, since responses
add. ECDSA's :math:`s = k^{-1}(z + r x)` multiplies secrets, so the
parties need products of values that are split between them.

Gennaro and Goldfeder's protocol gets them with a two-party
*multiplicative-to-additive* (MtA) conversion: parties holding a and b end
with :math:`\alpha + \beta = ab` without revealing a or b. With nonce
shares :math:`k_i`, masks :math:`\gamma_i` and Lagrange-weighted key
shares :math:`w_i`, MtA gives additive shares of :math:`\delta = k\gamma`
and :math:`\sigma = kx`. Revealing :math:`\delta` leaks nothing, because
:math:`\gamma` hides :math:`k`, and

.. math::

   R = \delta^{-1} \sum_i \gamma_i G = k^{-1} G, \qquad
   s = \sum_i (z k_i + r \sigma_i) = k (z + r x),

which is an ECDSA signature with nonce :math:`k^{-1}`.

Teaching difference: the key is generated jointly with Feldman commitments
on secp256k1, but :func:`multiplicative_to_additive` is an ideal
functionality, a function that splits the product at random. The real
protocol runs MtA with Paillier encryption and zero-knowledge range proofs,
so that no party learns another's inputs, and it checks every step to
catch a cheating party.
"""

import random
from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit._validation import seed as _check_seed
from blockchainkit.crypto.systems.curves import SECP256K1, add, multiply, public_key
from blockchainkit.wallets.core.base import EcdsaSignature, KeyShares, ThresholdSigning
from blockchainkit.wallets.systems.ecdsa import message_hash

_N = SECP256K1.order


def _scalar(rng: random.Random) -> int:
    return rng.randrange(1, _N)


def threshold_keygen(threshold: int, parties: int, *, seed: int = 0) -> KeyShares:
    r"""Generate a key jointly: every party deals a Shamir sharing of a random secret.

    Party i picks a polynomial :math:`f_i` of degree ``threshold - 1``,
    publishes :math:`a_{ik} G` for its coefficients, and sends
    :math:`f_i(j)` to party j. Party j's share is :math:`\sum_i f_i(j)`; the
    joint key is :math:`\sum_i a_{i0} G`, and its private key
    :math:`\sum_i a_{i0}` is never assembled.

    Examples
    --------
    >>> from blockchainkit.wallets import threshold_keygen, verify_key_share
    >>> keys = threshold_keygen(2, 3, seed=1)
    >>> [verify_key_share(keys, i) for i in (1, 2, 3)]
    [True, True, True]
    """
    integer(threshold, "threshold", 1)
    integer(parties, "parties", threshold)
    _check_seed(seed)
    rng = random.Random(seed)
    polynomials = [[_scalar(rng) for _ in range(threshold)] for _ in range(parties)]
    commitments = tuple(tuple(public_key(a) for a in poly) for poly in polynomials)
    shares = tuple(
        (j, sum(_evaluate(poly, j) for poly in polynomials) % _N) for j in range(1, parties + 1)
    )
    joint = None
    for dealt in commitments:
        joint = add(joint, dealt[0], SECP256K1)
    # The dealt secrets sum to zero only with negligible probability.
    assert joint is not None
    return KeyShares(joint, threshold, shares, commitments)


def _evaluate(coefficients: Sequence[int], x: int) -> int:
    value = 0
    for a in reversed(coefficients):
        value = (value * x + a) % _N
    return value


def verify_key_share(keys: KeyShares, index: int) -> bool:
    """Feldman's check of party ``index``'s share against every dealer's commitments."""
    shares = dict(keys.shares)
    if index not in shares:
        raise ValueError(f"no party {index}")
    expected = None
    for dealt in keys.commitments:
        for k, commitment in enumerate(dealt):
            expected = add(expected, multiply(pow(index, k, _N), commitment, SECP256K1), SECP256K1)
    return public_key(shares[index]) == expected


def lagrange_coefficient(index: int, signers: Sequence[int]) -> int:
    r"""Shamir share to additive share: :math:`\lambda_i = \prod_{j \ne i} j / (j - i)`."""
    weight = 1
    for j in signers:
        if j != index:
            weight = weight * j * pow(j - index, -1, _N) % _N
    return weight


def multiplicative_to_additive(a: int, b: int, rng: random.Random) -> tuple[int, int]:
    """The MtA ideal functionality: random ``(alpha, beta)`` with ``alpha + beta = a b mod n``.

    In Gennaro and Goldfeder's protocol, the holder of a sends a under
    Paillier encryption; the holder of b computes ``E(a b - beta)`` by
    homomorphic operations for a random beta, and returns it.
    """
    beta = rng.randrange(_N)
    return (a * b - beta) % _N, beta


def threshold_sign(
    message: bytes, keys: KeyShares, signers: Sequence[int], *, seed: int = 0
) -> ThresholdSigning:
    """Sign ``message`` with the shares of ``signers``, at least ``keys.threshold`` of them.

    Parameters
    ----------
    message : bytes
        The message; it is hashed with SHA-256, as by
        :func:`~blockchainkit.wallets.systems.ecdsa.ecdsa_sign`.
    keys : KeyShares
        From :func:`threshold_keygen`.
    signers : sequence of int
        Distinct party indices.
    seed : int
        Seeds every party's nonce share, mask and MtA randomness.

    Returns
    -------
    ThresholdSigning
        Its signature verifies with
        :func:`~blockchainkit.wallets.systems.ecdsa.ecdsa_verify` under
        ``keys.public``.

    Examples
    --------
    >>> from blockchainkit.wallets import ecdsa_verify, threshold_keygen, threshold_sign
    >>> keys = threshold_keygen(2, 3, seed=1)
    >>> signing = threshold_sign(b"pay bob 5", keys, [1, 3], seed=2)
    >>> ecdsa_verify(b"pay bob 5", signing.signature, keys.public), signing.conversions
    (True, 4)
    """
    shares = dict(keys.shares)
    signers = tuple(signers)
    if len(set(signers)) != len(signers) or not set(signers) <= set(shares):
        raise ValueError("signers must be distinct parties of this key")
    if len(signers) < keys.threshold:
        raise ValueError(f"need at least {keys.threshold} signers")
    _check_seed(seed)
    rng = random.Random(seed)
    w = {i: lagrange_coefficient(i, signers) * shares[i] % _N for i in signers}
    k = {i: _scalar(rng) for i in signers}
    gamma = {i: _scalar(rng) for i in signers}
    delta = {i: k[i] * gamma[i] % _N for i in signers}
    sigma = {i: k[i] * w[i] % _N for i in signers}
    conversions = 0
    for i in signers:
        for j in signers:
            if i != j:
                for target, other in ((delta, gamma), (sigma, w)):
                    alpha, beta = multiplicative_to_additive(k[i], other[j], rng)
                    target[i] = (target[i] + alpha) % _N
                    target[j] = (target[j] + beta) % _N
                    conversions += 1
    joint_delta = sum(delta.values()) % _N
    gamma_point = None
    for i in signers:
        gamma_point = add(gamma_point, public_key(gamma[i]), SECP256K1)
    nonce_point = multiply(pow(joint_delta, -1, _N), gamma_point, SECP256K1)
    assert nonce_point is not None
    r = nonce_point[0] % _N
    z = message_hash(message)
    s = sum(z * k[i] + r * sigma[i] for i in signers) % _N
    # r or s is zero only with negligible probability, as for one signer.
    assert r and s
    return ThresholdSigning(EcdsaSignature(r, min(s, _N - s)), signers, conversions)
