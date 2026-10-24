"""Result containers for blockchainkit.privacy."""

from dataclasses import dataclass

from blockchainkit.proofs.core.base import Groth16Proof


@dataclass(frozen=True)
class MixRun:
    """A batch of messages passed through a cascade of mixes.

    Attributes
    ----------
    batches : tuple of tuple of bytes
        What an observer of the wires sees: the batch entering the first mix,
        then the batch leaving each mix, in the order it was sent.
    permutations : tuple of tuple of int
        For each mix, ``permutations[k][j]`` is the position in its input
        batch of the message it sent ``j``-th. Only the mix knows it.
    delivered : tuple of tuple of str and bytes
        ``(recipient, message)`` pairs, in the order the last mix sent them.
    """

    batches: tuple[tuple[bytes, ...], ...]
    permutations: tuple[tuple[int, ...], ...]
    delivered: tuple[tuple[str, bytes], ...]

    def output_of(self, sender: int) -> int:
        """The position in :attr:`delivered` of the message that entered at ``sender``."""
        position = sender
        for permutation in self.permutations:
            position = permutation.index(position)
        return position

    def candidates(self, sender: int, corrupt: frozenset[int] = frozenset()) -> frozenset[int]:
        """Outputs that could be ``sender``'s, to an observer who learns the corrupt mixes' orders.

        An honest mix may have sent any input to any output, so from then on
        every position is a candidate.
        """
        positions = {sender}
        for k, permutation in enumerate(self.permutations):
            if k in corrupt:
                positions = {permutation.index(i) for i in positions}
            else:
                positions = set(range(len(permutation)))
        return frozenset(positions)


@dataclass(frozen=True)
class FlowObservation:
    """Packet times of low-latency flows, seen where they enter and leave an anonymity network.

    Attributes
    ----------
    entering : tuple of tuple of float
        Packet send times of each flow at its entry relay.
    leaving : tuple of tuple of float
        Packet times of each flow at its exit relay, in a shuffled order.
    truth : tuple of int
        ``truth[i]`` is the position in :attr:`leaving` of entering flow ``i``.
    """

    entering: tuple[tuple[float, ...], ...]
    leaving: tuple[tuple[float, ...], ...]
    truth: tuple[int, ...]


@dataclass(frozen=True)
class RingSignature:
    """A ring signature: the first challenge and one response per ring member.

    Attributes
    ----------
    challenge : int
        The challenge at member 0, from which the chain of challenges restarts.
    responses : tuple of int
        One response per member, in ring order.
    """

    challenge: int
    responses: tuple[int, ...]


@dataclass(frozen=True)
class LinkableRingSignature:
    """A (multilayered) linkable ring signature with the key image of its first column.

    Attributes
    ----------
    challenge : int
        The challenge at member 0.
    responses : tuple of tuple of int
        ``responses[i][j]`` answers for member ``i``'s key in column ``j``.
    key_image : int
        ``H_p(P)**x`` for the signer's first-column key ``P = g**x``: the same
        for every signature by that key, whatever the ring.
    """

    challenge: int
    responses: tuple[tuple[int, ...], ...]
    key_image: int


@dataclass(frozen=True)
class TransactionRecord:
    """A transaction as a block explorer shows it: addresses and amounts, in and out.

    Attributes
    ----------
    inputs : tuple of tuple of str and int
        ``(address, amount)`` of every coin spent; empty for newly minted coins.
    outputs : tuple of tuple of str and int
        ``(address, amount)`` of every coin created.
    """

    inputs: tuple[tuple[str, int], ...]
    outputs: tuple[tuple[str, int], ...]

    @property
    def fee(self) -> int:
        """Inputs minus outputs; 0 for a minting transaction."""
        if not self.inputs:
            return 0
        return sum(a for _, a in self.inputs) - sum(a for _, a in self.outputs)


@dataclass(frozen=True)
class PaymentHistory:
    """Simulated payments and the ground truth that an analyst does not have.

    Attributes
    ----------
    transactions : tuple of TransactionRecord
        Every transaction, in the order it was made.
    owners : dict
        Address to the user who owns it.
    """

    transactions: tuple[TransactionRecord, ...]
    owners: dict[str, str]


@dataclass(frozen=True)
class ClusterScore:
    """How well address clusters match the users who really own the addresses.

    Attributes
    ----------
    addresses : int
        Addresses clustered.
    users : int
        Distinct owners.
    clusters : int
        Clusters found; equal to ``users`` if clustering were perfect.
    false_merges : int
        Clusters that join addresses of two or more users.
    identified : int
        Users all of whose addresses lie in one cluster, with no one else's.
    largest : int
        Size of the largest cluster.
    """

    addresses: int
    users: int
    clusters: int
    false_merges: int
    identified: int
    largest: int


@dataclass(frozen=True)
class StealthKeys:
    """A CryptoNote wallet's two key pairs.

    Attributes
    ----------
    view_secret, spend_secret : int
        ``a`` finds incoming payments; ``b`` is needed to spend them.
    view_public, spend_public : int
        ``A = g**a`` and ``B = g**b``, published together as the address.
    """

    view_secret: int
    spend_secret: int
    view_public: int
    spend_public: int


@dataclass(frozen=True)
class StealthOutput:
    """A payment to a stealth address, as it appears on the ledger.

    Attributes
    ----------
    one_time_key : int
        ``P = g**H(A**r) * B``, the key the output is paid to.
    tx_public : int
        ``R = g**r``, published with the transaction so the payee can scan.
    """

    one_time_key: int
    tx_public: int


@dataclass(frozen=True)
class CoinJoinRound:
    """One CoinJoin transaction and who really owns each of its addresses.

    Attributes
    ----------
    transaction : TransactionRecord
        The joint transaction, outputs in shuffled order.
    owners : dict
        Address to participant, inputs and outputs alike.
    denomination : int
        The amount of every mixed output.
    """

    transaction: TransactionRecord
    owners: dict[str, str]
    denomination: int

    @property
    def anonymity_set(self) -> int:
        """The number of outputs of exactly the denomination, which nobody can tell apart."""
        return sum(1 for _, amount in self.transaction.outputs if amount == self.denomination)


@dataclass(frozen=True)
class ZerocoinSpend:
    """A Zerocoin spend: the coin's serial number and a proof that some minted coin holds it.

    Attributes
    ----------
    serial : int
        Revealed when spending, so the coin cannot be spent twice.
    proof : RingSignature
        Proof of knowing the opening of one of the minted coins with this serial.
    """

    serial: int
    proof: RingSignature


@dataclass(frozen=True)
class RingRangeProof:
    """A range proof from one two-member ring signature per bit.

    Attributes
    ----------
    bit_commitments : tuple of int
        ``C_k = g**(b_k 2**k) * h**r_k``, multiplying to the committed amount.
    signatures : tuple of RingSignature
        For each ``k``, a ring signature over ``{C_k, C_k / g**(2**k)}`` with
        base ``h``: one of them is ``h**r_k``, so ``b_k`` is 0 or 1.
    """

    bit_commitments: tuple[int, ...]
    signatures: tuple[RingSignature, ...]

    @property
    def bits(self) -> int:
        """Number of bits, so the amount lies in ``[0, 2**bits)``."""
        return len(self.bit_commitments)


@dataclass(frozen=True)
class ConfidentialOutput:
    """An output whose amount is hidden in a Pedersen commitment.

    Attributes
    ----------
    commitment : int
        ``g**amount * h**blinding``.
    range_proof : RingRangeProof
        Shows the amount is small and not negative.
    """

    commitment: int
    range_proof: RingRangeProof


@dataclass(frozen=True)
class RingCTTransaction:
    """A Ring Confidential Transaction with one input hidden in a ring.

    Attributes
    ----------
    ring : tuple of tuple of int
        ``(one-time key, amount commitment)`` of every possible input.
    outputs : tuple of ConfidentialOutput
        The new outputs.
    fee : int
        The public fee.
    signature : LinkableRingSignature
        Signs with the input's key and proves amounts balance, without
        saying which ring member is spent.
    """

    ring: tuple[tuple[int, int], ...]
    outputs: tuple[ConfidentialOutput, ...]
    fee: int
    signature: LinkableRingSignature


@dataclass(frozen=True)
class Kernel:
    """A Mimblewimble transaction kernel: the excess and a signature with it.

    Attributes
    ----------
    excess : int
        ``h**k``, the part of the outputs' blinding not cancelled by the inputs'.
    fee : int
        The fee, signed as the kernel's message.
    nonce_commitment, response : int
        A Schnorr signature ``(h**u, u + e*k)`` proving knowledge of ``k``.
    """

    excess: int
    fee: int
    nonce_commitment: int
    response: int


@dataclass(frozen=True)
class MimblewimbleTransaction:
    """A Mimblewimble transaction, or several merged into one.

    Attributes
    ----------
    inputs, outputs : tuple of int
        Pedersen commitments ``g**v * h**r``, sorted; no addresses, no amounts.
    kernels : tuple of Kernel
        One per original transaction, sorted.
    offset : int
        Part of the blinding kept out of the kernels, so that merged
        transactions cannot be split back apart.
    minted : int
        New coins created (a block reward); 0 for an ordinary payment.
    """

    inputs: tuple[int, ...]
    outputs: tuple[int, ...]
    kernels: tuple[Kernel, ...]
    offset: int
    minted: int = 0


@dataclass(frozen=True)
class PuzzlePromise:
    """TumbleBit's promise to a payee: an RSA puzzle and a token locked under its solution.

    Attributes
    ----------
    puzzle : int
        ``z = epsilon**e mod N``; only the tumbler can find ``epsilon``.
    sealed : bytes
        The tumbler's payment token, encrypted with a key derived from ``epsilon``.
    """

    puzzle: int
    sealed: bytes


@dataclass(frozen=True)
class TumblerRun:
    """A round of payments through a TumbleBit tumbler, as the tumbler sees it.

    Attributes
    ----------
    promised : tuple of tuple of str and int
        ``(payee, puzzle)`` for each puzzle the tumbler promised to pay.
    solved : tuple of tuple of str and int
        ``(payer, puzzle)`` for each puzzle a payer paid the tumbler to solve.
    paid : tuple of bool
        Whether each payee recovered its token.
    """

    promised: tuple[tuple[str, int], ...]
    solved: tuple[tuple[str, int], ...]
    paid: tuple[bool, ...]


@dataclass(frozen=True)
class RingInput:
    """A Monero-style input: a ring of earlier outputs, one of them really spent.

    Attributes
    ----------
    members : tuple of int
        Indices of the outputs in the ring, sorted (index order is age order).
    real : int
        The output really spent; the ledger does not reveal it.
    height : int
        Number of outputs created before this input was made.
    """

    members: tuple[int, ...]
    real: int
    height: int


@dataclass(frozen=True)
class TraceReport:
    """How many ring inputs analysis can trace (Möser et al., 2018).

    Attributes
    ----------
    rings : int
        Inputs analysed.
    zero_mixin : int
        Inputs whose ring holds only the real output.
    deduced : int
        Inputs whose real output the chain reaction pins down.
    newest_correct : int
        Inputs whose real output is the newest ring member.
    """

    rings: int
    zero_mixin: int
    deduced: int
    newest_correct: int


@dataclass(frozen=True)
class MixerReport:
    """What a public observer learns from a fixed-denomination mixer's deposits and withdrawals.

    Attributes
    ----------
    anonymity_sets : tuple of int
        For each withdrawal, the deposits it could have come from: those made
        before it, less the withdrawals already made.
    address_links : tuple of tuple of int
        ``(deposit, withdrawal)`` index pairs where the depositor's address
        receives the withdrawal.
    """

    anonymity_sets: tuple[int, ...]
    address_links: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Withdrawal:
    """A request to withdraw one deposit from a mixer, with its zero-knowledge proof.

    Attributes
    ----------
    root : int
        A Merkle root of deposits that the mixer has had.
    nullifier : int
        Marks the deposit spent without saying which one it is.
    recipient : str
        Who is paid; the proof is bound to it.
    proof : Groth16Proof
        Proof of knowing a deposit under ``root`` with this nullifier.
    """

    root: int
    nullifier: int
    recipient: str
    proof: Groth16Proof
