"""A Fiat-Shamir transcript: the prover's messages hashed into the verifier's challenges.

Fiat and Shamir (1986) replaced an interactive verifier by a hash of
everything said so far. :class:`Transcript` keeps a running SHA-256 state:
``append`` absorbs a labelled message, and ``challenge`` squeezes an
integer below a modulus that depends on every message before it. The
prover and the verifier run the same transcript, so they derive the same
challenges, and the prover cannot choose its messages after seeing them.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.constants import TRANSCRIPT_DOMAIN
from blockchainkit.crypto.systems.hashing import sha256

Message = int | bytes | None | Sequence["Message"]
"""Integers, bytes, ``None`` (a point at infinity), or sequences of them."""


def _encode(value: Message) -> bytes:
    if value is None:
        return b"N"
    if isinstance(value, bytes):
        return b"B" + len(value).to_bytes(8, "big") + value
    if type(value) is int:
        if value < 0:
            raise ValueError("transcripts absorb non-negative integers")
        body = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return b"I" + len(body).to_bytes(8, "big") + body
    if isinstance(value, (tuple, list)):
        return b"S" + len(value).to_bytes(8, "big") + b"".join(_encode(v) for v in value)
    raise TypeError(f"cannot absorb a {type(value).__name__}")


class Transcript:
    """A labelled, append-only Fiat-Shamir transcript.

    Parameters
    ----------
    protocol : bytes
        Names the protocol, so challenges never transfer between protocols.

    Examples
    --------
    >>> from blockchainkit.proofs import Transcript
    >>> prover, verifier = Transcript(b"demo"), Transcript(b"demo")
    >>> prover.append("commitment", 42); verifier.append("commitment", 42)
    >>> prover.challenge("c", 97) == verifier.challenge("c", 97)
    True
    """

    def __init__(self, protocol: bytes) -> None:
        if not isinstance(protocol, bytes):
            raise TypeError("protocol must be bytes")
        self._state = sha256(TRANSCRIPT_DOMAIN + _encode(protocol))

    def append(self, label: str, value: Message) -> None:
        """Absorb a labelled message."""
        if not isinstance(label, str):
            raise TypeError("label must be a string")
        self._state = sha256(self._state + _encode(label.encode()) + _encode(value))

    def challenge(self, label: str, modulus: int) -> int:
        """Squeeze an integer in ``[0, modulus)`` from everything absorbed so far.

        The 256-bit digest is reduced modulo ``modulus``, which must be below
        2**64, so the bias is below 2**-192.
        """
        integer(modulus, "modulus", 1)
        if modulus >= 2**64:
            raise ValueError("modulus must be below 2**64")
        self.append(label, b"challenge")
        return int.from_bytes(self._state, "big") % modulus
