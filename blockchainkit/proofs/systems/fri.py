"""FRI: fast Reed-Solomon interactive oracle proofs of proximity (2018).

Ben-Sasson, Bentov, Horesh and Riabzev showed how to check, with a few
hash-based queries, that a committed list of N values is (close to) the
evaluations of a polynomial of degree below d, a Reed-Solomon codeword.
Split f into even and odd parts, ``f(X) = f_e(X**2) + X f_o(X**2)``; a
random alpha folds them into one polynomial of half the degree on a
domain of half the size,

    f'(x**2) = (f(x) + f(-x)) / 2 + alpha (f(x) - f(-x)) / (2 x).

The prover commits to each layer with a Merkle tree, and after log2(d)
folds the polynomial is a constant. The verifier picks random positions
and checks each fold from two Merkle-opened values. A function far from
every low-degree polynomial stays far after folding whp, so each query
catches it with constant probability: no trusted setup, only hashes.

Domains are cosets ``offset * <w>`` of power-of-two subgroups of the
BabyBear field; the challenges come from a Fiat-Shamir transcript.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.proofs.core.base import FRILayerOpening, FRIProof, FRIQuery
from blockchainkit.proofs.utils.polynomials import FIELD_GENERATOR, FIELD_PRIME, root_of_unity
from blockchainkit.proofs.utils.transcript import Transcript
from blockchainkit.structures.systems.merkle import MerkleTree, verify_proof

_P = FIELD_PRIME


def _leaf(value: int) -> bytes:
    return value.to_bytes(8, "big")


def _fold(low: int, high: int, x: int, alpha: int) -> int:
    """The folded value at x**2 from f(x) = low and f(-x) = high."""
    half = pow(2, -1, _P)
    return ((low + high) * half + alpha * (low - high) * half * pow(x, -1, _P)) % _P


def _check_parameters(domain_size: int, degree_bound: int, num_queries: int, offset: int) -> int:
    for value, name in ((domain_size, "domain_size"), (degree_bound, "degree_bound")):
        integer(value, name, 2)
        if value & (value - 1):
            raise ValueError(f"{name} must be a power of two")
    if degree_bound * 2 > domain_size:
        raise ValueError("the domain must be at least twice the degree bound")
    integer(num_queries, "num_queries", 1)
    integer(offset, "offset", 1)
    root_of_unity(domain_size)
    return degree_bound.bit_length() - 1


def fri_prove(
    evaluations: Sequence[int],
    degree_bound: int,
    *,
    offset: int = FIELD_GENERATOR,
    num_queries: int = 8,
    transcript: Transcript | None = None,
) -> FRIProof:
    """Commit to evaluations on ``offset * <w>`` and prove they have degree below ``degree_bound``.

    Parameters
    ----------
    evaluations : sequence of int
        Values at ``offset * w**i`` for i < N, with N a power of two.
    degree_bound : int
        A power of two, at most N / 2; N / degree_bound is the blowup.
    offset : int
        The coset shift.
    num_queries : int
        Positions the verifier checks.
    transcript : Transcript, optional
        Continue an existing Fiat-Shamir transcript, as a STARK does.

    Returns
    -------
    FRIProof

    Examples
    --------
    >>> from blockchainkit.proofs import evaluate_on_domain, fri_prove, fri_verify
    >>> values = evaluate_on_domain(range(1, 9), 32, offset=31)  # degree 7 on 32 points
    >>> proof = fri_prove(values, 8)
    >>> fri_verify(proof, domain_size=32, degree_bound=8)
    True
    """
    n = len(evaluations)
    rounds = _check_parameters(n, degree_bound, num_queries, offset)
    if transcript is None:
        transcript = Transcript(b"fri")
    layer = [v % _P for v in evaluations]
    shift, w = offset % _P, root_of_unity(n)
    layers, trees = [layer], []
    for _ in range(rounds):
        tree = MerkleTree(_leaf(v) for v in layer)
        trees.append(tree)
        transcript.append("root", tree.root)
        alpha = transcript.challenge("alpha", _P)
        half = len(layer) // 2
        x, folded = shift, []
        for i in range(half):
            folded.append(_fold(layer[i], layer[i + half], x, alpha))
            x = x * w % _P
        layer, shift, w = folded, shift * shift % _P, w * w % _P
        layers.append(layer)
    final = layer[0]
    transcript.append("final", final)
    queries = []
    for _ in range(num_queries):
        index = transcript.challenge("query", n // 2)
        openings = []
        for k, tree in enumerate(trees):
            half = len(layers[k]) // 2
            i = index % half
            openings.append(
                FRILayerOpening(
                    layers[k][i], tree.proof(i), layers[k][i + half], tree.proof(i + half)
                )
            )
        queries.append(FRIQuery(index, tuple(openings)))
    return FRIProof(tuple(t.root for t in trees), final, tuple(queries))


def fri_verify(
    proof: FRIProof,
    *,
    domain_size: int,
    degree_bound: int,
    offset: int = FIELD_GENERATOR,
    num_queries: int = 8,
    transcript: Transcript | None = None,
) -> bool:
    """Check every query's Merkle openings and folds, down to the final constant.

    The query positions must be the ones the transcript dictates, so a
    caller that continues the transcript (a STARK) can trust
    ``proof.queries[k].index`` once this returns True.
    """
    rounds = _check_parameters(domain_size, degree_bound, num_queries, offset)
    if not isinstance(proof, FRIProof) or len(proof.roots) != rounds:
        return False
    if len(proof.queries) != num_queries or type(proof.final) is not int:
        return False
    if transcript is None:
        transcript = Transcript(b"fri")
    alphas = []
    for root in proof.roots:
        transcript.append("root", root)
        alphas.append(transcript.challenge("alpha", _P))
    transcript.append("final", proof.final)
    w0 = root_of_unity(domain_size)
    for query in proof.queries:
        if query.index != transcript.challenge("query", domain_size // 2):
            return False
        if len(query.layers) != rounds:
            return False
        size, shift, w = domain_size, offset % _P, w0
        expected, position = None, 0
        for k, opening in enumerate(query.layers):
            half = size // 2
            i = query.index % half
            for value, path, where in (
                (opening.low, opening.low_path, i),
                (opening.high, opening.high_path, i + half),
            ):
                if type(value) is not int or not 0 <= value < _P or path.index != where:
                    return False
                if not verify_proof(_leaf(value), path, proof.roots[k]):
                    return False
            # The previous layer's fold landed at ``position``: i or i + half here.
            if expected is not None and expected != (
                opening.low if position == i else opening.high
            ):
                return False
            expected, position = (
                _fold(opening.low, opening.high, shift * pow(w, i, _P), alphas[k]),
                i,
            )
            size, shift, w = half, shift * shift % _P, w * w % _P
        if expected != proof.final % _P:
            return False
    return True
