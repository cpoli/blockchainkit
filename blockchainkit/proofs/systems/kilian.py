"""Succinct arguments from Merkle commitments: Kilian (1992) and Micali's CS proofs (1994).

A PCP is short to *check* but long to *send*: the Hadamard proof of an
n-variable system has 2**n + 2**(n**2) bits. Kilian's argument sends only
a Merkle root of the PCP. The verifier then picks its random queries, and
the prover opens each queried bit with its authentication path. The
prover cannot change an answer after committing without finding a hash
collision, so communication drops to the root plus a logarithmic path
per query.

Micali removed the interaction: the queries are derived by hashing the
root, so the prover writes the whole argument down at once, a
*computationally sound proof*. Soundness then rests on the hash behaving
like a random oracle, and a cheating prover can grind: change the
commitment (here, a salt) and rehash until the queries miss its lies.
"""

from collections.abc import Callable
from random import Random

from blockchainkit import _validation
from blockchainkit._validation import integer
from blockchainkit.proofs.core.base import (
    CSProof,
    HadamardProof,
    KilianRun,
    Opening,
    QuadraticSystem,
)
from blockchainkit.proofs.systems.pcp import run_pcp_verifier
from blockchainkit.proofs.utils.transcript import Transcript
from blockchainkit.structures.systems.merkle import MerkleTree, verify_proof


def commit_pcp(proof: HadamardProof) -> MerkleTree:
    """Build a Merkle tree whose leaf i is bit i of the PCP, one byte per leaf."""
    if not isinstance(proof, HadamardProof):
        raise TypeError("proof must be a HadamardProof")
    return MerkleTree(bytes([bit]) for bit in proof.bits)


def _opening_bytes(tree: MerkleTree, position: int) -> int:
    return 9 + 32 * sum(s is not None for s in tree.proof(position).siblings)


def kilian_argument(
    system: QuadraticSystem,
    proof: HadamardProof,
    *,
    repetitions: int = 1,
    seed: int = 0,
    respond: Callable[[int], int] | None = None,
) -> KilianRun:
    """Run Kilian's interactive argument for a quadratic system.

    The prover commits to ``proof`` and sends the root; the verifier then
    draws the PCP queries from ``seed``; the prover answers each with a bit
    and the Merkle path of the committed bit.

    Parameters
    ----------
    system : QuadraticSystem
    proof : HadamardProof
        The PCP the prover commits to.
    repetitions : int
        Repetitions of the PCP verifier.
    seed : int
        Seed of the verifier's queries, drawn after the root is sent.
    respond : callable, optional
        A cheating prover's answer for each queried position, in place of
        the committed bit. The path it sends is the committed one.

    Returns
    -------
    KilianRun

    Examples
    --------
    >>> from blockchainkit.proofs import QuadraticSystem, hadamard_proof, kilian_argument
    >>> system = QuadraticSystem(3, ((((0, 1), (2, 2)), 1),))
    >>> run = kilian_argument(system, hadamard_proof([1, 1, 0]), repetitions=4)
    >>> run.accepted, run.queries
    (True, 56)
    """
    integer(repetitions, "repetitions", 1)
    _validation.seed(seed)
    tree = commit_pcp(proof)
    root = tree.root
    bits = proof.bits
    sent, valid = 32, True

    def oracle(position: int) -> int:
        nonlocal sent, valid
        bit = bits[position] if respond is None else respond(position)
        sent += _opening_bytes(tree, position)
        if bit not in (0, 1) or not verify_proof(bytes([bit]), tree.proof(position), root):
            valid = False
        return bit

    run = run_pcp_verifier(system, oracle, Random(seed), repetitions)
    return KilianRun(root, run.accepted and valid, run.queries, sent, len(bits))


def _query_rng(system: QuadraticSystem, root: bytes, salt: int) -> Random:
    transcript = Transcript(b"micali-cs-proof")
    transcript.append(
        "system", [system.num_variables, [[list(map(list, t)), c] for t, c in system.equations]]
    )
    transcript.append("root", root)
    transcript.append("salt", salt)
    return Random(transcript.challenge("queries", 2**64 - 1))


def micali_proof(
    system: QuadraticSystem, proof: HadamardProof, *, repetitions: int = 1, salt: int = 0
) -> CSProof:
    """Write a non-interactive CS proof: the queries come from hashing the root and a salt.

    Examples
    --------
    >>> from blockchainkit.proofs import (
    ...     QuadraticSystem, hadamard_proof, micali_proof, verify_cs_proof)
    >>> system = QuadraticSystem(3, ((((0, 1), (2, 2)), 1),))
    >>> cs = micali_proof(system, hadamard_proof([1, 1, 0]), repetitions=4)
    >>> verify_cs_proof(system, cs, repetitions=4)
    True
    """
    integer(repetitions, "repetitions", 1)
    integer(salt, "salt")
    tree = commit_pcp(proof)
    bits = proof.bits
    openings: list[Opening] = []

    def oracle(position: int) -> int:
        openings.append(Opening(position, bits[position], tree.proof(position)))
        return bits[position]

    run_pcp_verifier(system, oracle, _query_rng(system, tree.root, salt), repetitions)
    return CSProof(tree.root, salt, tuple(openings))


def verify_cs_proof(system: QuadraticSystem, cs_proof: CSProof, *, repetitions: int = 1) -> bool:
    """Re-derive the queries from the root and salt, and check every opening and PCP test."""
    if not isinstance(system, QuadraticSystem) or not isinstance(cs_proof, CSProof):
        raise TypeError("need a QuadraticSystem and a CSProof")
    integer(repetitions, "repetitions", 1)
    remaining = list(cs_proof.openings)
    valid = True

    def oracle(position: int) -> int:
        nonlocal valid
        if not remaining:
            valid = False
            return 0
        opening = remaining.pop(0)
        if opening.position != position or opening.path.index != position:
            valid = False
            return 0
        if opening.bit not in (0, 1) or not verify_proof(
            bytes([opening.bit]), opening.path, cs_proof.root
        ):
            valid = False
            return 0
        return opening.bit

    rng = _query_rng(system, cs_proof.root, cs_proof.salt)
    run = run_pcp_verifier(system, oracle, rng, repetitions)
    return run.accepted and valid and not remaining
