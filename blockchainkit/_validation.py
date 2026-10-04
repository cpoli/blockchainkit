"""Argument validation shared by every blockchainkit subpackage."""


def integer(value: int, name: str, minimum: int = 0) -> None:
    """Validate an integer with an inclusive lower bound.

    Raises
    ------
    TypeError
        ``value`` is not an ``int``. Booleans are rejected even though
        ``bool`` subclasses ``int``: ``True`` as a key or an amount is a bug.
    ValueError
        ``value`` is below ``minimum``.
    """
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer, not {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def seed(value: int) -> None:
    """Validate a simulation seed: any integer, but not a bool, float, or string.

    ``random.Random`` silently accepts strings and bytes, so a typo would
    still produce a reproducible but unintended stream.
    """
    if type(value) is not int:
        raise TypeError(f"seed must be an integer, not {type(value).__name__}")
