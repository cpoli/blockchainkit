"""Keys, signatures and the Script templates that channels are built from.

Every channel output in this subpackage is a :mod:`blockchainkit.vm.systems.script`
program judged by :func:`~blockchainkit.vm.systems.script.verify_script`.
That interpreter has no ``OP_CHECKMULTISIG``, so a 2-of-2 output checks two
signatures in a row, and no ``OP_CHECKSEQUENCEVERIFY``, so a relative delay
is written with ``OP_CHECKLOCKTIMEVERIFY`` and checked against the output's
age: the spender passes ``locktime = height - confirmed_at``.
"""

from typing import Any

from blockchainkit.constants import CHANNEL_DOMAIN
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.curves import SECP256K1, public_key
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.signatures import deterministic_nonce, sign
from blockchainkit.structures.utils.encoding import canonical_json
from blockchainkit.vm.systems.script import (
    ScriptItem,
    encode_public_key,
    encode_signature,
    number,
)

PublicKey = tuple[int, int]


def check_key(private: int, name: str) -> None:
    """Validate a secp256k1 private key."""
    if type(private) is not int:
        raise TypeError(f"{name} must be an integer private key")
    if not 1 <= private < SECP256K1.order:
        raise ValueError(f"{name} must be in [1, the curve order)")


def channel_message(*fields: Any) -> bytes:
    """The bytes a channel party signs: the domain tag, then the canonical JSON of ``fields``."""
    return CHANNEL_DOMAIN + canonical_json(list(fields))


def signature(private: int, message: bytes) -> SchnorrSignature:
    """Sign ``message`` with a deterministic (RFC 6979) nonce."""
    return sign(message, private, nonce=deterministic_nonce(private, message))


def derived_key(private: int, label: str) -> int:
    """A second private key derived from ``private`` for one purpose, such as settlement."""
    digest = sha256(CHANNEL_DOMAIN + label.encode() + private.to_bytes(32, "big"))
    return int.from_bytes(digest, "big") % (SECP256K1.order - 1) + 1


def two_of_two_locking(first: PublicKey, second: PublicKey) -> tuple[ScriptItem, ...]:
    """Both keys must sign: ``<first> OP_CHECKSIG OP_VERIFY <second> OP_CHECKSIG``."""
    return (
        encode_public_key(first),
        "OP_CHECKSIG",
        "OP_VERIFY",
        encode_public_key(second),
        "OP_CHECKSIG",
    )


def two_of_two_unlocking(
    first: SchnorrSignature, second: SchnorrSignature
) -> tuple[ScriptItem, ...]:
    """The matching unlocking script: ``<second signature> <first signature>``."""
    return (encode_signature(second), encode_signature(first))


def revocable_locking(
    revocation: PublicKey, owner: PublicKey, delay: int
) -> tuple[ScriptItem, ...]:
    """Pay ``owner`` after ``delay`` blocks, or the holder of ``revocation`` at once.

    The script is ``OP_IF <revocation> OP_ELSE <delay> OP_CHECKLOCKTIMEVERIFY
    OP_DROP <owner> OP_ENDIF OP_CHECKSIG``.
    """
    return (
        "OP_IF",
        encode_public_key(revocation),
        "OP_ELSE",
        number(delay),
        "OP_CHECKLOCKTIMEVERIFY",
        "OP_DROP",
        encode_public_key(owner),
        "OP_ENDIF",
        "OP_CHECKSIG",
    )


def key_pair(private: int, name: str = "private key") -> tuple[int, PublicKey]:
    """Validate ``private`` and return it with its public key."""
    check_key(private, name)
    return private, public_key(private)
