"""Halo: recursive proof composition without a trusted setup (2019).

A proof that verifies another proof, which verified another, can compress
an entire blockchain's history into one constant-size proof, if
verification is cheap enough to run inside a proof. Inner-product
arguments need no setup, but verifying one costs a multi-exponentiation of
length n. Bowe, Grigg and Hopwood noticed that this expensive step has a
special form: after the log2(n) challenges c_j of the halving rounds, the
verifier needs

    G_final = prod G_i**s_i,    where    sum s_i X**i = g(X) = prod (1 + c_j X**(2**(k-j))),

a *commitment to a polynomial g that anyone can evaluate in O(log n)*.
So the verifier does the cheap part, and keeps ``(c, G_final)`` as an
*accumulator*: a claim to be checked later. Two accumulators merge into
one by opening a random combination of their G_finals at a random point,
which is again an inner-product argument, with its own deferred claim. A
chain of any length then needs one O(n) check at the very end.

This module provides the inner-product polynomial commitment and its
accumulation, in the 62-bit teaching group. Halo itself ran the cheap
verifier inside a circuit over a cycle of two elliptic curves (Tweedledum
and Tweedledee); here the verifier runs in Python. Commitments carry no
blinding, so they are binding but not hiding.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP
from blockchainkit.proofs.core.base import AccumulationProof, HaloAccumulator, IPAOpening
from blockchainkit.proofs.utils.groups import independent_generators, multi_exponent
from blockchainkit.proofs.utils.transcript import Transcript

_GROUP = TEACHING_GROUP


def ipa_generators(size: int) -> tuple[int, ...]:
    """Return ``size`` independent generators G_i, then one more, U, for the evaluation."""
    integer(size, "size", 2)
    if size & (size - 1):
        raise ValueError("size must be a power of two")
    return independent_generators(size + 1, "halo")


def ipa_commit(coefficients: Sequence[int], generators: Sequence[int]) -> int:
    """Commit to a polynomial of degree below n: ``prod G_i**a_i``.

    >>> from blockchainkit.proofs import ipa_commit, ipa_generators
    >>> gens = ipa_generators(4)
    >>> ipa_commit([1, 2], gens) == ipa_commit([1, 2, 0, 0], gens)
    True
    """
    n = len(generators) - 1
    if len(coefficients) > n:
        raise ValueError(f"at most {n} coefficients")
    padded = [c % _GROUP.q for c in coefficients] + [0] * (n - len(coefficients))
    return multi_exponent(generators[:n], padded, _GROUP)


def _s_vector(challenges: Sequence[int], n: int) -> list[int]:
    """Coefficients of g(X) = prod (1 + c_j X**(2**(k-j))), round 1 owning the top bit."""
    q, k = _GROUP.q, len(challenges)
    s = [1] * n
    for i in range(n):
        for j, c in enumerate(challenges):
            if i >> (k - 1 - j) & 1:
                s[i] = s[i] * c % q
    return s


def challenge_polynomial(challenges: Sequence[int], point: int) -> int:
    """Evaluate ``g(X) = prod (1 + c_j X**(2**(k-j)))`` at a point in O(log n).

    >>> from blockchainkit.proofs import challenge_polynomial
    >>> challenge_polynomial([2, 3], 5) == (1 + 2 * 5**2) * (1 + 3 * 5)
    True
    """
    q, k = _GROUP.q, len(challenges)
    result = 1
    for j, c in enumerate(challenges):
        result = result * (1 + c * pow(point, 2 ** (k - 1 - j), q)) % q
    return result


def _start(transcript: Transcript, commitment: int, point: int, value: int) -> int:
    transcript.append("opening", [commitment, point, value])
    return transcript.challenge("u", _GROUP.q)


def ipa_open(
    coefficients: Sequence[int],
    point: int,
    generators: Sequence[int],
    *,
    label: bytes = b"halo-ipa",
) -> IPAOpening:
    """Prove the value of a committed polynomial at ``point`` by halving.

    Each round sends ``L = prod G_hi**a_lo U**<a_lo, b_hi>`` and
    ``R = prod G_lo**a_hi U**<a_hi, b_lo>``, where ``b = (1, x, x**2, ...)``,
    and folds ``a' = a_lo + c**-1 a_hi``, ``b' = b_lo + c b_hi``,
    ``G' = G_lo G_hi**c``.

    Examples
    --------
    >>> from blockchainkit.proofs import ipa_commit, ipa_generators, ipa_open, ipa_verify
    >>> gens = ipa_generators(8)
    >>> opening = ipa_open([3, 1, 4, 1, 5], 2, gens)
    >>> opening.value, ipa_verify(ipa_commit([3, 1, 4, 1, 5], gens), opening, gens)
    (109, True)
    """
    p, q = _GROUP.p, _GROUP.q
    n = len(generators) - 1
    integer(point, "point")
    commitment = ipa_commit(coefficients, generators)
    a = [c % q for c in coefficients] + [0] * (n - len(coefficients))
    b = [pow(point, i, q) for i in range(n)]
    value = sum(x * y for x, y in zip(a, b, strict=True)) % q
    transcript = Transcript(label)
    u = pow(generators[n], _start(transcript, commitment, point % q, value), p)
    g = list(generators[:n])
    lefts, rights, challenges = [], [], []
    while len(a) > 1:
        h = len(a) // 2
        c_left = sum(x * y for x, y in zip(a[:h], b[h:], strict=True)) % q
        c_right = sum(x * y for x, y in zip(a[h:], b[:h], strict=True)) % q
        lefts.append(multi_exponent(g[h:], a[:h], _GROUP) * pow(u, c_left, p) % p)
        rights.append(multi_exponent(g[:h], a[h:], _GROUP) * pow(u, c_right, p) % p)
        transcript.append("round", [lefts[-1], rights[-1]])
        c = transcript.challenge("c", q) or 1
        challenges.append(c)
        c_inverse = pow(c, -1, q)
        a = [(a[i] + c_inverse * a[h + i]) % q for i in range(h)]
        b = [(b[i] + c * b[h + i]) % q for i in range(h)]
        g = [g[i] * pow(g[h + i], c, p) % p for i in range(h)]
    return IPAOpening(point % q, value, tuple(lefts), tuple(rights), a[0], g[0])


def ipa_defer(
    commitment: int, opening: IPAOpening, generators: Sequence[int], *, label: bytes = b"halo-ipa"
) -> HaloAccumulator | None:
    """Do the cheap part of verification and return the deferred claim about G_final.

    This takes O(log n) group operations: it folds the commitment with L
    and R and evaluates g(x) without the generators, trusting the opening's
    ``g_final``. It returns ``None`` if the final equation fails, and
    otherwise an accumulator that :func:`decide` must eventually check.
    """
    p, q = _GROUP.p, _GROUP.q
    n = len(generators) - 1
    if not isinstance(opening, IPAOpening) or 2 ** len(opening.left) != n:
        return None
    if len(opening.left) != len(opening.right):
        return None
    transcript = Transcript(label)
    u = pow(generators[n], _start(transcript, commitment, opening.point, opening.value), p)
    target = commitment * pow(u, opening.value, p) % p
    challenges = []
    for big_l, big_r in zip(opening.left, opening.right, strict=True):
        transcript.append("round", [big_l, big_r])
        c = transcript.challenge("c", q) or 1
        challenges.append(c)
        target = target * pow(big_l, c, p) * pow(big_r, pow(c, -1, q), p) % p
    b_final = challenge_polynomial(challenges, opening.point)
    a = opening.final
    if target != pow(opening.g_final, a, p) * pow(u, a * b_final % q, p) % p:
        return None
    return HaloAccumulator(tuple(challenges), opening.g_final)


def decide(accumulator: HaloAccumulator, generators: Sequence[int]) -> bool:
    """The expensive O(n) check: is ``g_final`` really ``prod G_i**s_i``?"""
    n = len(generators) - 1
    if not isinstance(accumulator, HaloAccumulator) or 2 ** len(accumulator.challenges) != n:
        return False
    s = _s_vector(accumulator.challenges, n)
    return multi_exponent(generators[:n], s, _GROUP) == accumulator.g_final


def ipa_verify(commitment: int, opening: IPAOpening, generators: Sequence[int]) -> bool:
    """Verify an opening completely: the deferred checks, then :func:`decide` at once."""
    accumulator = ipa_defer(commitment, opening, generators)
    return accumulator is not None and decide(accumulator, generators)


def _accumulation_challenges(accumulators: Sequence[HaloAccumulator]) -> tuple[int, int]:
    transcript = Transcript(b"halo-accumulate")
    transcript.append("accumulators", [[list(a.challenges), a.g_final] for a in accumulators])
    q = _GROUP.q
    return transcript.challenge("point", q), transcript.challenge("rho", q)


def _combined_commitment(accumulators: Sequence[HaloAccumulator], rho: int) -> int:
    p, q = _GROUP.p, _GROUP.q
    result = 1
    for j, accumulator in enumerate(accumulators):
        result = result * pow(accumulator.g_final, pow(rho, j, q), p) % p
    return result


def accumulate(
    accumulators: Sequence[HaloAccumulator], generators: Sequence[int]
) -> AccumulationProof:
    """Merge deferred claims into one: open ``sum rho**j g_j(X)`` at a random point.

    The prover knows each g_j's coefficients from its challenges, so it can
    open the combination of the G_finals; if any G_final were wrong, it could
    not. The result's own deferred claim is the new accumulator.
    """
    if not accumulators or not all(isinstance(a, HaloAccumulator) for a in accumulators):
        raise ValueError("need at least one HaloAccumulator")
    n = len(generators) - 1
    q = _GROUP.q
    point, rho = _accumulation_challenges(accumulators)
    combined = [0] * n
    for j, accumulator in enumerate(accumulators):
        weight = pow(rho, j, q)
        for i, s in enumerate(_s_vector(accumulator.challenges, n)):
            combined[i] = (combined[i] + weight * s) % q
    return AccumulationProof(ipa_open(combined, point, generators, label=b"halo-accumulate-ipa"))


def verify_accumulation(
    accumulators: Sequence[HaloAccumulator], proof: AccumulationProof, generators: Sequence[int]
) -> HaloAccumulator | None:
    """Check an accumulation step in O(k log n) and return the new accumulator, or ``None``.

    Examples
    --------
    >>> from blockchainkit.proofs import (ipa_generators, ipa_commit, ipa_open, ipa_defer,
    ...     accumulate, verify_accumulation, decide)
    >>> gens = ipa_generators(8)
    >>> claims = [ipa_defer(ipa_commit(f, gens), ipa_open(f, 5, gens), gens)
    ...           for f in ([1, 2, 3], [4, 5, 6, 7])]
    >>> merged = verify_accumulation(claims, accumulate(claims, gens), gens)
    >>> decide(merged, gens)
    True
    """
    if not accumulators or not isinstance(proof, AccumulationProof):
        return None
    if not all(isinstance(a, HaloAccumulator) for a in accumulators):
        return None
    q = _GROUP.q
    point, rho = _accumulation_challenges(accumulators)
    expected = (
        sum(
            pow(rho, j, q) * challenge_polynomial(a.challenges, point)
            for j, a in enumerate(accumulators)
        )
        % q
    )
    opening = proof.opening
    if opening.point != point or opening.value != expected:
        return None
    commitment = _combined_commitment(accumulators, rho)
    return ipa_defer(commitment, opening, generators, label=b"halo-accumulate-ipa")
