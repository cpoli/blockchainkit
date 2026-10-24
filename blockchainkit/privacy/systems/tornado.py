"""Tornado Cash: a mixer contract with zero-knowledge withdrawals (2019).

Tornado Cash put Zerocash's notes and nullifiers in an Ethereum contract.
A user deposits a fixed amount, say 1 ether, together with the commitment
to a secret note; the contract appends it to a Merkle tree of deposits.
Later, from a fresh address, anyone holding the note withdraws by
publishing its nullifier and a zk-SNARK proving the note is a leaf under a
recent root. The contract pays out once per nullifier. Because all deposits
are the same size, the withdrawal could be any earlier deposit not yet
withdrawn: that is the anonymity set.

The proof hides the link, but behaviour does not. Users who withdraw to
the address they deposited from, or withdraw right after an unusual
deposit, shrink their anonymity sets to one. In August 2022 the US
Treasury sanctioned the Tornado Cash contracts, after hackers had
laundered stolen funds through them.

This mixer proves with the Zerocash spend circuit of
:mod:`blockchainkit.proofs` (Groth16 over a toy pairing, MiMC hashing).
The circuit's new-note commitment is used to bind the recipient: it must
be the commitment to a zero-valued note "owned" by the recipient's tag, so
a front-runner cannot redirect a withdrawal. Tornado binds the recipient,
a relayer and its fee as separate public inputs of its own circuit.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.privacy.core.base import MixerReport, Withdrawal
from blockchainkit.proofs.core.base import Note, ProvingKey, VerifyingKey
from blockchainkit.proofs.systems.groth16 import groth16_prove, groth16_verify
from blockchainkit.proofs.systems.zerocash import (
    mimc_hash,
    note_commitment,
    nullifier,
    spend_circuit,
)
from blockchainkit.proofs.utils.polynomials import FIELD_PRIME


def _recipient_note(recipient: str) -> Note:
    return Note(int.from_bytes(sha256(recipient.encode()), "big") % FIELD_PRIME, 0, 0, 0)


def recipient_commitment(recipient: str) -> int:
    """The commitment a withdrawal to ``recipient`` must create: a zero note owned by its tag."""
    return note_commitment(_recipient_note(recipient))


def _levels(leaves: Sequence[int], depth: int) -> list[list[int]]:
    level = list(leaves) + [0] * (2**depth - len(leaves))
    levels = [level]
    for _ in range(depth):
        level = [mimc_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        levels.append(level)
    return levels


def deposit_root(leaves: Sequence[int], depth: int) -> int:
    """The MiMC Merkle root of the deposit tree, padded with zeros."""
    integer(depth, "depth", 1)
    if len(leaves) > 2**depth:
        raise ValueError("more leaves than the tree holds")
    return _levels(leaves, depth)[-1][0]


class Mixer(Contract):
    """A fixed-denomination mixer: deposit with a commitment, withdraw with a proof.

    Constructor arguments: ``denomination``, the tree ``depth``, and the
    Groth16 ``verifying_key`` of the spend circuit for that depth.
    """

    layout = ("denomination", "depth", "verifying_key", "count", "leaves", "roots", "nullifiers")

    def constructor(self, denomination: int, depth: int, verifying_key: VerifyingKey) -> None:
        integer(denomination, "denomination", 1)
        integer(depth, "depth", 1)
        self.write("denomination", denomination)
        self.write("depth", depth)
        self.write("verifying_key", verifying_key)

    def deposits(self) -> tuple[int, ...]:
        """Every deposit commitment, in order."""
        return tuple(self.read("leaves", i) for i in range(self.read("count")))

    def deposit(self, commitment: int) -> int:
        """Add a note commitment, paying exactly the denomination; return its index."""
        self.require(self.value == self.read("denomination"), "send exactly the denomination")
        index = self.read("count")
        depth = self.read("depth")
        self.require(index < 2**depth, "the mixer is full")
        self.write("leaves", index, commitment)
        self.write("count", index + 1)
        self.write("roots", deposit_root([*self.deposits()], depth), True)
        self.emit("Deposit", commitment=commitment, index=index)
        return int(index)

    def withdraw(self, withdrawal: Withdrawal) -> None:
        """Pay the denomination to the recipient if the proof is valid and the nullifier new."""
        w = withdrawal
        self.require(self.read("roots", w.root), "unknown root")
        self.require(not self.read("nullifiers", w.nullifier), "the note was already withdrawn")
        public = [w.root, w.nullifier, recipient_commitment(w.recipient), self.read("denomination")]
        self.require(groth16_verify(self.read("verifying_key"), public, w.proof), "invalid proof")
        self.write("nullifiers", w.nullifier, True)
        self.require(self.send(w.recipient, self.read("denomination")), "payment failed")
        self.emit("Withdrawal", recipient=w.recipient, nullifier=w.nullifier)


def prove_withdrawal(
    proving_key: ProvingKey,
    deposits: Sequence[int],
    depth: int,
    secret_key: int,
    note: Note,
    recipient: str,
    *,
    seed: int = 0,
) -> Withdrawal:
    """Prove that ``note``, owned by ``secret_key``, is among ``deposits``, paying ``recipient``.

    Raises
    ------
    ValueError
        The note's commitment is not among the deposits.
    """
    commitment = note_commitment(note)
    if commitment not in deposits:
        raise ValueError("the note was never deposited")
    index = list(deposits).index(commitment)
    levels = _levels(deposits, depth)
    siblings = [levels[k][(index >> k) ^ 1] for k in range(depth)]
    circuit = spend_circuit(
        depth, secret_key, note, siblings, index, _recipient_note(recipient), note.value
    )
    proof = groth16_prove(proving_key, circuit.witness(), seed=seed)
    return Withdrawal(levels[-1][0], nullifier(secret_key, note.rho), recipient, proof)


def mixer_report(
    deposits: Sequence[tuple[str, int]], withdrawals: Sequence[tuple[str, int]]
) -> MixerReport:
    """Anonymity sets and address links from ``(address, block)`` deposits and withdrawals.

    A withdrawal's anonymity set counts the deposits in earlier blocks, less
    the withdrawals in earlier blocks. An address link pairs a deposit with
    a withdrawal paid to the same address.

    >>> from blockchainkit.privacy import mixer_report
    >>> report = mixer_report([("a", 1), ("b", 2), ("c", 3)], [("x", 4), ("b", 5)])
    >>> report.anonymity_sets, report.address_links
    ((3, 2), ((1, 1),))
    """
    sets = []
    for _, block in withdrawals:
        before = sum(1 for _, b in deposits if b < block)
        out = sum(1 for _, b in withdrawals if b < block)
        sets.append(before - out)
    links = tuple(
        (i, j)
        for i, (depositor, _) in enumerate(deposits)
        for j, (recipient, _) in enumerate(withdrawals)
        if depositor == recipient
    )
    return MixerReport(tuple(sets), links)
