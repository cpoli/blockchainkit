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


def probability(value: float, name: str) -> None:
    """Validate a real number in [0, 1]; booleans are rejected like in :func:`integer`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number in [0, 1]")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be in [0, 1]")


def positive(value: float, name: str) -> None:
    """Validate a finite real number greater than zero, such as a delay or an interval."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a positive real number")
    if not 0 < value < float("inf"):
        raise ValueError(f"{name} must be positive and finite")
