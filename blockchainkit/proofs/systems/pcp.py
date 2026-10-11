"""Probabilistically checkable proofs: the Hadamard PCP for quadratic equations (1992).

The PCP theorem (Arora and Safra; Arora, Lund, Motwani, Sudan and Szegedy,
1992) says every NP statement has a proof that a verifier checks by
reading a constant number of its bits, chosen at random, and rejecting a
false statement with constant probability. This module implements the
first step of the ALMSS proof: an *exponentially long* proof checked with
14 queries.

The statement is that a system of quadratic equations over GF(2) has a
solution u. The proof writes out the Hadamard encodings of u and of
u (x) u: every parity ``<u, x>`` and every ``<u (x) u, y>``. The verifier
tests that both tables are linear functions (Blum, Luby and Rubinfeld,
1990), that the second is the tensor square of the first, and that a
random combination of the equations holds, reading each table through
self-correction, ``f(x) = f(x + s) - f(s)``, so that a few corrupted entries
cannot be targeted.
"""

from collections.abc import Callable, Sequence
from random import Random

from blockchainkit import _validation
from blockchainkit._validation import integer
from blockchainkit.proofs.core.base import HadamardProof, PCPRun, QuadraticSystem

Oracle = Callable[[int], int]
"""Reads one bit of a proof at a position of the concatenated tables."""


def hadamard_proof(assignment: Sequence[int]) -> HadamardProof:
    """Encode an assignment u as the tables of ``<u, x>`` and ``<u (x) u, y>``.

    Parameters
    ----------
    assignment : sequence of int
        Between 1 and 4 bits; the second table has 2**(n**2) entries.

    Examples
    --------
    >>> from blockchainkit.proofs import hadamard_proof
    >>> proof = hadamard_proof([1, 0, 1])
    >>> len(proof.linear), len(proof.quadratic)
    (8, 512)
    """
    n = len(assignment)
    if not 1 <= n <= 4 or any(bit not in (0, 1) for bit in assignment):
        raise ValueError("the assignment must be 1 to 4 bits")
    u = sum(bit << i for i, bit in enumerate(assignment))
    uu = sum(1 << (i * n + j) for i in range(n) for j in range(n) if u >> i & u >> j & 1)
    return HadamardProof(
        tuple((x & u).bit_count() & 1 for x in range(2**n)),
        tuple((y & uu).bit_count() & 1 for y in range(2 ** (n * n))),
    )


def _outer(r: int, s: int, n: int) -> int:
    return sum(1 << (i * n + j) for i in range(n) for j in range(n) if r >> i & s >> j & 1)


def run_pcp_verifier(
    system: QuadraticSystem, oracle: Oracle, rng: Random, repetitions: int
) -> PCPRun:
    """Run the Hadamard PCP verifier against any proof oracle.

    Positions below 2**n read the linear table; position 2**n + y reads
    entry y of the quadratic table. Each repetition makes 14 queries:
    linearity of both tables (3 + 3), tensor consistency (6), and one
    random combination of the equations (2).
    """
    n = system.num_variables
    linear_size, quadratic_size = 2**n, 2 ** (n * n)
    queries = 0

    def f(x: int) -> int:
        nonlocal queries
        queries += 1
        return oracle(x) & 1

    def g(y: int) -> int:
        nonlocal queries
        queries += 1
        return oracle(linear_size + y) & 1

    for _ in range(repetitions):
        x, y = rng.randrange(linear_size), rng.randrange(linear_size)
        if f(x) ^ f(y) != f(x ^ y):
            return PCPRun(False, queries, "linearity of the linear table")
        x, y = rng.randrange(quadratic_size), rng.randrange(quadratic_size)
        if g(x) ^ g(y) != g(x ^ y):
            return PCPRun(False, queries, "linearity of the quadratic table")
        r, r2, s, s2 = (rng.randrange(linear_size) for _ in range(4))
        t = rng.randrange(quadratic_size)
        left = (f(r ^ s) ^ f(s)) & (f(r2 ^ s2) ^ f(s2))
        if left != g(_outer(r, r2, n) ^ t) ^ g(t):
            return PCPRun(False, queries, "tensor consistency")
        mask, constant = 0, 0
        for equation in system.equations:
            if rng.randrange(2):
                mask ^= sum(1 << (i * n + j) for i, j in equation[0])
                constant ^= equation[1]
        t = rng.randrange(quadratic_size)
        if g(mask ^ t) ^ g(t) != constant:
            return PCPRun(False, queries, "the equations")
    return PCPRun(True, queries, None)


def pcp_verify(
    system: QuadraticSystem, proof: HadamardProof, *, repetitions: int = 1, seed: int = 0
) -> PCPRun:
    """Check a Hadamard proof by reading 14 random bits per repetition.

    A correct proof of a satisfiable system always passes. If the system
    has no solution, every proof is rejected with constant probability per
    repetition, so ``repetitions`` drives the error down exponentially.

    Examples
    --------
    >>> from blockchainkit.proofs import QuadraticSystem, hadamard_proof, pcp_verify
    >>> system = QuadraticSystem(2, ((((0, 1),), 1), (((0, 0),), 1)))  # u0 u1 = 1, u0 = 1
    >>> pcp_verify(system, hadamard_proof([1, 1]), repetitions=10).accepted
    True
    """
    if not isinstance(system, QuadraticSystem) or not isinstance(proof, HadamardProof):
        raise TypeError("need a QuadraticSystem and a HadamardProof")
    integer(repetitions, "repetitions", 1)
    _validation.seed(seed)
    n = system.num_variables
    if len(proof.linear) != 2**n or len(proof.quadratic) != 2 ** (n * n):
        raise ValueError("the proof's tables do not match the number of variables")
    table = proof.linear + proof.quadratic
    return run_pcp_verifier(system, table.__getitem__, Random(seed), repetitions)
