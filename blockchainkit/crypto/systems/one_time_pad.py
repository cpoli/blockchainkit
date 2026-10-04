"""The one-time pad (Vernam 1917; Shannon 1949): XOR with a key as long as the message."""


def xor_bytes(left: bytes, right: bytes) -> bytes:
    """Return the bytewise XOR of two equally long byte strings.

    >>> from blockchainkit.crypto import xor_bytes
    >>> xor_bytes(b"\\x0f", b"\\xff")
    b'\\xf0'
    """
    if not isinstance(left, bytes) or not isinstance(right, bytes):
        raise TypeError("xor_bytes needs bytes")
    if len(left) != len(right):
        raise ValueError("inputs must have equal length")
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def one_time_pad(message: bytes, key: bytes) -> bytes:
    """Encrypt or decrypt with a one-time pad: ``message XOR key``.

    The same call decrypts, because XOR is its own inverse. Shannon proved
    the pad perfectly secret when the key is uniformly random, as long as the
    message, and never reused: every plaintext of that length is then equally
    likely given the ciphertext. Reusing a key leaks ``m1 XOR m2``.

    Parameters
    ----------
    message : bytes
        Plaintext (or ciphertext, to decrypt).
    key : bytes
        A key exactly as long as the message.

    Examples
    --------
    >>> from blockchainkit.crypto import one_time_pad
    >>> ciphertext = one_time_pad(b"hi", b"\\x01\\x02")
    >>> one_time_pad(ciphertext, b"\\x01\\x02")
    b'hi'
    """
    if isinstance(message, bytes) and isinstance(key, bytes) and len(key) != len(message):
        raise ValueError("the key must be exactly as long as the message")
    return xor_bytes(message, key)
