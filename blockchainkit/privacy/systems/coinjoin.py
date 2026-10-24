"""CoinJoin: many payers in one transaction, so its inputs need not share an owner (2013).

Gregory Maxwell pointed out on the Bitcoin forum that nothing requires a
transaction's inputs to belong to one person. Several users can each
contribute an input and name an output, check the joint transaction, and
sign only their own input. If every mixed output pays the same
*denomination*, an observer cannot tell whose output is whose: for
:math:`n` such outputs each user hides among :math:`n`, and the common
input ownership heuristic, applied to the transaction, merges strangers.

The change outputs are another matter. Each one is an input amount minus
the denomination, which usually links it to its input, so only the
equal-valued outputs are anonymous.

:func:`coinjoin` builds the transaction without fees or signatures; real
rounds (JoinMarket, Wasabi, Whirlpool) coordinate through a server or a
market and use blinded registrations so the coordinator cannot link
inputs to outputs either.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.privacy.core.base import CoinJoinRound, TransactionRecord
from blockchainkit.privacy.systems.clustering import fresh_address


def coinjoin(
    participants: Sequence[tuple[str, str, int]], denomination: int, *, seed: int = 0
) -> CoinJoinRound:
    """Join each participant's ``(user, input address, amount)`` into one transaction.

    Each gets an output of ``denomination`` at a fresh address and, if its
    input is larger, its change at another; the outputs are shuffled.

    Raises
    ------
    ValueError
        An input is smaller than the denomination, or a user joins twice.

    Examples
    --------
    >>> from blockchainkit.privacy import coinjoin
    >>> round_ = coinjoin([("ann", "a1", 10), ("bob", "b1", 13), ("cat", "c1", 10)], 10)
    >>> round_.anonymity_set, round_.transaction.fee
    (3, 0)
    """
    integer(denomination, "denomination", 1)
    check_seed(seed)
    users = [user for user, _, _ in participants]
    if len(set(users)) != len(users):
        raise ValueError("each user joins once")
    owners: dict[str, str] = {}
    inputs, outputs = [], []
    for user, address, amount in participants:
        integer(amount, "amount", denomination)
        owners[address] = user
        inputs.append((address, amount))
        mixed = fresh_address(f"coinjoin:{seed}:{user}:mixed")
        owners[mixed] = user
        outputs.append((mixed, denomination))
        if amount > denomination:
            change = fresh_address(f"coinjoin:{seed}:{user}:change")
            owners[change] = user
            outputs.append((change, amount - denomination))
    Random(seed).shuffle(outputs)
    return CoinJoinRound(TransactionRecord(tuple(inputs), tuple(outputs)), owners, denomination)


def link_change(transaction: TransactionRecord, denomination: int) -> dict[str, str]:
    """Link each change output to the one input whose amount is the change plus the denomination.

    Outputs of exactly the denomination are left out; so is any change that
    two or more inputs could have produced.
    """
    integer(denomination, "denomination", 1)
    links = {}
    for address, amount in transaction.outputs:
        if amount == denomination:
            continue
        sources = [a for a, value in transaction.inputs if value == amount + denomination]
        if len(sources) == 1:
            links[address] = sources[0]
    return links
