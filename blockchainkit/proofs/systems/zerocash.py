"""Zerocash: private payments from notes, nullifiers and a SNARK (2014).

Ben-Sasson, Chiesa, Garman, Green, Miers, Tromer and Virza hid the sender,
receiver and amount of every payment. Coins are *notes* ``(owner, value,
rho, r)``, and the ledger stores only their hiding commitments, in a Merkle
tree. To spend a note, its owner publishes

- its *nullifier* ``PRF_sk(rho)``, which the ledger records so the note
  cannot be spent twice, yet which nobody can link to the commitment,
- the commitment to a new note for the payee, and
- a zk-SNARK that some commitment in the tree opens to a note owned by the
  spender, with this nullifier and enough value for the new note.

The ledger learns that *some* unspent note paid *someone*, and nothing else.

This model uses Groth16 on the toy pairing, MiMC (Albrecht et al., 2016)
as the arithmetic-friendly hash, and one input and one output per
spend, with a public amount leaving the pool. Zerocash used SHA-256 inside
its circuits, two inputs and two outputs per transaction, and
encryption of the new note for the payee.
"""

from collections.abc import Sequence
from functools import lru_cache

from blockchainkit._validation import integer
from blockchainkit.constants import MIMC_DOMAIN
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.proofs.core.base import (
    Groth16Trapdoor,
    Note,
    ProvingKey,
    SpendTransaction,
    VerifyingKey,
)
from blockchainkit.proofs.systems.circuits import Circuit, Wire
from blockchainkit.proofs.systems.groth16 import groth16_prove, groth16_setup, groth16_verify
from blockchainkit.proofs.utils.polynomials import FIELD_PRIME

MIMC_ROUNDS = 12
"""int: Rounds of MiMC-7 over the BabyBear field: ceil(log_7 p)."""

VALUE_BITS = 16
"""int: Note values are range-checked to this many bits inside the circuit."""


@lru_cache(maxsize=4)
def _constants(prime: int) -> tuple[int, ...]:
    return (0,) + tuple(
        int.from_bytes(sha256(MIMC_DOMAIN + i.to_bytes(4, "big")), "big") % prime
        for i in range(1, MIMC_ROUNDS)
    )


def mimc_hash(left: int, right: int, prime: int = FIELD_PRIME) -> int:
    """Compress two field elements with MiMC-7 in Miyaguchi-Preneel mode.

    Each round computes ``x = (x + key + c_i)**7`` with ``key = left``,
    starting from ``x = right``; the output is ``x + 2 key + right``. Seven
    is the smallest exponent coprime to ``p - 1``, so each round permutes
    the field, and it costs four multiplications in a circuit.

    >>> from blockchainkit.proofs import mimc_hash
    >>> mimc_hash(1, 2) == mimc_hash(1, 2) != mimc_hash(2, 1)
    True
    """
    integer(left, "left")
    integer(right, "right")
    x = right % prime
    for c in _constants(prime):
        x = pow(x + left + c, 7, prime)
    return (x + 2 * left + right) % prime


def mimc_gadget(circuit: Circuit, left: Wire, right: Wire) -> Wire:
    """Constrain a new wire to ``mimc_hash(left, right)``: 4 constraints per round."""
    x = right
    for c in _constants(circuit.prime):
        t = x + left + c
        t2 = circuit.mul(t, t)
        t4 = circuit.mul(t2, t2)
        x = circuit.mul(circuit.mul(t4, t2), t)
    return x + left * 2 + right


def owner_key(secret_key: int) -> int:
    """The public address of a spending key: ``H(sk, 0)``."""
    return mimc_hash(secret_key, 0)


def note_commitment(note: Note) -> int:
    """``H(H(owner, value), H(rho, r))``: hiding thanks to r, binding thanks to the hash."""
    return mimc_hash(mimc_hash(note.owner, note.value), mimc_hash(note.rho, note.randomness))


def nullifier(secret_key: int, rho: int) -> int:
    """``H(sk, rho)``: only the owner can compute it, and it reveals nothing about the note."""
    return mimc_hash(secret_key, rho)


def _merkle_root(leaves: Sequence[int], depth: int) -> int:
    level = list(leaves) + [0] * (2**depth - len(leaves))
    for _ in range(depth):
        level = [mimc_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def spend_circuit(
    depth: int,
    secret_key: int,
    note: Note,
    siblings: Sequence[int],
    index: int,
    new_note: Note,
    public_value: int,
) -> Circuit:
    """Build the spend statement and its witness.

    Public inputs: the Merkle root, the nullifier, the new commitment and
    the amount leaving the pool. The circuit checks that the spender owns
    the note, that its commitment is a leaf on the path to the root, that
    the nullifier is derived from it, that the new commitment is well
    formed, and that ``value = new value + public value`` with the new
    value in ``[0, 2**16)``. Without that range check, a "negative" new value
    ``p - k`` would mint k coins.
    """
    integer(depth, "depth", 1)
    integer(index, "index")
    if len(siblings) != depth or index >= 2**depth:
        raise ValueError("need one sibling per level and an index inside the tree")
    root = _merkle_root_from_path(note_commitment(note), siblings, index)
    c = Circuit()
    root_wire = c.public(root)
    nullifier_wire = c.public(nullifier(secret_key, note.rho))
    new_commitment = c.public(note_commitment(new_note))
    public_wire = c.public(public_value)

    sk = c.private(secret_key)
    value, rho, randomness = c.private(note.value), c.private(note.rho), c.private(note.randomness)
    owner = mimc_gadget(c, sk, c.one * 0)
    current = mimc_gadget(c, mimc_gadget(c, owner, value), mimc_gadget(c, rho, randomness))
    for level, sibling in enumerate(siblings):
        sibling_wire, bit = c.private(sibling), c.private(index >> level & 1)
        c.assert_boolean(bit)
        swap = c.mul(bit, sibling_wire - current)  # Swaps the pair when the bit is 1.
        current = mimc_gadget(c, current + swap, sibling_wire - swap)
    c.assert_equal(current, root_wire)
    c.assert_equal(mimc_gadget(c, sk, rho), nullifier_wire)

    new_owner, new_value = c.private(new_note.owner), c.private(new_note.value)
    new_rho, new_randomness = c.private(new_note.rho), c.private(new_note.randomness)
    formed = mimc_gadget(
        c, mimc_gadget(c, new_owner, new_value), mimc_gadget(c, new_rho, new_randomness)
    )
    c.assert_equal(formed, new_commitment)
    c.assert_equal(value, new_value + public_wire)
    total = c.one * 0
    for k in range(VALUE_BITS):
        bit = c.private(new_note.value % FIELD_PRIME >> k & 1)
        c.assert_boolean(bit)
        total = total + bit * 2**k
    c.assert_equal(total, new_value)
    return c


def _merkle_root_from_path(leaf: int, siblings: Sequence[int], index: int) -> int:
    current = leaf
    for level, sibling in enumerate(siblings):
        if index >> level & 1:
            current = mimc_hash(sibling, current)
        else:
            current = mimc_hash(current, sibling)
    return current


def spend_setup(depth: int, trapdoor: Groth16Trapdoor) -> ProvingKey:
    """Run the Groth16 setup for the spend circuit of a tree of the given depth."""
    dummy = Note(0, 0, 0, 0)
    circuit = spend_circuit(depth, 0, dummy, [0] * depth, 0, dummy, 0)
    return groth16_setup(circuit.r1cs(), trapdoor)


class ShieldedPool:
    """The ledger side of Zerocash: commitments, nullifiers, and proof checks.

    Parameters
    ----------
    depth : int
        The note-commitment tree holds ``2**depth`` notes.
    verifying_key : VerifyingKey
        From :func:`spend_setup` for the same depth.

    Examples
    --------
    >>> from blockchainkit.proofs import (Groth16Trapdoor, Note, ShieldedPool, owner_key,
    ...     prove_spend, spend_setup)
    >>> key = spend_setup(2, Groth16Trapdoor(5, 6, 7, 8, 9))
    >>> pool = ShieldedPool(2, key.verifying_key)
    >>> alice, bob = 1111, 2222
    >>> coin = Note(owner_key(alice), 100, rho=1, randomness=77)
    >>> index = pool.mint(coin)
    >>> payment = Note(owner_key(bob), 60, rho=2, randomness=88)
    >>> spend = prove_spend(key, pool, alice, coin, index, payment, public_value=40)
    >>> pool.spend(spend), pool.supply
    (1, 60)
    """

    def __init__(self, depth: int, verifying_key: VerifyingKey) -> None:
        integer(depth, "depth", 1)
        if not isinstance(verifying_key, VerifyingKey):
            raise TypeError("verifying_key must be a VerifyingKey")
        self.depth = depth
        self.verifying_key = verifying_key
        self._commitments: list[int] = []
        self._nullifiers: set[int] = set()
        self._roots = {self.root}
        self.supply = 0

    @property
    def commitments(self) -> tuple[int, ...]:
        """Every note commitment in order, which is all an observer sees of the notes."""
        return tuple(self._commitments)

    @property
    def nullifiers(self) -> frozenset[int]:
        """The nullifiers of spent notes."""
        return frozenset(self._nullifiers)

    @property
    def root(self) -> int:
        """The current root of the commitment tree."""
        return _merkle_root(self._commitments, self.depth)

    def _append(self, commitment: int) -> int:
        if len(self._commitments) == 2**self.depth:
            raise ValueError("the commitment tree is full")
        self._commitments.append(commitment)
        self._roots.add(self.root)
        return len(self._commitments) - 1

    def mint(self, note: Note) -> int:
        """Deposit public value into a new note; the value is visible, the owner is not."""
        if not isinstance(note, Note):
            raise TypeError("note must be a Note")
        index = self._append(note_commitment(note))
        self.supply += note.value
        return index

    def siblings(self, index: int) -> tuple[int, ...]:
        """The Merkle path of a note: the sibling hash at each level."""
        integer(index, "index")
        if index >= len(self._commitments):
            raise IndexError("no note at this index")
        level = list(self._commitments) + [0] * (2**self.depth - len(self._commitments))
        path = []
        for _ in range(self.depth):
            path.append(level[index ^ 1])
            level = [mimc_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
            index //= 2
        return tuple(path)

    def spend(self, transaction: SpendTransaction) -> int:
        """Check a spend and record it; return the new note's index.

        Raises
        ------
        ValueError
            Unknown root, reused nullifier, amount out of range, or invalid proof.
        """
        t = transaction
        if t.root not in self._roots:
            raise ValueError("unknown Merkle root")
        if t.nullifier in self._nullifiers:
            raise ValueError("double spend: the nullifier was already revealed")
        if type(t.public_value) is not int or not 0 <= t.public_value < 2**VALUE_BITS:
            raise ValueError("the public value is out of range")
        inputs = [t.root, t.nullifier, t.new_commitment, t.public_value]
        if not groth16_verify(self.verifying_key, inputs, t.proof):
            raise ValueError("invalid spend proof")
        self._nullifiers.add(t.nullifier)
        self.supply -= t.public_value
        return self._append(t.new_commitment)


def prove_spend(
    proving_key: ProvingKey,
    pool: ShieldedPool,
    secret_key: int,
    note: Note,
    index: int,
    new_note: Note,
    public_value: int,
    *,
    seed: int = 0,
) -> SpendTransaction:
    """Spend ``note`` (at ``index`` in the pool) into ``new_note`` plus a public amount.

    Raises
    ------
    ValueError
        The statement is false: a key that does not own the note, values
        that do not balance, or a new value outside ``[0, 2**16)``.
    """
    siblings = pool.siblings(index)
    circuit = spend_circuit(pool.depth, secret_key, note, siblings, index, new_note, public_value)
    proof = groth16_prove(proving_key, circuit.witness(), seed=seed)
    root, spent, created, value = circuit.public_inputs()
    return SpendTransaction(root, spent, created, value, proof)
