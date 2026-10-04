"""Shared types and result containers for blockchainkit.crypto."""

from dataclasses import dataclass

Point = tuple[int, int] | None
"""An affine curve point ``(x, y)``, or ``None`` for the point at infinity."""


@dataclass(frozen=True)
class SchnorrSignature:
    """A finite commitment point R and response scalar s."""

    commitment: tuple[int, int]
    response: int


@dataclass(frozen=True)
class DiscreteLogResult:
    """An exponent x with base**x = target, and the work spent finding it.

    Attributes
    ----------
    exponent : int
        The smallest non-negative solution.
    group_operations : int
        Group multiplications in the baby-step and giant-step tables, the
        dominant cost.
    """

    exponent: int
    group_operations: int


@dataclass(frozen=True)
class CollisionResult:
    """Two distinct inputs whose truncated hashes agree.

    Attributes
    ----------
    first, second : bytes
        The colliding inputs.
    digest : int
        Their shared truncated hash.
    trials : int
        Hashes computed before the collision appeared.
    """

    first: bytes
    second: bytes
    digest: int
    trials: int


@dataclass(frozen=True)
class PuzzleSolution:
    """The contents of one solved Merkle puzzle, and the trials it took.

    Attributes
    ----------
    puzzle_id : bytes
        The identifier the solver announces publicly.
    key : bytes
        The session key, which stays secret.
    trials : int
        Weak keys tried before the puzzle opened.
    """

    puzzle_id: bytes
    key: bytes
    trials: int


@dataclass(frozen=True)
class LamportKeyPair:
    """A Lamport one-time key: 256 pairs of secret preimages and their hashes.

    Attributes
    ----------
    private : tuple
        256 pairs of bytes: for each digest bit, the preimage revealed when
        that bit is 0 or 1.
    public : tuple
        256 pairs of bytes: the SHA-256 of each private preimage.
    """

    private: tuple[tuple[bytes, bytes], ...]
    public: tuple[tuple[bytes, bytes], ...]

    def __repr__(self) -> str:
        return (
            f"LamportKeyPair(public[0]={self.public[0][0].hex()[:16]}..., pairs={len(self.public)})"
        )


@dataclass(frozen=True)
class FeldmanShares:
    """Shamir shares plus public commitments that let each holder check theirs.

    Attributes
    ----------
    shares : tuple
        ``(x, f(x))`` pairs of int, points over the integers modulo the group
        order q.
    commitments : tuple of int
        ``g**a_j mod p`` for each polynomial coefficient ``a_j``.
    """

    shares: tuple[tuple[int, int], ...]
    commitments: tuple[int, ...]
