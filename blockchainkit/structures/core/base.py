"""Result containers for blockchainkit.structures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MerkleProof:
    """Leaf position, leaf count, and bottom-up siblings (None for promotion)."""

    index: int
    leaf_count: int
    siblings: tuple[bytes | None, ...]


@dataclass(frozen=True)
class ProofStep:
    """One level of Merkle-proof verification, from the leaf toward the root.

    Attributes
    ----------
    side : {"left", "right", "promoted"}
        Where the sibling sits: ``"left"`` means hash(sibling || current),
        ``"right"`` means hash(current || sibling), and ``"promoted"`` means
        the node had no sibling and moved up unchanged.
    sibling : bytes or None
        The sibling digest from the proof (``None`` when promoted).
    digest : bytes
        The node digest after this step.
    """

    side: str
    sibling: bytes | None
    digest: bytes


@dataclass(frozen=True)
class MerkleTrace:
    """Every step of reconstructing a root from a leaf and its proof.

    Attributes
    ----------
    leaf_digest : bytes
        The domain-separated hash of the leaf payload.
    steps : tuple of ProofStep
        Bottom-up reconstruction steps.
    root : bytes
        The count-bound root the proof reconstructs.
    valid : bool
        Whether that root equals the trusted root.
    """

    leaf_digest: bytes
    steps: tuple[ProofStep, ...]
    root: bytes
    valid: bool
