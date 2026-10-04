"""Argument validation shared by every blockchainkit subpackage."""


def integer(value: int, name: str, minimum: int = 0) -> None:
    """Validate an integer, excluding booleans, with an inclusive lower bound."""
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
