"""Commitments: salted hash commitments (Blum 1981) and Pedersen commitments (1991).

A commitment is a sealed envelope: binding (the committer cannot change the
contents later) and hiding (nobody can read them before the opening). A hash
commitment is computationally hiding and binding. A Pedersen commitment is
*perfectly* hiding and computationally binding, and commitments add.
"""

import hmac

from blockchainkit._validation import integer
from blockchainkit.constants import COMMIT_DOMAIN, PEDERSEN_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.hashing import sha256


def commit(message: bytes, salt: bytes) -> bytes:
    """Commit to a message with a secret salt of at least 16 bytes.

    Parameters
    ----------
    message : bytes
        Bytes to commit to.
    salt : bytes
        Random secret salt; fixed salts are only appropriate for experiments.

    Returns
    -------
    bytes
        Domain-separated digest. Length framing prevents ambiguous openings.

    Notes
    -----
    Hiding depends on salt entropy; binding relies on collision resistance.
    """
    if not isinstance(message, bytes) or not isinstance(salt, bytes):
        raise TypeError("message and salt must be bytes")
    if len(salt) < 16:
        raise ValueError("use at least 16 salt bytes")
    return sha256(COMMIT_DOMAIN + len(salt).to_bytes(8, "big") + salt + message)


def verify_commitment(digest: bytes, message: bytes, salt: bytes) -> bool:
    """Check an opening against a commitment using constant-time comparison."""
    return hmac.compare_digest(digest, commit(message, salt))


def pedersen_generators(group: DHGroup = TEACHING_GROUP) -> tuple[int, int]:
    """Return ``(g, h)``: the group generator and a second, independent generator.

    ``h`` is derived by hashing the group parameters into the subgroup, so
    nobody knows ``log_g(h)``. Anyone who did could open a commitment to any
    value, which is why ``h`` must not be chosen by the committer.
    """
    counter = 0
    while True:
        seed = PEDERSEN_DOMAIN + f"{group.p}:{group.q}:{group.g}:{counter}".encode()
        candidate = int.from_bytes(sha256(seed), "big") % group.p
        h = pow(candidate, (group.p - 1) // group.q, group.p)
        if h not in (0, 1, group.g):
            return group.g, h
        counter += 1  # Degenerate candidate (probability about 2/q): hash again.


def pedersen_commit(value: int, blinding: int, group: DHGroup = TEACHING_GROUP) -> int:
    """Commit to ``value`` as ``g**value * h**blinding mod p``.

    With a uniformly random blinding factor the commitment is uniformly
    distributed whatever the value (perfect hiding). Opening it to a
    different value would reveal ``log_g(h)`` (computational binding).
    Commitments multiply to a commitment of the sum:
    ``C(a, r) * C(b, s) = C(a + b, r + s)``.

    Parameters
    ----------
    value, blinding : int
        Elements of the integers modulo the group order q.
    group : DHGroup
        A prime-order subgroup; defaults to
        :data:`~blockchainkit.crypto.systems.asymmetric.TEACHING_GROUP`.

    Examples
    --------
    >>> from blockchainkit.crypto import pedersen_commit, TEACHING_GROUP as G
    >>> pedersen_commit(2, 5) * pedersen_commit(3, 7) % G.p == pedersen_commit(5, 12)
    True
    """
    for number, name in ((value, "value"), (blinding, "blinding")):
        integer(number, name)
        if number >= group.q:
            raise ValueError(f"{name} must be below the group order q")
    g, h = pedersen_generators(group)
    return pow(g, value, group.p) * pow(h, blinding, group.p) % group.p
