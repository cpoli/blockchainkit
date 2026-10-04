"""Salted, length-delimited hash commitments."""

import hmac

from blockchainkit.constants import COMMIT_DOMAIN
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
