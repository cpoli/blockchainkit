"""Shared types and result containers for blockchainkit.crypto."""

from dataclasses import dataclass

Point = tuple[int, int] | None
"""An affine curve point ``(x, y)``, or ``None`` for the point at infinity."""


@dataclass(frozen=True)
class SchnorrSignature:
    """A finite commitment point R and response scalar s."""

    commitment: tuple[int, int]
    response: int
