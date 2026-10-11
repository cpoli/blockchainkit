"""Proofs of reserves and liabilities (Maxwell, 2013).

An exchange can prove its *reserves* by moving or signing with the coins it
holds, but that shows nothing unless its *liabilities*, what it owes its
customers, are proved too. In Maxwell's scheme the exchange publishes the
root of a Merkle sum tree over every customer balance
(:class:`~blockchainkit.fraud.utils.merkle_sum.MerkleSumTree`); each
customer checks that its own balance is counted, and anyone checks that the
reserves cover the root's total.

An exchange that leaves out customers, or lowers their balances, declares
smaller liabilities, but every customer it cheats can catch it. If each
customer checks independently with probability :math:`f`, cheating
:math:`k` of them goes unnoticed with probability :math:`(1 - f)^k`.
"""

from collections.abc import Mapping
from random import Random

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.fraud.core.base import AuditResult
from blockchainkit.fraud.utils.merkle_sum import MerkleSumTree, verify_sum_proof


def liability_tree(balances: Mapping[str, int], *, salt: bytes = b"") -> MerkleSumTree:
    """The Merkle sum tree an honest exchange publishes: every balance, sorted by customer.

    Examples
    --------
    >>> from blockchainkit.fraud import liability_tree
    >>> liability_tree({"bob": 50, "alice": 30}).total
    80
    """
    return MerkleSumTree(sorted(balances.items()), salt=salt)


def detection_probability(cheated: int, checking: float) -> float:
    """Chance that at least one of ``cheated`` customers checks, each with probability ``checking``.

    Examples
    --------
    >>> from blockchainkit.fraud import detection_probability
    >>> round(detection_probability(10, 0.1), 3)
    0.651
    """
    integer(cheated, "cheated")
    probability(checking, "checking")
    return 1 - (1 - checking) ** cheated


def audit(
    published: MerkleSumTree,
    balances: Mapping[str, int],
    *,
    checking: float,
    seed: int = 0,
) -> AuditResult:
    """Let each customer check its inclusion proof with probability ``checking``.

    Parameters
    ----------
    published : MerkleSumTree
        The tree the exchange published, honest or not.
    balances : Mapping
        What each customer is truly owed.
    checking : float
        Probability that a customer asks for and checks its proof.
    seed : int
        Seeds which customers check.

    Returns
    -------
    AuditResult
        A checking customer complains if its leaf is missing or its proof
        fails for its true balance.
    """
    probability(checking, "checking")
    check_seed(seed)
    rng = Random(seed)
    checked, complaints = [], []
    for customer in sorted(balances):
        if rng.random() >= checking:
            continue
        checked.append(customer)
        index = published.index(customer)
        valid = index is not None and verify_sum_proof(
            customer,
            balances[customer],
            published.proof(index),
            published.root,
            published.total,
            salt=published.salt,
        )
        if not valid:
            complaints.append(customer)
    return AuditResult(tuple(checked), tuple(complaints))


def reserve_ratio(reserves: int, liabilities: int) -> float:
    """Reserves per unit of liabilities: below 1, not every customer can be paid.

    Examples
    --------
    >>> from blockchainkit.fraud import reserve_ratio
    >>> reserve_ratio(80, 100)
    0.8
    """
    integer(reserves, "reserves")
    integer(liabilities, "liabilities", 1)
    return reserves / liabilities
