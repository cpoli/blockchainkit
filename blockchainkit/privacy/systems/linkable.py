r"""Linkable ring signatures and key images: anonymous, but only once (Liu, Wei and Wong, 2004).

A ring signature hides the spender, so on its own it would let a coin be
spent twice: two signatures by the same key look unrelated. A *linkable*
ring signature adds a *key image* :math:`I = H_p(P)^x`, a value fixed by
the signer's key :math:`P = g^x` but not revealing it. Every signature by
that key carries the same image, so the ledger rejects the second spend,
yet nobody learns which ring member made either one.

The ring proves both statements with the same response, for each member
:math:`i` with challenge :math:`c_i` and response :math:`r_i`:

.. math::

   L_i = g^{r_i} P_i^{c_i}, \qquad R_i = H_p(P_i)^{r_i} I^{c_i},
   \qquad c_{i+1} = H(m, L_i, R_i).

Only the signer can close the ring with a single :math:`x` that serves
both. *MLSAG* (Noether, 2016) signs with one key per *column* for each
member at once, the same challenge chaining them; RingCT uses a second
column to prove amounts balance.

The key image here hashes the public key, as CryptoNote does, so it links
signatures across different rings; Liu, Wei and Wong hashed the ring, which
links only signatures over the same ring.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.constants import KEY_IMAGE_DOMAIN, RING_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.privacy.core.base import LinkableRingSignature
from blockchainkit.privacy.systems.ring_signatures import _check_ring
from blockchainkit.privacy.utils.groups import hash_to_group, hash_to_scalar


def _image_base(public: int, group: DHGroup) -> int:
    return hash_to_group(KEY_IMAGE_DOMAIN, public, group=group)


def key_image(secret: int, group: DHGroup = TEACHING_GROUP) -> int:
    """``H_p(P)**x`` for the key pair ``(x, P = g**x)``.

    >>> from blockchainkit.privacy import key_image
    >>> key_image(5) == key_image(5) != key_image(6)
    True
    """
    return pow(_image_base(group.public(secret), group), secret, group.p)


def _matrix(ring: Sequence[Sequence[int]], group: DHGroup) -> tuple[tuple[int, ...], ...]:
    rows = tuple(tuple(member) for member in ring)
    if not rows or not rows[0]:
        raise ValueError("the ring needs at least one member with at least one key")
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("every member needs the same number of keys")
    for column in zip(*rows, strict=True):
        _check_ring(column, group)
    return rows


def _bases(bases: Sequence[int] | None, width: int, group: DHGroup) -> tuple[int, ...]:
    if bases is None:
        return (group.g,) * width
    if len(bases) != width:
        raise ValueError("need one base per column")
    return tuple(bases)


def _hash(message: bytes, ring: tuple[tuple[int, ...], ...], image: int, *points: int) -> int:
    return hash_to_scalar(RING_DOMAIN, message.hex(), [list(r) for r in ring], image, *points)


def mlsag_sign(
    message: bytes,
    ring: Sequence[Sequence[int]],
    index: int,
    secrets: Sequence[int],
    *,
    seed: int = 0,
    bases: Sequence[int] | None = None,
    group: DHGroup = TEACHING_GROUP,
) -> LinkableRingSignature:
    """Sign as member ``index`` of a ring whose members each hold one key per column.

    Parameters
    ----------
    message : bytes
        What is signed.
    ring : sequence of sequence of int
        ``ring[i][j]`` is member ``i``'s public key in column ``j``.
    index : int
        The signer's position.
    secrets : sequence of int
        The signer's private keys, one per column.
    seed : int
        Seeds the nonces and the other members' responses.
    bases : sequence of int, optional
        The generator of each column; ``group.g`` for all by default. The
        key image is always taken in the first column.
    group : DHGroup
        The group of the keys.

    Raises
    ------
    ValueError
        A secret does not match the signer's key in its column.
    """
    rows = _matrix(ring, group)
    width = len(rows[0])
    gens = _bases(bases, width, group)
    integer(index, "index")
    check_seed(seed)
    p, q, n = group.p, group.q, len(rows)
    if index >= n or len(secrets) != width:
        raise ValueError("need a valid index and one secret per column")
    for secret, base, key in zip(secrets, gens, rows[index], strict=True):
        integer(secret, "secret", 1)
        if pow(base, secret, p) != key:
            raise ValueError("a secret is not the key of the ring member at index")
    image = pow(_image_base(rows[index][0], group), secrets[0], p)
    rng = Random(seed)
    nonces = [rng.randrange(1, q) for _ in range(width)]
    challenges = [0] * n
    responses = [[0] * width for _ in range(n)]
    i = (index + 1) % n
    first = pow(_image_base(rows[index][0], group), nonces[0], p)
    challenges[i] = _hash(
        message, rows, image, *(pow(b, u, p) for b, u in zip(gens, nonces, strict=True)), first
    )
    while i != index:
        responses[i] = [rng.randrange(q) for _ in range(width)]
        challenges[(i + 1) % n] = _hash(
            message, rows, image, *_points(rows[i], responses[i], challenges[i], gens, image, group)
        )
        i = (i + 1) % n
    responses[index] = [
        (u - x * challenges[index]) % q for u, x in zip(nonces, secrets, strict=True)
    ]
    return LinkableRingSignature(challenges[0], tuple(tuple(row) for row in responses), image)


def _points(
    keys: Sequence[int],
    responses: Sequence[int],
    challenge: int,
    gens: Sequence[int],
    image: int,
    group: DHGroup,
) -> list[int]:
    p = group.p
    points = [
        pow(b, r, p) * pow(key, challenge, p) % p
        for b, r, key in zip(gens, responses, keys, strict=True)
    ]
    points.append(pow(_image_base(keys[0], group), responses[0], p) * pow(image, challenge, p) % p)
    return points


def mlsag_verify(
    message: bytes,
    ring: Sequence[Sequence[int]],
    signature: LinkableRingSignature,
    *,
    bases: Sequence[int] | None = None,
    group: DHGroup = TEACHING_GROUP,
) -> bool:
    """Check a signature from :func:`mlsag_sign`: the challenges close the ring."""
    rows = _matrix(ring, group)
    gens = _bases(bases, len(rows[0]), group)
    image = signature.key_image
    if type(image) is not int or not 1 < image < group.p or pow(image, group.q, group.p) != 1:
        return False
    if len(signature.responses) != len(rows):
        return False
    if any(len(r) != len(rows[0]) for r in signature.responses):
        return False
    challenge = signature.challenge
    for keys, responses in zip(rows, signature.responses, strict=True):
        challenge = _hash(
            message, rows, image, *_points(keys, responses, challenge, gens, image, group)
        )
    return challenge == signature.challenge


def lsag_sign(
    message: bytes,
    ring: Sequence[int],
    index: int,
    secret: int,
    *,
    seed: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> LinkableRingSignature:
    """A linkable ring signature with one key per member: :func:`mlsag_sign` with one column.

    Examples
    --------
    >>> from blockchainkit.privacy import key_image, lsag_sign, lsag_verify
    >>> from blockchainkit.crypto import TEACHING_GROUP as G
    >>> ring = [G.public(x) for x in (11, 22, 33)]
    >>> signature = lsag_sign(b"spend", ring, 2, 33)
    >>> lsag_verify(b"spend", ring, signature), signature.key_image == key_image(33)
    (True, True)
    """
    return mlsag_sign(message, [[key] for key in ring], index, [secret], seed=seed, group=group)


def lsag_verify(
    message: bytes,
    ring: Sequence[int],
    signature: LinkableRingSignature,
    *,
    group: DHGroup = TEACHING_GROUP,
) -> bool:
    """Check a signature from :func:`lsag_sign`."""
    return mlsag_verify(message, [[key] for key in ring], signature, group=group)


def linked(first: LinkableRingSignature, second: LinkableRingSignature) -> bool:
    """Whether two signatures were made with the same key: their key images are equal."""
    return first.key_image == second.key_image
