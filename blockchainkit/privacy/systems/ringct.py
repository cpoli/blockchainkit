r"""Ring Confidential Transactions: hiding the input and the amounts at once (Noether, 2016).

Monero hid which output a transaction spends with linkable ring signatures,
but amounts stayed public, and a ring could only mix outputs of the same
denomination. RingCT puts every amount in a Pedersen commitment, as
confidential transactions do, and must then prove the amounts balance
without saying which ring member is the input.

It does so with a second column in an MLSAG signature. Each ring member
:math:`i` is a pair (one-time key :math:`P_i`, amount commitment
:math:`C_i`), and the second column's key is

.. math::

   Z_i = \frac{C_i}{g^{\text{fee}} \\prod_j C^{\text{out}}_j} ,

which, for the real input whose amount equals the outputs plus the fee, is
:math:`h^{z}` with :math:`z` the difference of blinding factors. Signing
both columns with one ring of challenges proves the signer knows the key
of some :math:`P_i` *and* the :math:`z` of the same :math:`Z_i`, so that
member's amount balances. The key image of :math:`P_i` stops double spends.

This model has one input per transaction; Monero gives each input a
*pseudo-output* commitment so several inputs balance together, and since
2019 it uses CLSAG and Bulletproofs in place of MLSAG and digit-wise
range proofs.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.commitments import pedersen_generators
from blockchainkit.privacy.core.base import ConfidentialOutput, RingCTTransaction
from blockchainkit.privacy.systems.confidential import (
    DEFAULT_BITS,
    confidential_output,
    verify_range,
)
from blockchainkit.privacy.systems.linkable import mlsag_sign, mlsag_verify
from blockchainkit.structures.utils.encoding import canonical_json


def _columns(
    ring: Sequence[tuple[int, int]], outputs: Sequence[int], fee: int, group: DHGroup
) -> list[list[int]]:
    p = group.p
    total = pow(group.g, fee, p)
    for c in outputs:
        total = total * c % p
    inverse = pow(total, -1, p)
    return [[key, commitment * inverse % p] for key, commitment in ring]


def _message(ring: Sequence[tuple[int, int]], outputs: Sequence[int], fee: int) -> bytes:
    return canonical_json([[list(member) for member in ring], list(outputs), fee])


def ringct_spend(
    ring: Sequence[tuple[int, int]],
    index: int,
    secret: int,
    amount: int,
    blinding: int,
    outputs: Sequence[tuple[int, int]],
    fee: int,
    *,
    bits: int = DEFAULT_BITS,
    seed: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> RingCTTransaction:
    """Spend ring member ``index``, which holds ``amount`` under ``blinding``, into ``outputs``.

    Parameters
    ----------
    ring : sequence of tuple of int
        ``(one-time key, amount commitment)`` of each possible input.
    index : int
        The real input.
    secret : int
        The real input's one-time private key.
    amount, blinding : int
        The real input's amount and the blinding factor of its commitment.
    outputs : sequence of tuple of int
        ``(amount, blinding)`` of each new output.
    fee : int
        The public fee.
    bits : int
        Size of the outputs' range proofs.
    seed : int
        Seeds the signature and the range proofs.
    group : DHGroup
        The group of keys and commitments.

    Raises
    ------
    ValueError
        The amounts do not balance, the blinding factors cancel exactly (no
        key for the second column), or the secrets do not match the ring.
    """
    integer(fee, "fee")
    check_seed(seed)
    if amount != sum(v for v, _ in outputs) + fee:
        raise ValueError("the input amount must equal the outputs plus the fee")
    rng = Random(seed)
    made: list[ConfidentialOutput] = [
        confidential_output(v, r, bits, seed=rng.randrange(2**32), group=group) for v, r in outputs
    ]
    commitments = [o.commitment for o in made]
    z = (blinding - sum(r for _, r in outputs)) % group.q
    if z == 0:
        raise ValueError("the output blinding factors must not cancel the input's exactly")
    _, h = pedersen_generators(group)
    signature = mlsag_sign(
        _message(ring, commitments, fee),
        _columns(ring, commitments, fee, group),
        index,
        [secret, z],
        seed=rng.randrange(2**32),
        bases=[group.g, h],
        group=group,
    )
    return RingCTTransaction(tuple((k, c) for k, c in ring), tuple(made), fee, signature)


def verify_ringct(transaction: RingCTTransaction, group: DHGroup = TEACHING_GROUP) -> bool:
    """Check the ring signature, which also proves the amounts balance, and every range proof."""
    commitments = [o.commitment for o in transaction.outputs]
    if not all(verify_range(o.commitment, o.range_proof, group) for o in transaction.outputs):
        return False
    _, h = pedersen_generators(group)
    try:
        columns = _columns(transaction.ring, commitments, transaction.fee, group)
        return mlsag_verify(
            _message(transaction.ring, commitments, transaction.fee),
            columns,
            transaction.signature,
            bases=[group.g, h],
            group=group,
        )
    except ValueError:
        return False
