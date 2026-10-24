r"""Confidential transactions: hidden amounts that still add up (Maxwell, 2015).

Each output's amount is replaced by a Pedersen commitment
:math:`C = g^{v} h^{r}`. Commitments multiply as their amounts add, so
anyone can check that a transaction creates no money,

.. math::

   \\prod_{\text{in}} C_i = g^{\text{fee}} \\prod_{\text{out}} C_j ,

as long as the sender chooses the blinding factors to cancel. That check
alone is not enough: amounts are numbers modulo the group order :math:`q`,
so an output of :math:`q - 1`, that is :math:`-1`, lets another output
hold one coin more than was paid in. Every output therefore carries a
*range proof* that its amount is small. Maxwell's proof commits to each
digit and proves, with a ring signature over :math:`\\{C_k, C_k / g^{2^k}\\}`,
that one of them is a pure :math:`h^{r_k}`, so the digit is 0 or 1; the
digit commitments multiply back to :math:`C`.

Elements and Liquid use base-4 digits joined into one Borromean ring
signature; here every bit has its own two-member ring signature. Bulletproofs
(see :mod:`blockchainkit.proofs`) later made the proof logarithmic.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.commitments import pedersen_commit, pedersen_generators
from blockchainkit.privacy.core.base import ConfidentialOutput, RingRangeProof
from blockchainkit.privacy.systems.ring_signatures import ring_sign, ring_verify

DEFAULT_BITS = 16
"""int: Bits of a range proof, so amounts lie in ``[0, 2**16)``."""


def _bit_message(commitment: int, k: int) -> bytes:
    return f"range:{commitment}:{k}".encode()


def _pair(bit_commitment: int, k: int, group: DHGroup) -> list[int]:
    return [bit_commitment, bit_commitment * pow(group.g, -(2**k), group.p) % group.p]


def prove_range(
    value: int,
    blinding: int,
    bits: int = DEFAULT_BITS,
    *,
    seed: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> RingRangeProof:
    """Prove that ``pedersen_commit(value, blinding)`` holds a value in ``[0, 2**bits)``.

    Raises
    ------
    ValueError
        ``value`` is out of range, so no proof exists.

    Examples
    --------
    >>> from blockchainkit.privacy import prove_range, verify_range
    >>> from blockchainkit.crypto import pedersen_commit
    >>> verify_range(pedersen_commit(1000, 99), prove_range(1000, 99))
    True
    """
    integer(bits, "bits", 1)
    integer(blinding, "blinding")
    check_seed(seed)
    if not 0 <= value < 2**bits:
        raise ValueError(f"value is not in [0, 2**{bits})")
    _, h = pedersen_generators(group)
    q = group.q
    rng = Random(seed)
    blindings = [rng.randrange(1, q) for _ in range(bits - 1)]
    last = (blinding - sum(blindings)) % q
    while last == 0:  # A zero blinding has no ring key; probability 1/q.
        blindings[0] = rng.randrange(1, q)
        last = (blinding - sum(blindings)) % q
    blindings.append(last)
    commitments = []
    signatures = []
    commitment = pedersen_commit(value, blinding % q, group)
    for k, r in enumerate(blindings):
        bit = value >> k & 1
        c = pedersen_commit(bit << k, r, group)
        commitments.append(c)
        signatures.append(
            ring_sign(
                _bit_message(commitment, k),
                _pair(c, k, group),
                bit,
                r,
                seed=rng.randrange(2**32),
                base=h,
                group=group,
            )
        )
    return RingRangeProof(tuple(commitments), tuple(signatures))


def verify_range(commitment: int, proof: RingRangeProof, group: DHGroup = TEACHING_GROUP) -> bool:
    """Check that ``proof`` shows ``commitment`` to hold a value in ``[0, 2**proof.bits)``."""
    if not proof.bits or len(proof.signatures) != proof.bits:
        return False
    _, h = pedersen_generators(group)
    product = 1
    for k, (c, signature) in enumerate(zip(proof.bit_commitments, proof.signatures, strict=True)):
        try:
            if not ring_verify(
                _bit_message(commitment, k), _pair(c, k, group), signature, base=h, group=group
            ):
                return False
        except (TypeError, ValueError):
            return False
        product = product * c % group.p
    return product == commitment


def confidential_output(
    amount: int,
    blinding: int,
    bits: int = DEFAULT_BITS,
    *,
    seed: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> ConfidentialOutput:
    """An output committing to ``amount``, with its range proof."""
    proof = prove_range(amount, blinding, bits, seed=seed, group=group)
    return ConfidentialOutput(pedersen_commit(amount, blinding % group.q, group), proof)


def commitments_balance(
    inputs: Sequence[int], outputs: Sequence[int], fee: int, group: DHGroup = TEACHING_GROUP
) -> bool:
    """Whether the input commitments equal ``g**fee`` times the output commitments."""
    integer(fee, "fee")
    p = group.p
    left = 1
    for c in inputs:
        left = left * c % p
    right = pow(group.g, fee, p)
    for c in outputs:
        right = right * c % p
    return left == right


def verify_confidential(
    inputs: Sequence[int],
    outputs: Sequence[ConfidentialOutput],
    fee: int,
    group: DHGroup = TEACHING_GROUP,
) -> bool:
    """A confidential transaction is valid if it balances and every output has a range proof."""
    commitments = [output.commitment for output in outputs]
    return commitments_balance(inputs, commitments, fee, group) and all(
        verify_range(o.commitment, o.range_proof, group) for o in outputs
    )
