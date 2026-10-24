r"""Pay to script hash (Andresen, BIP16, 2012) and multisig wallets.

Before 2012, a coin locked by several keys carried the whole locking
script, so the payer had to know and pay for the payee's security policy.
P2SH locks a coin to the hash of a *redeem script* instead:

.. math::

   \text{locking} = \texttt{OP\_HASH256}\ \langle H(\text{redeem}) \rangle\ \texttt{OP\_EQUAL}

The spender reveals the redeem script as the last push of the unlocking
script. Validation runs twice: first the unlocking script and the locking
script, which only check the hash; then, if that passes, the redeem script
on the stack the unlocking script left, which checks the signatures. The
payer sees only a 20-byte hash in a short address starting with 3, and the
policy, such as 2 of 3 keys, stays private until the coin is spent.

Teaching differences from BIP16: the hash is ``OP_HASH256`` (double
SHA-256), because :mod:`blockchainkit.vm.systems.script` has no
``OP_HASH160``; and since it has no ``OP_CHECKMULTISIG`` either, an m-of-n
redeem script is a tree of ``OP_IF`` branches, one per set of m signers,
which the spender picks with true and false pushes. Its size grows like
``C(n, m)``, so the 520-byte limit on a pushed script soon binds: 2-of-3
fits, 3-of-5 does not.
"""

from collections.abc import Mapping, Sequence
from itertools import combinations

from blockchainkit._validation import integer
from blockchainkit.constants import MAX_SCRIPT_ELEMENT_SIZE
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.hashing import hash256
from blockchainkit.vm.core.base import ScriptResult
from blockchainkit.vm.systems.script import (
    OPCODES,
    ScriptItem,
    encode_public_key,
    encode_signature,
    verify_script,
)
from blockchainkit.wallets.systems.base58 import P2SH_VERSION, base58check_encode
from blockchainkit.wallets.utils.keys import PublicKey
from blockchainkit.wallets.utils.ripemd160 import hash160

OPCODE_BYTES = {
    "OP_FALSE": 0x00,
    "OP_TRUE": 0x51,
    "OP_IF": 0x63,
    "OP_ELSE": 0x67,
    "OP_ENDIF": 0x68,
    "OP_VERIFY": 0x69,
    "OP_RETURN": 0x6A,
    "OP_DROP": 0x75,
    "OP_DUP": 0x76,
    "OP_EQUAL": 0x87,
    "OP_EQUALVERIFY": 0x88,
    "OP_SHA256": 0xA8,
    "OP_HASH256": 0xAA,
    "OP_CHECKSIG": 0xAC,
    "OP_CHECKLOCKTIMEVERIFY": 0xB1,
}
"""dict: Bitcoin's byte for each opcode of the teaching interpreter."""

_OPCODE_NAMES = {byte: name for name, byte in OPCODE_BYTES.items()}
assert set(OPCODE_BYTES) == OPCODES


def serialize_script(script: Sequence[ScriptItem]) -> bytes:
    """Encode a script as Bitcoin does: opcodes as bytes, pushes with a length prefix.

    A push of 1 to 75 bytes is prefixed by its length; longer pushes use
    ``OP_PUSHDATA1`` (0x4c) or ``OP_PUSHDATA2`` (0x4d). An empty push is
    0x00, the same byte as ``OP_FALSE``, which pushes the empty string.
    """
    out = bytearray()
    for item in script:
        if isinstance(item, str):
            if item not in OPCODE_BYTES:
                raise ValueError(f"unknown opcode {item!r}")
            out.append(OPCODE_BYTES[item])
        elif not isinstance(item, bytes):
            raise TypeError("script items are bytes pushes or opcode names")
        elif not item:
            out.append(0)
        elif len(item) <= 75:
            out += bytes([len(item)]) + item
        elif len(item) <= 255:
            out += bytes([0x4C, len(item)]) + item
        elif len(item) <= 0xFFFF:
            out += bytes([0x4D]) + len(item).to_bytes(2, "little") + item
        else:
            raise ValueError("a push is at most 65,535 bytes")
    return bytes(out)


def parse_script(data: bytes) -> tuple[ScriptItem, ...]:
    """Decode :func:`serialize_script`'s bytes back into opcodes and pushes.

    Raises
    ------
    ValueError
        An unknown opcode byte, or a push running past the end.
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    items: list[ScriptItem] = []
    i = 0
    while i < len(data):
        byte = data[i]
        i += 1
        if 1 <= byte <= 75:
            size = byte
        elif byte == 0x4C:
            size, i = data[i] if i < len(data) else -1, i + 1
        elif byte == 0x4D:
            size = int.from_bytes(data[i : i + 2], "little") if i + 2 <= len(data) else -1
            i += 2
        elif byte in _OPCODE_NAMES:
            items.append(_OPCODE_NAMES[byte])
            continue
        else:
            raise ValueError(f"unknown opcode byte 0x{byte:02x}")
        if size < 0 or i + size > len(data):
            raise ValueError("a push runs past the end of the script")
        items.append(data[i : i + size])
        i += size
    return tuple(items)


def multisig_redeem_script(threshold: int, publics: Sequence[PublicKey]) -> tuple[ScriptItem, ...]:
    """An m-of-n redeem script: one ``OP_IF`` branch per set of ``threshold`` keys.

    Each branch checks its keys in turn,
    ``<K1> OP_CHECKSIG OP_VERIFY ... <Km> OP_CHECKSIG``, and the last branch
    needs no ``OP_IF``.

    Examples
    --------
    >>> from blockchainkit.crypto import public_key
    >>> from blockchainkit.wallets import multisig_redeem_script
    >>> script = multisig_redeem_script(2, [public_key(k) for k in (3, 5, 7)])
    >>> script.count("OP_IF"), script.count("OP_CHECKSIG")
    (2, 6)
    """
    integer(threshold, "threshold", 1)
    keys = [encode_public_key(public) for public in publics]
    if threshold > len(keys):
        raise ValueError("threshold exceeds the number of keys")
    if len(set(keys)) != len(keys):
        raise ValueError("keys must be distinct")
    branches = []
    for subset in combinations(keys, threshold):
        body: list[ScriptItem] = []
        for key in subset[:-1]:
            body += [key, "OP_CHECKSIG", "OP_VERIFY"]
        branches.append([*body, subset[-1], "OP_CHECKSIG"])
    script = branches[-1]
    for branch in reversed(branches[:-1]):
        script = ["OP_IF", *branch, "OP_ELSE", *script, "OP_ENDIF"]
    return tuple(script)


def multisig_unlocking(
    threshold: int, keys: int, signatures: Mapping[int, SchnorrSignature]
) -> tuple[bytes, ...]:
    """The pushes that satisfy :func:`multisig_redeem_script`: signatures, then branch choices.

    Parameters
    ----------
    threshold, keys : int
        m and n of the redeem script.
    signatures : mapping of int to SchnorrSignature
        Exactly ``threshold`` signatures, keyed by the signer's position in
        the key list.
    """
    integer(threshold, "threshold", 1)
    integer(keys, "keys", threshold)
    signers = tuple(sorted(signatures))
    if len(signers) != threshold or not set(signers) <= set(range(keys)):
        raise ValueError("need exactly threshold signatures from positions 0 to keys - 1")
    branch = list(combinations(range(keys), threshold)).index(signers)
    last = branch == len(list(combinations(range(keys), threshold))) - 1
    choices = [b""] * branch + ([] if last else [b"\x01"])
    pushes = [encode_signature(signatures[i]) for i in reversed(signers)]
    return (*pushes, *reversed(choices))


def p2sh_locking(redeem: Sequence[ScriptItem]) -> tuple[ScriptItem, ...]:
    """Lock a coin to a redeem script's hash: ``OP_HASH256 <hash> OP_EQUAL``."""
    return ("OP_HASH256", hash256(serialize_script(redeem)), "OP_EQUAL")


def p2sh_unlocking(redeem: Sequence[ScriptItem], pushes: Sequence[bytes]) -> tuple[bytes, ...]:
    """The redeem script's own unlocking pushes, followed by the serialized redeem script."""
    return (*pushes, serialize_script(redeem))


def p2sh_address(redeem: Sequence[ScriptItem]) -> str:
    """The Base58Check address of a redeem script: version 5 and its ``HASH160``.

    This is the address BIP16 gives the script; the teaching locking script
    commits with ``OP_HASH256`` instead.
    """
    return base58check_encode(P2SH_VERSION, hash160(serialize_script(redeem)))


def verify_p2sh(
    unlocking: Sequence[ScriptItem],
    locking: Sequence[ScriptItem],
    *,
    message: bytes = b"",
    locktime: int = 0,
) -> ScriptResult:
    """Validate a spend of a P2SH output in BIP16's two stages.

    The unlocking script must contain only pushes. Stage one runs it with
    the locking script, checking the hash; stage two parses the last push
    as the redeem script and runs it on the other pushes.

    Examples
    --------
    >>> from blockchainkit.crypto import public_key, sign
    >>> from blockchainkit.wallets import (
    ...     multisig_redeem_script, multisig_unlocking, p2sh_locking, p2sh_unlocking, verify_p2sh)
    >>> redeem = multisig_redeem_script(2, [public_key(k) for k in (3, 5, 7)])
    >>> signatures = {0: sign(b"tx", 3, nonce=11), 2: sign(b"tx", 7, nonce=13)}
    >>> spend = p2sh_unlocking(redeem, multisig_unlocking(2, 3, signatures))
    >>> verify_p2sh(spend, p2sh_locking(redeem), message=b"tx").valid
    True
    """
    if any(not isinstance(item, bytes) for item in unlocking) or not unlocking:
        return ScriptResult(False, (), "a P2SH unlocking script holds only pushes", 0)
    outer = verify_script(unlocking, locking, message=message, locktime=locktime)
    if not outer.valid:
        return outer
    serialized = unlocking[-1]
    assert isinstance(serialized, bytes)
    if len(serialized) > MAX_SCRIPT_ELEMENT_SIZE:
        error = f"the redeem script exceeds {MAX_SCRIPT_ELEMENT_SIZE} bytes"
        return ScriptResult(False, (), error, outer.operations)
    try:
        redeem = parse_script(serialized)
    except ValueError as exc:
        return ScriptResult(False, (), str(exc), outer.operations)
    inner = verify_script(unlocking[:-1], redeem, message=message, locktime=locktime)
    return ScriptResult(inner.valid, inner.stack, inner.error, outer.operations + inner.operations)
