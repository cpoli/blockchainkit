"""Small, inspectable finite-field helpers for teaching."""


def integer(value: int, name: str, minimum: int = 0) -> None:
    """Validate an integer, excluding booleans, with an inclusive lower bound."""
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def is_prime(value: int) -> bool:
    """Test primality deterministically for integers below 2**64.

    Uses trial division followed by deterministic Miller--Rabin bases for
    this bounded domain. Larger numbers are deliberately not accepted.

    >>> is_prime(7919), is_prime(561)
    (True, False)
    """
    if type(value) is not int or value >= 2**64:
        raise ValueError("expected an integer below 2**64")
    if value < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % p == 0:
            return value == p
    d, s = value - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, value)
            if x == value - 1:
                break
        else:
            return False
    return True
