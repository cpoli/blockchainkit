"""Result containers for blockchainkit.channels."""

from collections.abc import Mapping
from dataclasses import dataclass

from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.structures.core.base import MerkleProof, SparseMerkleProof


@dataclass(frozen=True)
class Settlement:
    """How a channel was closed on chain, and who received what.

    Attributes
    ----------
    kind : str
        ``"cooperative"``, ``"unilateral"``, ``"penalty"`` or ``"refund"``.
    payouts : Mapping
        Coins paid to each party.
    height : int
        The block at which the last output was claimed.
    state : int
        The off-chain state that was settled.
    """

    kind: str
    payouts: Mapping[str, int]
    height: int
    state: int


@dataclass(frozen=True)
class SwapOutcome:
    """Who ended up with which coins after an atomic swap between chains A and B.

    Attributes
    ----------
    alice, bob : tuple of int
        Coins each party holds on chain A and on chain B, out of the swap's outputs.
    secret_revealed : bool
        True if Alice's preimage appeared on chain B.
    """

    alice: tuple[int, int]
    bob: tuple[int, int]
    secret_revealed: bool

    @property
    def completed(self) -> bool:
        """True if both parties received the other chain's coins."""
        return self.alice[0] == self.bob[1] == 0 and self.alice[1] > 0 and self.bob[0] > 0

    @property
    def refunded(self) -> bool:
        """True if both parties took their own coins back."""
        return self.alice[1] == self.bob[0] == 0 and self.alice[0] > 0 and self.bob[1] > 0

    @property
    def atomic(self) -> bool:
        """True if the swap either completed or was refunded, so nobody lost."""
        return self.completed or self.refunded


@dataclass(frozen=True)
class Commitment:
    """One party's commitment transaction in a Lightning channel.

    Attributes
    ----------
    holder : str
        The party who can publish it.
    state : int
        The channel state it records.
    to_local : int
        The holder's balance, locked behind the revocable delay.
    to_remote : int
        The counterparty's balance, paid at once.
    revocation : tuple of int
        The public key that lets the counterparty take ``to_local`` once revoked.
    txid : bytes
        Hash identifying the transaction.
    """

    holder: str
    state: int
    to_local: int
    to_remote: int
    revocation: tuple[int, int]
    txid: bytes


@dataclass(frozen=True)
class Route:
    """A payment route and what each hop forwards.

    Attributes
    ----------
    nodes : tuple of int
        Sender first, recipient last.
    amounts : tuple of int
        The HTLC amount offered on each hop, ``len(nodes) - 1`` of them.
    expiries : tuple of int
        Each hop's HTLC expiry (an absolute block height).
    """

    nodes: tuple[int, ...]
    amounts: tuple[int, ...]
    expiries: tuple[int, ...]

    @property
    def fee(self) -> int:
        """What the sender pays the intermediate nodes."""
        return self.amounts[0] - self.amounts[-1]


@dataclass(frozen=True)
class PaymentAttempt:
    """The result of sending a payment along a route.

    Attributes
    ----------
    success : bool
        True if the recipient received the payment.
    route : Route
        The route tried.
    failed_at : tuple of int or None
        The channel ``(from, to)`` where the HTLC was refused, if it was.
    error : str or None
        ``"temporary_channel_failure"`` (not enough balance) or
        ``"unknown_payment_hash"`` (the recipient cannot claim it).
    """

    success: bool
    route: Route
    failed_at: tuple[int, int] | None
    error: str | None


@dataclass(frozen=True)
class ProbeResult:
    """What an outsider learned about one side of a channel by sending probes.

    Attributes
    ----------
    low, high : int
        The balance lies in ``[low, high]``.
    probes : int
        Payments sent.
    """

    low: int
    high: int
    probes: int


@dataclass(frozen=True)
class CoinTransfer:
    """A Plasma Cash transfer of one coin, signed by its previous owner.

    Attributes
    ----------
    coin : int
        The coin's identifier, its slot in the sparse Merkle tree.
    owner : tuple of int
        The new owner's public key.
    parent_block : int
        The block holding the previous transfer of the coin (0 for a deposit).
    signature : SchnorrSignature or None
        The previous owner's signature; None for a deposit.
    """

    coin: int
    owner: tuple[int, int]
    parent_block: int
    signature: SchnorrSignature | None = None


@dataclass(frozen=True)
class InclusionProof:
    """A transfer, the block it is in, and the sparse Merkle proof that it is.

    Attributes
    ----------
    transfer : CoinTransfer
    block : int
    proof : SparseMerkleProof
    """

    transfer: CoinTransfer
    block: int
    proof: SparseMerkleProof


@dataclass(frozen=True)
class PlasmaExit:
    """An exit from the Plasma chain, waiting out its challenge period.

    Attributes
    ----------
    coin : int
    owner : tuple of int
        Who receives the coin if the exit stands.
    block : int
        The block of the exiting transfer.
    parent_block : int
        The block of the transfer before it.
    deadline : int
        The height from which the exit can be finalized.
    status : str
        ``"pending"``, ``"challenged"`` or ``"finalized"``.
    """

    coin: int
    owner: tuple[int, int]
    block: int
    parent_block: int
    deadline: int
    status: str = "pending"


@dataclass(frozen=True)
class AtomixResult:
    """A cross-shard transfer by Atomix's lock, then commit or abort.

    Attributes
    ----------
    committed : bool
        True if every input shard accepted and the output was credited.
    balances : tuple of Mapping
        Each shard's balances afterwards.
    rejected : tuple of int
        The input shards that refused to lock.
    """

    committed: bool
    balances: tuple[Mapping[str, int], ...]
    rejected: tuple[int, ...]


@dataclass(frozen=True)
class Transfer:
    """A rollup transaction: move ``amount`` from ``sender`` to ``recipient``."""

    sender: str
    recipient: str
    amount: int


@dataclass(frozen=True)
class ValidityProof:
    """The statement a zk-rollup's proof attests: this batch takes ``old_root`` to ``new_root``.

    Attributes
    ----------
    old_root, new_root : bytes
        State roots before and after the batch.
    batch_digest : bytes
        Hash of the batch's transactions.
    """

    old_root: bytes
    new_root: bytes
    batch_digest: bytes


@dataclass(frozen=True)
class FraudProof:
    """The single step at which an optimistic rollup's assertion went wrong.

    Attributes
    ----------
    step : int
        The transaction whose execution the assertion got wrong (0-based).
    rounds : int
        Bisection rounds the challenge game took.
    claimed, correct : bytes
        The asserted and the true state root after that step.
    """

    step: int
    rounds: int
    claimed: bytes
    correct: bytes


@dataclass(frozen=True)
class ErasureCodedData:
    """A block's data extended with Reed-Solomon parity and committed to by a Merkle root.

    Attributes
    ----------
    k : int
        Data symbols; any ``k`` shares recover them.
    shares : tuple of int
        The codeword.
    root : bytes
        Merkle root over the shares.
    """

    k: int
    shares: tuple[int, ...]
    root: bytes


@dataclass(frozen=True)
class EncodingFraudProof:
    """Evidence that a block producer's shares do not form a Reed-Solomon codeword.

    Attributes
    ----------
    positions : tuple of int
        ``k + 1`` share positions.
    shares : tuple of int
        Their values.
    proofs : tuple of MerkleProof
        Each share's inclusion proof against the block's root.
    """

    positions: tuple[int, ...]
    shares: tuple[int, ...]
    proofs: tuple[MerkleProof, ...]


@dataclass(frozen=True)
class SamplingResult:
    """Light clients sampling a block whose producer withholds some shares.

    Attributes
    ----------
    detected : float
        Fraction of clients that asked for a withheld share.
    collected : int
        Distinct shares that clients' samples brought to the network.
    recoverable : bool
        True if the collected shares are enough to rebuild the data.
    """

    detected: float
    collected: int
    recoverable: bool


@dataclass(frozen=True)
class AppointmentReceipt:
    """A watchtower's signed promise to watch for one revoked commitment (PISA).

    Attributes
    ----------
    tower : tuple of int
        The watchtower's public key.
    hint : bytes
        Half the revoked commitment's txid, which the tower watches for.
    expires : int
        The last height the tower is responsible for.
    signature : SchnorrSignature
    """

    tower: tuple[int, int]
    hint: bytes
    expires: int
    signature: SchnorrSignature
