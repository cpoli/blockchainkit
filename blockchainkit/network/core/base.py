"""Event records for blockchainkit.network."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Delivery:
    """First receipt of a byte payload at a peer at integer simulation time."""

    time: int
    sender: str
    recipient: str
    payload: bytes
