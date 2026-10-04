"""Result containers for blockchainkit.structures."""

from dataclasses import dataclass

from blockchainkit._validation import integer


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


@dataclass(frozen=True, order=True)
class OutPoint:
    """A reference to one coin: the creating transaction's id and the output index."""

    txid: bytes
    index: int

    def __post_init__(self) -> None:
        if not isinstance(self.txid, bytes) or len(self.txid) != 32:
            raise ValueError("txid must be 32 bytes")
        integer(self.index, "index")

    def __repr__(self) -> str:
        return f"OutPoint({self.txid.hex()[:12]}..., {self.index})"


@dataclass(frozen=True)
class Coin:
    """An unspent output: who owns it and how much it holds."""

    owner: str
    amount: int


@dataclass(frozen=True)
class SparseMerkleProof:
    """Siblings from the leaf up, and the value at the key (None if absent)."""

    key: bytes
    value: bytes | None
    siblings: tuple[bytes, ...]


@dataclass(frozen=True)
class MMRProof:
    """Path from a leaf to its peak, plus every peak and the range size."""

    index: int
    size: int
    siblings: tuple[bytes, ...]
    peaks: tuple[bytes, ...]
