"""Account identifiers: 64 lowercase hex characters, the SHA-256 of a public key."""

_HEX = frozenset("0123456789abcdef")


def is_account_id(value: object) -> bool:
    """Return whether ``value`` has the shape of an account identifier.

    >>> from blockchainkit.structures.utils import is_account_id
    >>> is_account_id("ab" * 32), is_account_id("AB" * 32)
    (True, False)
    """
    return isinstance(value, str) and len(value) == 64 and _HEX.issuperset(value)
