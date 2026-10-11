"""Provisions: proofs of solvency that reveal no balances (Dagher et al., 2015).

A Merkle sum tree reveals the exchange's total liabilities, and its proof of
reserves reveals which addresses it owns. Provisions hides both behind
Pedersen commitments :math:`C(v, r) = g^v h^r`, which multiply into a
commitment to the sum:

- for each address of a public *anonymity set*, the exchange commits to the
  address's balance if it owns it and to 0 otherwise, and proves which one
  without saying;
- for each customer it commits to the balance, proves it is not negative,
  and privately gives the customer the blinding factor to check it;
- dividing the product of the asset commitments by that of the liability
  commitments gives a commitment to assets minus liabilities, which it
  proves is not negative.

Every "is 0 or that value" statement is an OR proof (Cramer, Damgård and
Schoenmakers, 1994) made non-interactive with Fiat-Shamir, and every "is not
negative" a commitment to each bit, each proved to be 0 or 1.
"""

from collections.abc import Collection, Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.constants import SOLVENCY_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.commitments import pedersen_commit, pedersen_generators
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.fraud.core.base import BitRangeProof, SolvencyProof
from blockchainkit.structures.utils.encoding import canonical_json

DEFAULT_BITS = 16
"""Bits of the range proofs, so balances and the surplus must lie in ``[0, 2**16)``."""

OrProof = tuple[int, int, int, int]


def _challenge(group: DHGroup, *values: int) -> int:
    framed = SOLVENCY_DOMAIN + canonical_json([group.p, group.q, group.g, *values])
    return int.from_bytes(sha256(framed), "big") % group.q


def _targets(commitment: int, value: int, group: DHGroup) -> tuple[int, int]:
    """The two statements: ``commitment = h**r`` or ``commitment / g**value = h**r``."""
    g, _ = pedersen_generators(group)
    return commitment, commitment * pow(g, -value, group.p) % group.p


def prove_either(
    commitment: int, value: int, opened: int, blinding: int, rng: Random, group: DHGroup
) -> OrProof:
    """Prove that ``commitment`` holds 0 or ``value``, without saying which.

    ``opened`` is the value it holds and ``blinding`` its blinding factor.
    The branch that is false is simulated by choosing its challenge and
    response first; the challenges must add up to the Fiat-Shamir hash, so
    only one branch can be simulated.
    """
    _, h = pedersen_generators(group)
    p, q = group.p, group.q
    real = 0 if opened == 0 else 1
    targets = _targets(commitment, value, group)
    fake_c, fake_z, nonce = rng.randrange(q), rng.randrange(q), rng.randrange(q)
    announce = [0, 0]
    announce[real] = pow(h, nonce, p)
    announce[1 - real] = pow(h, fake_z, p) * pow(targets[1 - real], -fake_c, p) % p
    total = _challenge(group, commitment, value, *announce)
    real_c = (total - fake_c) % q
    real_z = (nonce + real_c * blinding) % q
    c = (real_c, fake_c) if real == 0 else (fake_c, real_c)
    z = (real_z, fake_z) if real == 0 else (fake_z, real_z)
    return c[0], c[1], z[0], z[1]


def verify_either(commitment: int, value: int, proof: OrProof, group: DHGroup) -> bool:
    """Check a proof from :func:`prove_either` that ``commitment`` holds 0 or ``value``."""
    _, h = pedersen_generators(group)
    p = group.p
    c0, c1, z0, z1 = proof
    announce = [
        pow(h, z, p) * pow(target, -c, p) % p
        for target, c, z in zip(_targets(commitment, value, group), (c0, c1), (z0, z1), strict=True)
    ]
    return (c0 + c1) % group.q == _challenge(group, commitment, value, *announce)


def prove_range(
    value: int, blinding: int, bits: int, rng: Random, group: DHGroup = TEACHING_GROUP
) -> BitRangeProof:
    """Prove that ``pedersen_commit(value, blinding)`` holds a value in ``[0, 2**bits)``.

    Each bit gets its own commitment and an OR proof that it is 0 or 1; the
    bits' blinding factors are chosen so that the commitments, raised to
    1, 2, 4, ..., multiply back to the original one.

    Raises
    ------
    ValueError
        ``value`` is outside the range, so no such proof exists.
    """
    integer(bits, "bits", 1)
    if not 0 <= value < 2**bits:
        raise ValueError(f"value is not in [0, 2**{bits})")
    q = group.q
    blindings = [rng.randrange(q) for _ in range(bits - 1)]
    rest = (blinding - sum(r << k for k, r in enumerate(blindings))) % q
    blindings.append(rest * pow(2, -(bits - 1), q) % q)
    commitments, proofs = [], []
    for k, r in enumerate(blindings):
        bit = value >> k & 1
        commitment = pedersen_commit(bit, r, group)
        commitments.append(commitment)
        proofs.append(prove_either(commitment, 1, bit, r, rng, group))
    return BitRangeProof(tuple(commitments), tuple(proofs))


def verify_range(commitment: int, proof: BitRangeProof, group: DHGroup = TEACHING_GROUP) -> bool:
    """Check that ``proof`` shows ``commitment`` to hold a value in ``[0, 2**proof.bits)``."""
    if len(proof.bit_proofs) != proof.bits:
        return False
    combined = 1
    for k, (bit, either) in enumerate(zip(proof.bit_commitments, proof.bit_proofs, strict=True)):
        if not verify_either(bit, 1, either, group):
            return False
        combined = combined * pow(bit, 2**k, group.p) % group.p
    return combined == commitment


class SolvencyProver:
    """An exchange preparing a Provisions-style proof of solvency.

    Parameters
    ----------
    asset_balances : sequence of int
        The public balance of every address in the anonymity set.
    owned : collection of int
        Indices of the addresses the exchange owns.
    liabilities : sequence of int
        What the exchange owes each customer.
    bits : int
        Size of the range proofs.
    seed : int
        Seeds the blinding factors and proof nonces.
    group : DHGroup
        The group of the commitments.

    Examples
    --------
    >>> from blockchainkit.fraud import SolvencyProver, verify_solvency
    >>> prover = SolvencyProver([50, 70, 20], owned={0, 2}, liabilities=[30, 25])
    >>> verify_solvency([50, 70, 20], prover.prove())
    True
    """

    def __init__(
        self,
        asset_balances: Sequence[int],
        owned: Collection[int],
        liabilities: Sequence[int],
        *,
        bits: int = DEFAULT_BITS,
        seed: int = 0,
        group: DHGroup = TEACHING_GROUP,
    ) -> None:
        integer(bits, "bits", 1)
        check_seed(seed)
        for amount in (*asset_balances, *liabilities):
            integer(amount, "balance")
        if any(type(i) is not int or not 0 <= i < len(asset_balances) for i in owned):
            raise ValueError("owned must hold indices of asset_balances")
        self._balances = tuple(asset_balances)
        self._owned = frozenset(owned)
        self._liabilities = tuple(liabilities)
        self._bits = bits
        self._rng = Random(seed)
        self._group = group
        q = group.q
        self._asset_blindings = tuple(self._rng.randrange(q) for _ in self._balances)
        self._liability_blindings = tuple(self._rng.randrange(q) for _ in self._liabilities)

    @property
    def assets(self) -> int:
        """Total balance of the owned addresses."""
        return sum(self._balances[i] for i in self._owned)

    @property
    def surplus(self) -> int:
        """Assets minus liabilities."""
        return self.assets - sum(self._liabilities)

    def blinding(self, customer: int) -> int:
        """The blinding factor given privately to ``customer`` to check its commitment."""
        return self._liability_blindings[customer]

    def prove(self) -> SolvencyProof:
        """Commit to every asset and liability and prove solvency.

        Raises
        ------
        ValueError
            The exchange is insolvent, or a balance is too large for the
            range proofs.
        """
        group, rng = self._group, self._rng
        held = [b if i in self._owned else 0 for i, b in enumerate(self._balances)]
        assets = tuple(
            pedersen_commit(v, r, group) for v, r in zip(held, self._asset_blindings, strict=True)
        )
        asset_proofs = tuple(
            prove_either(c, b, v, r, rng, group)
            for c, b, v, r in zip(assets, self._balances, held, self._asset_blindings, strict=True)
        )
        liabilities = tuple(
            pedersen_commit(v, r, group)
            for v, r in zip(self._liabilities, self._liability_blindings, strict=True)
        )
        liability_proofs = tuple(
            prove_range(v, r, self._bits, rng, group)
            for v, r in zip(self._liabilities, self._liability_blindings, strict=True)
        )
        if self.surplus < 0:
            raise ValueError("insolvent: no proof of a non-negative surplus exists")
        blinding = (sum(self._asset_blindings) - sum(self._liability_blindings)) % group.q
        surplus = prove_range(self.surplus, blinding, self._bits, rng, group)
        return SolvencyProof(assets, asset_proofs, liabilities, liability_proofs, surplus)


def verify_liability(
    commitment: int, balance: int, blinding: int, group: DHGroup = TEACHING_GROUP
) -> bool:
    """A customer's check that ``commitment`` holds its ``balance``."""
    return pedersen_commit(balance, blinding, group) == commitment


def verify_solvency(
    asset_balances: Sequence[int], proof: SolvencyProof, group: DHGroup = TEACHING_GROUP
) -> bool:
    """Check a proof of solvency against the anonymity set's public balances.

    Every asset commitment must hold 0 or its address's balance, every
    liability must be non-negative, and so must the surplus they imply.
    """
    if len(proof.asset_commitments) != len(asset_balances):
        return False
    if len(proof.asset_proofs) != len(asset_balances):
        return False
    if len(proof.liability_proofs) != len(proof.liability_commitments):
        return False
    p = group.p
    combined = 1
    for commitment, balance, either in zip(
        proof.asset_commitments, asset_balances, proof.asset_proofs, strict=True
    ):
        if not verify_either(commitment, balance, either, group):
            return False
        combined = combined * commitment % p
    for commitment, ranged in zip(proof.liability_commitments, proof.liability_proofs, strict=True):
        if not verify_range(commitment, ranged, group):
            return False
        combined = combined * pow(commitment, -1, p) % p
    return verify_range(combined, proof.surplus_proof, group)
