r"""Fraud proofs and data-availability sampling (Al-Bassam, Sonnino and Buterin, 2018).

A light client checks headers, not blocks, and fraud proofs let it reject
an invalid block if one honest full node complains. But a fraud proof needs
the block's data, and a producer can publish a header and withhold part of
the data, so that nobody can prove anything. Al-Bassam, Sonnino and Buterin
made withholding detectable. The producer extends the data with a
Reed-Solomon code and commits to all the shares with a Merkle root. Any
half of the shares rebuilds the rest, so to hide anything the producer
must withhold more than half of them, and then a client that downloads
``s`` random shares, with their Merkle proofs, notices with probability

.. math::

   1 - \left(1 - \tfrac{1}{2}\right)^s,

already above 99% for ``s = 7``. Many clients sampling also collect enough
shares between them to rebuild the block.

A producer could instead publish shares that are not a codeword, so that
different halves rebuild different data. That is caught by an *encoding
fraud proof*: ``k`` shares that fix the polynomial, and one more that is
not on it, each with its Merkle proof.

The paper arranges the shares in a two-dimensional square, so that a
fraud proof needs one row, about the square root of the block; this
module uses one dimension, so a fraud proof holds ``k + 1`` shares.
"""

from collections.abc import Collection
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.channels.core.base import EncodingFraudProof, ErasureCodedData, SamplingResult
from blockchainkit.channels.systems.reed_solomon import is_codeword, rs_encode
from blockchainkit.channels.utils.field import PRIME, interpolate
from blockchainkit.structures.core.base import MerkleProof
from blockchainkit.structures.systems.merkle import MerkleTree, verify_proof


def _leaf(value: int) -> bytes:
    return value.to_bytes(8, "big")


def commit_shares(k: int, shares: tuple[int, ...]) -> ErasureCodedData:
    """Commit to ``shares`` as they are, whether or not they form a codeword."""
    integer(k, "k", 1)
    if len(shares) < k:
        raise ValueError("fewer shares than data symbols")
    return ErasureCodedData(k, shares, MerkleTree(_leaf(s) for s in shares).root)


def extend(
    data: tuple[int, ...] | list[int], *, factor: int = 2, prime: int = PRIME
) -> ErasureCodedData:
    """Extend ``data`` to ``factor * len(data)`` Reed-Solomon shares and commit to them.

    Examples
    --------
    >>> from blockchainkit.channels import extend
    >>> extend([3, 1, 4]).shares
    (3, 1, 4, 12, 25, 43)
    """
    integer(factor, "factor", 1)
    return commit_shares(len(data), rs_encode(data, factor * len(data), prime=prime))


def prove_share(block: ErasureCodedData, position: int) -> MerkleProof:
    """The Merkle proof a client receives with the share at ``position``."""
    return MerkleTree(_leaf(s) for s in block.shares).proof(position)


def verify_share(value: int, proof: MerkleProof, root: bytes) -> bool:
    """True if ``value`` is the share the root commits to at ``proof.index``."""
    return verify_proof(_leaf(value), proof, root)


def detection_probability(withheld: float, samples: int) -> float:
    """Chance that ``samples`` uniform draws (with replacement) hit a withheld share.

    Examples
    --------
    >>> from blockchainkit.channels import detection_probability
    >>> round(detection_probability(0.5, 7), 4)
    0.9922
    """
    integer(samples, "samples")
    if not 0 <= withheld <= 1:
        raise ValueError("withheld must be a fraction in [0, 1]")
    return 1 - (1 - withheld) ** samples


def simulate_sampling(
    block: ErasureCodedData,
    withheld: Collection[int],
    *,
    clients: int,
    samples: int,
    seed: int = 0,
) -> SamplingResult:
    """Clients each request ``samples`` distinct random shares from a producer withholding some.

    Parameters
    ----------
    block : ErasureCodedData
        What the producer committed to.
    withheld : collection of int
        Share positions the producer refuses to serve.
    clients, samples : int
        Number of light clients and shares each requests.
    seed : int
        Seeds the clients' choices.

    Returns
    -------
    SamplingResult
    """
    integer(clients, "clients", 1)
    integer(samples, "samples", 1)
    check_seed(seed)
    n = len(block.shares)
    if samples > n:
        raise ValueError("more samples than shares")
    hidden = set(withheld)
    rng = Random(seed)
    collected: set[int] = set()
    detected = 0
    for _ in range(clients):
        chosen = rng.sample(range(n), samples)
        if hidden.intersection(chosen):
            detected += 1
        collected.update(p for p in chosen if p not in hidden)
    return SamplingResult(detected / clients, len(collected), len(collected) >= block.k)


def encoding_fraud_proof(
    block: ErasureCodedData, *, prime: int = PRIME
) -> EncodingFraudProof | None:
    """Prove that the committed shares are not a codeword; None if they are one.

    The first ``k`` shares fix the polynomial; the proof adds the first
    share that is not on it.
    """
    shares = dict(enumerate(block.shares))
    if is_codeword(shares, block.k, prime=prime):
        return None
    basis = [(x, shares[x]) for x in range(block.k)]
    bad = next(x for x in range(block.k, len(shares)) if interpolate(basis, x, prime) != shares[x])
    positions = (*range(block.k), bad)
    return EncodingFraudProof(
        positions,
        tuple(block.shares[p] for p in positions),
        tuple(prove_share(block, p) for p in positions),
    )


def verify_encoding_fraud_proof(
    proof: EncodingFraudProof, root: bytes, k: int, *, prime: int = PRIME
) -> bool:
    """Check an encoding fraud proof against a header's data root, without the block.

    Examples
    --------
    >>> from blockchainkit.channels import (
    ...     commit_shares, encoding_fraud_proof, verify_encoding_fraud_proof)
    >>> bad = commit_shares(3, (3, 1, 4, 12, 26, 43))  # The share at 4 is off the parabola.
    >>> proof = encoding_fraud_proof(bad)
    >>> proof.positions, verify_encoding_fraud_proof(proof, bad.root, 3)
    ((0, 1, 2, 4), True)
    """
    integer(k, "k", 1)
    positions = proof.positions
    sizes = {len(positions), len(set(positions)), len(proof.shares), len(proof.proofs)}
    if sizes != {k + 1}:
        return False
    for position, value, merkle in zip(positions, proof.shares, proof.proofs, strict=True):
        if merkle.index != position or not verify_share(value, merkle, root):
            return False
    basis = list(zip(positions[:k], proof.shares[:k], strict=True))
    return interpolate(basis, positions[k], prime) != proof.shares[k] % prime
