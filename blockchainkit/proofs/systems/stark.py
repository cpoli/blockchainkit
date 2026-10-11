"""STARKs: scalable, transparent arguments of knowledge from hashes (2018).

Ben-Sasson, Bentov, Horesh and Riabzev proved computations with nothing
but a hash function: no trusted setup, no pairings, and (as far as is
known) no quantum weakness. The computation is written as an *execution
trace* with *algebraic constraints* between consecutive rows (an AIR).
Here the trace is the Fibonacci sequence, a_0 = a_1 = 1 and
``a_(i+2) = a_(i+1) + a_i``, over T steps, and the claim is a_(T-1).

Interpolate the trace over the subgroup <g> of order T as a polynomial
f, so ``f(g**i) = a_i``. Each constraint becomes a divisibility: the
transition holds on rows 0 to T-3 exactly when

    (f(g**2 X) - f(g X) - f(X)) (X - g**(T-2)) (X - g**(T-1)) / (X**T - 1)

is a polynomial, and each boundary value when ``(f(X) - a) / (X - g**i)``
is. The prover evaluates f on a larger coset (the *low-degree extension*),
commits to it with a Merkle tree, combines the quotients with random
coefficients, and proves with FRI that the combination has low degree.
The verifier recomputes the combination at FRI's query positions from
Merkle-opened trace values at x, g x and g**2 x. A false claim leaves a
quotient that is not a polynomial, which FRI rejects.
"""

from blockchainkit._validation import integer
from blockchainkit.proofs.core.base import StarkProof, TraceOpening
from blockchainkit.proofs.systems.fri import fri_prove, fri_verify
from blockchainkit.proofs.utils.polynomials import (
    FIELD_GENERATOR,
    FIELD_PRIME,
    evaluate_on_domain,
    interpolate_on_domain,
    root_of_unity,
)
from blockchainkit.proofs.utils.transcript import Transcript
from blockchainkit.structures.systems.merkle import MerkleTree, verify_proof

_P = FIELD_PRIME


def fibonacci_trace(steps: int) -> tuple[int, ...]:
    """The first ``steps`` Fibonacci numbers modulo the BabyBear prime, from 1, 1.

    >>> from blockchainkit.proofs import fibonacci_trace
    >>> fibonacci_trace(8)
    (1, 1, 2, 3, 5, 8, 13, 21)
    """
    integer(steps, "steps", 2)
    trace = [1, 1]
    while len(trace) < steps:
        trace.append((trace[-1] + trace[-2]) % _P)
    return tuple(trace)


def _check(steps: int, blowup: int, num_queries: int) -> None:
    integer(steps, "steps", 4)
    integer(blowup, "blowup", 2)
    integer(num_queries, "num_queries", 1)
    for value, name in ((steps, "steps"), (blowup, "blowup")):
        if value & (value - 1):
            raise ValueError(f"{name} must be a power of two")


def _composition(
    values: tuple[int, int, int], x: int, steps: int, result: int, alphas: list[int]
) -> int:
    """The random combination of the four constraint quotients at one point."""
    f0, f1, f2 = values
    g = root_of_unity(steps)
    last, before_last = pow(g, steps - 1, _P), pow(g, steps - 2, _P)
    quotients = (
        (f0 - 1) * pow(x - 1, -1, _P),
        (f0 - 1) * pow(x - g, -1, _P),
        (f0 - result) * pow(x - last, -1, _P),
        (f2 - f1 - f0) * (x - before_last) * (x - last) * pow(pow(x, steps, _P) - 1, -1, _P),
    )
    return sum(a * q for a, q in zip(alphas, quotients, strict=True)) % _P


def _transcript(steps: int, result: int, root: bytes) -> tuple[Transcript, list[int]]:
    transcript = Transcript(b"stark-fibonacci")
    transcript.append("statement", [steps, result % _P, root])
    return transcript, [transcript.challenge(f"alpha{k}", _P) for k in range(4)]


def stark_prove(
    steps: int, *, claimed: int | None = None, blowup: int = 8, num_queries: int = 16
) -> StarkProof:
    """Prove that the Fibonacci sequence from 1, 1 reaches ``claimed`` after ``steps`` terms.

    Parameters
    ----------
    steps : int
        T, a power of two, at least 4.
    claimed : int, optional
        The claimed last term; the true one by default. A false claim still
        yields a "proof", which fails verification.
    blowup : int
        The low-degree extension's size over T: the code's inverse rate.
    num_queries : int
        FRI queries; each also opens the trace.

    Returns
    -------
    StarkProof

    Examples
    --------
    >>> from blockchainkit.proofs import stark_prove, stark_verify
    >>> proof = stark_prove(16)
    >>> stark_verify(proof, steps=16, result=987), stark_verify(proof, steps=16, result=988)
    (True, False)
    """
    _check(steps, blowup, num_queries)
    trace = fibonacci_trace(steps)
    result = trace[-1] if claimed is None else claimed
    integer(result, "claimed")
    n = steps * blowup
    extension = evaluate_on_domain(interpolate_on_domain(trace), n, offset=FIELD_GENERATOR)
    tree = MerkleTree(v.to_bytes(8, "big") for v in extension)
    transcript, alphas = _transcript(steps, result, tree.root)
    w = root_of_unity(n)
    composition, x = [], FIELD_GENERATOR
    for i in range(n):
        values = (extension[i], extension[(i + blowup) % n], extension[(i + 2 * blowup) % n])
        composition.append(_composition(values, x, steps, result, alphas))
        x = x * w % _P
    fri = fri_prove(composition, steps, num_queries=num_queries, transcript=transcript)
    openings = []
    for query in fri.queries:
        for position in (query.index, query.index + n // 2):
            trio = [(position + k * blowup) % n for k in range(3)]
            openings.append(
                TraceOpening(tuple(extension[j] for j in trio), tuple(tree.proof(j) for j in trio))
            )
    return StarkProof(tree.root, fri, tuple(openings))


def stark_verify(
    proof: StarkProof, *, steps: int, result: int, blowup: int = 8, num_queries: int = 16
) -> bool:
    """Check FRI on the composition, then its values against the opened trace."""
    _check(steps, blowup, num_queries)
    integer(result, "result")
    if not isinstance(proof, StarkProof) or len(proof.trace_openings) != 2 * num_queries:
        return False
    n = steps * blowup
    transcript, alphas = _transcript(steps, result, proof.trace_root)
    if not fri_verify(
        proof.fri, domain_size=n, degree_bound=steps, num_queries=num_queries, transcript=transcript
    ):
        return False
    w = root_of_unity(n)
    for k, query in enumerate(proof.fri.queries):
        first = query.layers[0]
        for opening, position, opened in (
            (proof.trace_openings[2 * k], query.index, first.low),
            (proof.trace_openings[2 * k + 1], query.index + n // 2, first.high),
        ):
            trio = [(position + j * blowup) % n for j in range(3)]
            if len(opening.values) != 3 or len(opening.paths) != 3:
                return False
            for value, path, where in zip(opening.values, opening.paths, trio, strict=True):
                if type(value) is not int or not 0 <= value < _P or path.index != where:
                    return False
                if not verify_proof(value.to_bytes(8, "big"), path, proof.trace_root):
                    return False
            x = FIELD_GENERATOR * pow(w, position, _P) % _P
            values = (opening.values[0], opening.values[1], opening.values[2])
            if _composition(values, x, steps, result, alphas) != opened:
                return False
    return True
