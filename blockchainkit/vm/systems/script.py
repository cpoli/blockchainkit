"""Bitcoin-style Script (2009): spending conditions as tiny stack programs.

A coin is locked by a *locking script*; to spend it, one supplies an
*unlocking script*. The unlocking script runs first, then the locking script
runs on the stack it left, and the spend is valid if no step fails and the
top of the stack is true. Script deliberately has no loops, so a script of n
operations runs at most n steps and needs no gas.

Teaching differences from Bitcoin: stack items are byte strings, but numbers
are big-endian; ``OP_HASH256`` (double SHA-256) replaces ``OP_HASH160`` in
pay-to-public-key-hash; and ``OP_CHECKSIG`` checks a blockchainkit Schnorr
signature over an explicit message rather than a transaction digest.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.curves import SECP256K1, encode_point
from blockchainkit.crypto.systems.hashing import hash256, sha256
from blockchainkit.crypto.systems.signatures import verify
from blockchainkit.vm.core.base import ScriptResult

ScriptItem = bytes | str
"""A data push (bytes) or an opcode name such as ``"OP_DUP"`` (str)."""

OPCODES = frozenset(
    {
        "OP_TRUE",
        "OP_FALSE",
        "OP_DUP",
        "OP_DROP",
        "OP_EQUAL",
        "OP_EQUALVERIFY",
        "OP_VERIFY",
        "OP_SHA256",
        "OP_HASH256",
        "OP_CHECKSIG",
        "OP_CHECKLOCKTIMEVERIFY",
        "OP_IF",
        "OP_ELSE",
        "OP_ENDIF",
        "OP_RETURN",
    }
)
"""Every opcode the interpreter accepts."""

_WIDTH = 32


def encode_public_key(public: tuple[int, int]) -> bytes:
    """A public key as stack bytes (uncompressed point encoding)."""
    return encode_point(public)


def encode_signature(signature: SchnorrSignature) -> bytes:
    """A signature as stack bytes: the commitment point, then the 32-byte response."""
    return encode_point(signature.commitment) + signature.response.to_bytes(_WIDTH, "big")


def _point(data: bytes) -> tuple[int, int]:
    if len(data) != 1 + 2 * _WIDTH or data[0] != 4:
        raise ValueError("not an encoded point")
    return int.from_bytes(data[1 : 1 + _WIDTH], "big"), int.from_bytes(data[1 + _WIDTH :], "big")


def number(value: int) -> bytes:
    """Encode a non-negative integer as minimal big-endian bytes (0 is empty)."""
    integer(value, "value")
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def _true(item: bytes) -> bool:
    return any(item)


class _Fail(Exception):
    pass


def _run(
    script: Sequence[ScriptItem],
    stack: list[bytes],
    message: bytes,
    locktime: int,
    operations: list[int],
) -> None:
    executing: list[bool] = []  # One entry per open OP_IF.
    for item in script:
        active = all(executing)
        if isinstance(item, bytes):
            operations[0] += 1
            if active:
                stack.append(item)
            continue
        if item not in OPCODES:
            raise _Fail(f"unknown opcode {item!r}")
        if item in ("OP_IF", "OP_ELSE", "OP_ENDIF"):
            operations[0] += 1
            if item == "OP_IF":
                if active:
                    if not stack:
                        raise _Fail("OP_IF on an empty stack")
                    executing.append(_true(stack.pop()))
                else:
                    executing.append(False)
            elif not executing:
                raise _Fail(f"{item} without OP_IF")
            elif item == "OP_ELSE":
                executing[-1] = not executing[-1] and all(executing[:-1])
            else:
                executing.pop()
            continue
        if not active:
            continue
        operations[0] += 1
        if item == "OP_RETURN":
            raise _Fail("OP_RETURN marks the output unspendable")
        if item == "OP_TRUE":
            stack.append(b"\x01")
            continue
        if item == "OP_FALSE":
            stack.append(b"")
            continue
        needed = 2 if item in ("OP_EQUAL", "OP_EQUALVERIFY", "OP_CHECKSIG") else 1
        if len(stack) < needed:
            raise _Fail(f"{item} needs {needed} stack items")
        if item == "OP_DUP":
            stack.append(stack[-1])
        elif item == "OP_DROP":
            stack.pop()
        elif item in ("OP_EQUAL", "OP_EQUALVERIFY"):
            equal = stack.pop() == stack.pop()
            if item == "OP_EQUALVERIFY" and not equal:
                raise _Fail("OP_EQUALVERIFY: items differ")
            if item == "OP_EQUAL":
                stack.append(b"\x01" if equal else b"")
        elif item == "OP_VERIFY":
            if not _true(stack.pop()):
                raise _Fail("OP_VERIFY: false")
        elif item == "OP_SHA256":
            stack.append(sha256(stack.pop()))
        elif item == "OP_HASH256":
            stack.append(hash256(stack.pop()))
        elif item == "OP_CHECKSIG":
            public, signature = stack.pop(), stack.pop()
            try:
                point = _point(signature[: 1 + 2 * _WIDTH])
                response = int.from_bytes(signature[1 + 2 * _WIDTH :], "big")
                ok = len(signature) == 1 + 3 * _WIDTH and verify(
                    message, SchnorrSignature(point, response), _point(public), SECP256K1
                )
            except ValueError:
                ok = False
            stack.append(b"\x01" if ok else b"")
        else:  # OP_CHECKLOCKTIMEVERIFY leaves its operand, as in BIP 65.
            if int.from_bytes(stack[-1], "big") > locktime:
                raise _Fail("OP_CHECKLOCKTIMEVERIFY: the lock time has not been reached")
    if executing:
        raise _Fail("OP_IF without OP_ENDIF")


def verify_script(
    unlocking: Sequence[ScriptItem],
    locking: Sequence[ScriptItem],
    *,
    message: bytes = b"",
    locktime: int = 0,
) -> ScriptResult:
    """Run the unlocking script, then the locking script on its stack, and judge the spend.

    Parameters
    ----------
    unlocking, locking : sequence of bytes or str
        Data pushes and opcode names.
    message : bytes
        What ``OP_CHECKSIG`` signatures must sign (the spending transaction).
    locktime : int
        The spending transaction's lock time, compared by
        ``OP_CHECKLOCKTIMEVERIFY``.

    Returns
    -------
    ScriptResult

    Notes
    -----
    Running the scripts separately matters: until 2010 Bitcoin concatenated
    them, and the unlocking script ``OP_TRUE OP_RETURN`` ended execution
    early with true on top, spending any coin (CVE-2010-5141).

    Examples
    --------
    >>> from blockchainkit.crypto import sha256
    >>> from blockchainkit.vm import verify_script
    >>> verify_script([b"secret"], ["OP_SHA256", sha256(b"secret"), "OP_EQUAL"]).valid
    True
    """
    if not isinstance(message, bytes):
        raise TypeError("message must be bytes")
    integer(locktime, "locktime")
    stack: list[bytes] = []
    operations = [0]  # Shared counter, so a failed run still reports its work.
    try:
        _run(unlocking, stack, message, locktime, operations)
        _run(locking, stack, message, locktime, operations)
    except _Fail as failure:
        return ScriptResult(False, tuple(stack), str(failure), operations[0])
    if not stack or not _true(stack[-1]):
        return ScriptResult(False, tuple(stack), "the top of the stack is not true", operations[0])
    return ScriptResult(True, tuple(stack), None, operations[0])


def p2pkh_locking(public: tuple[int, int]) -> tuple[ScriptItem, ...]:
    """Pay to public-key hash: ``OP_DUP OP_HASH256 <hash> OP_EQUALVERIFY OP_CHECKSIG``.

    The coin names only the hash of a key; the spender reveals the key and
    a signature.
    """
    return (
        "OP_DUP",
        "OP_HASH256",
        hash256(encode_public_key(public)),
        "OP_EQUALVERIFY",
        "OP_CHECKSIG",
    )


def p2pkh_unlocking(signature: SchnorrSignature, public: tuple[int, int]) -> tuple[ScriptItem, ...]:
    """The matching unlocking script: ``<signature> <public key>``."""
    return (encode_signature(signature), encode_public_key(public))


def htlc_locking(
    payment_hash: bytes,
    recipient: tuple[int, int],
    refund: tuple[int, int],
    timeout: int,
) -> tuple[ScriptItem, ...]:
    """A hash time-locked contract.

    The recipient can claim with a signature and the preimage of
    ``payment_hash`` (SHA-256); after ``timeout``, the sender can take a
    refund with its own signature::

        OP_IF
            OP_SHA256 <payment_hash> OP_EQUALVERIFY <recipient>
        OP_ELSE
            <timeout> OP_CHECKLOCKTIMEVERIFY OP_DROP <refund>
        OP_ENDIF
        OP_CHECKSIG
    """
    if not isinstance(payment_hash, bytes) or len(payment_hash) != 32:
        raise ValueError("payment_hash must be a 32-byte SHA-256 digest")
    return (
        "OP_IF",
        "OP_SHA256",
        payment_hash,
        "OP_EQUALVERIFY",
        encode_public_key(recipient),
        "OP_ELSE",
        number(timeout),
        "OP_CHECKLOCKTIMEVERIFY",
        "OP_DROP",
        encode_public_key(refund),
        "OP_ENDIF",
        "OP_CHECKSIG",
    )
