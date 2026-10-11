"""Kate-Zaverucha-Goldberg polynomial commitments (2010).

A trusted setup publishes ``[tau**i] G`` for a secret tau and then forgets
tau. A commitment to f is the single point ``C = [f(tau)] G``, computed
from the published powers without knowing tau. To prove ``f(z) = y``, the
prover sends ``W = [q(tau)] G`` for the quotient

    q(X) = (f(X) - y) / (X - z),

which is a polynomial exactly when f(z) = y. The verifier checks the
divisibility at the hidden point tau with one pairing equation,

    e(C - [y] G, G) = e(W, [tau] G - [z] G).

Commitments and openings are one group element each, whatever the degree.
Whoever knows tau can open a commitment to any value: see
:func:`forge_opening`.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import Point
from blockchainkit.crypto.systems.curves import Curve, add, multiply
from blockchainkit.proofs.core.base import SRS, KZGOpening
from blockchainkit.proofs.systems.pairing import PAIRING_CURVE, pairing
from blockchainkit.proofs.utils.groups import linear_combination
from blockchainkit.proofs.utils.polynomials import poly_divmod, poly_eval, poly_sub, polynomial


def trusted_setup(max_degree: int, secret: int, curve: Curve = PAIRING_CURVE) -> SRS:
    """Publish ``[secret**i] G`` for i up to ``max_degree``: a structured reference string.

    ``secret`` is the toxic waste tau. A single party running this knows
    it; :func:`~blockchainkit.proofs.systems.ceremony.contribute` spreads
    it over many parties so that one honest one suffices.

    >>> from blockchainkit.proofs import trusted_setup
    >>> trusted_setup(4, secret=1234).max_degree
    4
    """
    integer(max_degree, "max_degree", 1)
    integer(secret, "secret", 1)
    if secret % curve.order == 0:
        raise ValueError("secret must be nonzero modulo the group order")
    powers, power = [], 1
    for _ in range(max_degree + 1):
        powers.append(multiply(power, curve.generator, curve))
        power = power * secret % curve.order
    return SRS(tuple(powers), curve)


def kzg_commit(poly: Sequence[int], srs: SRS) -> Point:
    """Commit to a polynomial: ``[f(tau)] G``, a linear combination of the published powers.

    Examples
    --------
    >>> from blockchainkit.proofs import trusted_setup, kzg_commit, kzg_open, kzg_verify
    >>> srs = trusted_setup(4, secret=1234)
    >>> commitment = kzg_commit([5, 0, 1], srs)  # 5 + x**2
    >>> opening = kzg_open([5, 0, 1], 3, srs)
    >>> opening.value, kzg_verify(commitment, opening, srs)
    (14, True)
    """
    coefficients = polynomial(poly, srs.curve.order)
    if len(coefficients) > len(srs.powers):
        raise ValueError(f"degree exceeds the setup's maximum of {srs.max_degree}")
    return linear_combination(coefficients, srs.powers[: len(coefficients)], srs.curve)


def kzg_open(poly: Sequence[int], point: int, srs: SRS) -> KZGOpening:
    """Evaluate at ``point`` and prove it with a commitment to the quotient polynomial."""
    order = srs.curve.order
    integer(point, "point")
    value = poly_eval(poly, point, order)
    quotient, remainder = poly_divmod(poly_sub(poly, (value,), order), (-point, 1), order)
    assert not remainder  # f(X) - f(z) always vanishes at z.
    return KZGOpening(point % order, value, kzg_commit(quotient, srs))


def kzg_verify(commitment: Point, opening: KZGOpening, srs: SRS) -> bool:
    """Check ``e(C - [y] G, G) = e(W, [tau] G - [z] G)``; malformed inputs return False."""
    curve = srs.curve
    if not isinstance(opening, KZGOpening):
        return False
    try:
        for scalar in (opening.point, opening.value):
            integer(scalar, "scalar")
        left = add(commitment, multiply(-opening.value, curve.generator, curve), curve)
        shift = add(srs.powers[1], multiply(-opening.point, curve.generator, curve), curve)
        return pairing(left, curve.generator, curve) == pairing(opening.witness, shift, curve)
    except (TypeError, ValueError):
        return False


def forge_opening(commitment: Point, point: int, value: int, secret: int, srs: SRS) -> KZGOpening:
    """Open a commitment to *any* value, using the toxic waste tau.

    ``W = (C - [y] G) / (tau - z)`` satisfies the verification equation
    whatever y is, so a party that kept tau can prove false evaluations.
    This is why the setup's secret must be destroyed.
    """
    curve = srs.curve
    for scalar, name in ((point, "point"), (value, "value"), (secret, "secret")):
        integer(scalar, name)
    if (secret - point) % curve.order == 0:
        raise ValueError("cannot forge at the secret point itself")
    shifted = add(commitment, multiply(-value, curve.generator, curve), curve)
    witness = multiply(pow(secret - point, -1, curve.order), shifted, curve)
    return KZGOpening(point % curve.order, value % curve.order, witness)
