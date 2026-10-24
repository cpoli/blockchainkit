r"""Mimblewimble: no addresses, no amounts, and a chain that forgets spent outputs (2016).

An anonymous author, "Tom Elvis Jedusor", noticed that in a confidential
transaction the blinding factors can serve as the keys. An output is just
a commitment :math:`C = g^{v} h^{r}`, owned by whoever knows :math:`r`.
If a transaction balances, the outputs divided by the inputs (and
:math:`g^{\text{fee}}`) leave :math:`h^{k}` with :math:`k` the change in
blinding. The parties prove they know :math:`k` by a Schnorr signature
with the *excess* :math:`E = h^{k}` as public key, recorded in a *kernel*.
Nothing else is needed: no addresses, no scripts, no amounts.

Because only the sums matter, transactions merge non-interactively into
one, and an output created and spent in the merged set cancels with its
input. This *cut-through* lets a node discard every spent output yet still
check that

.. math::

   \frac{\\prod \text{outputs}}{\\prod \text{inputs}} \\, g^{\text{fees} - \text{minted}}
   = \\Big(\\prod_k E_k\\Big) h^{\text{offset}} .

Each transaction moves a random *offset* out of its kernel, as Grin does,
so that merged transactions cannot be split back apart by matching kernels
to subsets of inputs and outputs. Real Mimblewimble chains also attach a
range proof to every output; see
:mod:`~blockchainkit.privacy.systems.confidential`.
"""

from collections import Counter
from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.constants import KERNEL_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.crypto.systems.commitments import pedersen_commit, pedersen_generators
from blockchainkit.privacy.core.base import Kernel, MimblewimbleTransaction
from blockchainkit.privacy.utils.groups import hash_to_scalar


def _kernel_challenge(excess: int, nonce_commitment: int, fee: int, group: DHGroup) -> int:
    return hash_to_scalar(KERNEL_DOMAIN, excess, nonce_commitment, fee, group=group)


def mimblewimble_transaction(
    inputs: Sequence[tuple[int, int]],
    outputs: Sequence[tuple[int, int]],
    fee: int = 0,
    *,
    minted: int = 0,
    seed: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> MimblewimbleTransaction:
    """Build a transaction spending ``(value, blinding)`` inputs into outputs.

    Raises
    ------
    ValueError
        The values do not balance: inputs plus ``minted`` must equal outputs
        plus ``fee``.

    Examples
    --------
    >>> from blockchainkit.privacy import mimblewimble_transaction, verify_mimblewimble
    >>> coinbase = mimblewimble_transaction([], [(50, 11)], minted=50)
    >>> payment = mimblewimble_transaction([(50, 11)], [(30, 22), (19, 33)], fee=1, seed=1)
    >>> verify_mimblewimble(coinbase), verify_mimblewimble(payment)
    (True, True)
    """
    integer(fee, "fee")
    integer(minted, "minted")
    check_seed(seed)
    if sum(v for v, _ in inputs) + minted != sum(v for v, _ in outputs) + fee:
        raise ValueError("inputs plus minted coins must equal outputs plus the fee")
    q = group.q
    rng = Random(seed)
    _, h = pedersen_generators(group)
    offset = rng.randrange(q)
    key = (sum(r for _, r in outputs) - sum(r for _, r in inputs) - offset) % q
    nonce = rng.randrange(1, q)
    excess = pow(h, key, group.p)
    announce = pow(h, nonce, group.p)
    response = (nonce + _kernel_challenge(excess, announce, fee, group) * key) % q
    return MimblewimbleTransaction(
        tuple(sorted(pedersen_commit(v, r % q, group) for v, r in inputs)),
        tuple(sorted(pedersen_commit(v, r % q, group) for v, r in outputs)),
        (Kernel(excess, fee, announce, response),),
        offset,
        minted,
    )


def verify_kernel(kernel: Kernel, group: DHGroup = TEACHING_GROUP) -> bool:
    """Check the kernel's Schnorr signature: ``h**s == R * E**e``."""
    _, h = pedersen_generators(group)
    p = group.p
    e = _kernel_challenge(kernel.excess, kernel.nonce_commitment, kernel.fee, group)
    return pow(h, kernel.response, p) == kernel.nonce_commitment * pow(kernel.excess, e, p) % p


def verify_mimblewimble(
    transaction: MimblewimbleTransaction, group: DHGroup = TEACHING_GROUP
) -> bool:
    """Check every kernel signature and that the commitments sum to the kernels' excesses."""
    if not all(verify_kernel(kernel, group) for kernel in transaction.kernels):
        return False
    _, h = pedersen_generators(group)
    p = group.p
    fees = sum(kernel.fee for kernel in transaction.kernels)
    left = pow(group.g, fees - transaction.minted, p)
    for c in transaction.outputs:
        left = left * c % p
    for c in transaction.inputs:
        left = left * pow(c, -1, p) % p
    right = pow(h, transaction.offset, p)
    for kernel in transaction.kernels:
        right = right * kernel.excess % p
    return left == right


def aggregate(
    transactions: Sequence[MimblewimbleTransaction], group: DHGroup = TEACHING_GROUP
) -> MimblewimbleTransaction:
    """Merge transactions into one: sorted inputs, outputs and kernels, offsets added."""
    if not transactions:
        raise ValueError("nothing to aggregate")
    return MimblewimbleTransaction(
        tuple(sorted(c for t in transactions for c in t.inputs)),
        tuple(sorted(c for t in transactions for c in t.outputs)),
        tuple(
            sorted(
                (k for t in transactions for k in t.kernels),
                key=lambda k: (k.excess, k.nonce_commitment),
            )
        ),
        sum(t.offset for t in transactions) % group.q,
        sum(t.minted for t in transactions),
    )


def cut_through(transaction: MimblewimbleTransaction) -> MimblewimbleTransaction:
    """Remove every output that is also an input: it was created and spent in the same set."""
    common = Counter(transaction.inputs) & Counter(transaction.outputs)
    inputs = Counter(transaction.inputs) - common
    outputs = Counter(transaction.outputs) - common
    return MimblewimbleTransaction(
        tuple(sorted(inputs.elements())),
        tuple(sorted(outputs.elements())),
        transaction.kernels,
        transaction.offset,
        transaction.minted,
    )
