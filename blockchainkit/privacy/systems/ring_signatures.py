"""Ring signatures: signing for a group chosen on the spot (Rivest, Shamir and Tauman, 2001).

A ring signature convinces anyone that one of the listed public keys
signed, without revealing which. Unlike a group signature there is no
manager and no setup: the signer picks the other members' public keys
itself, and they need not know. The signature is a closed ring of
challenges: each member's challenge is the hash of the previous member's
commitment, and the signer's secret key is what lets it close the ring.

For keys :math:`y_i = g^{x_i}` and signer :math:`s`, the signer picks
:math:`u` and starts the ring at :math:`c_{s+1} = H(m, g^u)`; every other
member gets a random response :math:`r_i` and
:math:`c_{i+1} = H(m, g^{r_i} y_i^{c_i})`. Only the signer can then answer
:math:`r_s = u - x_s c_s`, which makes :math:`g^{r_s} y_s^{c_s} = g^u`.

This is the discrete-log construction of Abe, Ohkubo and Suzuki (2002),
which Monero's signatures descend from. Rivest, Shamir and Tauman built
their ring from RSA trapdoor permutations and a symmetric cipher.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.constants import RING_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.privacy.core.base import RingSignature
from blockchainkit.privacy.utils.groups import hash_to_scalar


def _check_ring(ring: Sequence[int], group: DHGroup) -> None:
    if not ring:
        raise ValueError("the ring needs at least one member")
    for key in ring:
        integer(key, "public key", 2)
        if key >= group.p or pow(key, group.q, group.p) != 1:
            raise ValueError("every ring member must be a key in the group")


def _challenge(message: bytes, ring: Sequence[int], commitment: int, group: DHGroup) -> int:
    return hash_to_scalar(RING_DOMAIN, message.hex(), list(ring), commitment, group=group)


def ring_sign(
    message: bytes,
    ring: Sequence[int],
    index: int,
    secret: int,
    *,
    seed: int = 0,
    base: int | None = None,
    group: DHGroup = TEACHING_GROUP,
) -> RingSignature:
    """Sign ``message`` as one of ``ring``, using the secret key of member ``index``.

    Parameters
    ----------
    message : bytes
        What is signed.
    ring : sequence of int
        Public keys ``base**x_i``, the signer's among them.
    index : int
        The signer's position in the ring.
    secret : int
        The signer's private key.
    seed : int
        Seeds the nonce and the other members' responses.
    base : int, optional
        The generator of the keys; ``group.g`` by default.
    group : DHGroup
        The group of the keys.

    Raises
    ------
    ValueError
        ``secret`` is not the private key of member ``index``.

    Examples
    --------
    >>> from blockchainkit.privacy import ring_sign, ring_verify
    >>> from blockchainkit.crypto import TEACHING_GROUP as G
    >>> ring = [G.public(x) for x in (11, 22, 33)]
    >>> ring_verify(b"hi", ring, ring_sign(b"hi", ring, 1, 22))
    True
    """
    _check_ring(ring, group)
    integer(index, "index")
    integer(secret, "secret", 1)
    check_seed(seed)
    g = group.g if base is None else base
    p, q, n = group.p, group.q, len(ring)
    if index >= n or pow(g, secret, p) != ring[index]:
        raise ValueError("secret is not the key of the ring member at index")
    rng = Random(seed)
    nonce = rng.randrange(1, q)
    challenges, responses = [0] * n, [0] * n
    i = (index + 1) % n
    challenges[i] = _challenge(message, ring, pow(g, nonce, p), group)
    while i != index:
        responses[i] = rng.randrange(q)
        commitment = pow(g, responses[i], p) * pow(ring[i], challenges[i], p) % p
        i = (i + 1) % n
        challenges[i] = _challenge(message, ring, commitment, group)
    responses[index] = (nonce - secret * challenges[index]) % q
    return RingSignature(challenges[0], tuple(responses))


def ring_verify(
    message: bytes,
    ring: Sequence[int],
    signature: RingSignature,
    *,
    base: int | None = None,
    group: DHGroup = TEACHING_GROUP,
) -> bool:
    """Check that one member of ``ring`` signed ``message``: the challenges close the ring."""
    _check_ring(ring, group)
    if len(signature.responses) != len(ring):
        return False
    g = group.g if base is None else base
    p = group.p
    challenge = signature.challenge
    for key, response in zip(ring, signature.responses, strict=True):
        commitment = pow(g, response, p) * pow(key, challenge, p) % p
        challenge = _challenge(message, ring, commitment, group)
    return challenge == signature.challenge
