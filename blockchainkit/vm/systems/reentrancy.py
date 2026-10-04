"""Reentrancy: the DAO attack (2016).

The DAO's withdrawal code sent ether *before* zeroing the caller's balance.
Sending ether to a contract runs that contract's code, so the attacker's
contract called ``withdraw`` again from inside the payment, while its
balance still showed the full deposit, and again, until the funds ran out
or the call stack's depth limit stopped it. About 3.6 million ether were
drained in June 2016.

The fix is the *checks-effects-interactions* order: check the conditions,
update the contract's own state, and only then call out. A re-entrant call
then finds a zero balance and gets nothing.

This module models the two orders directly in Python: the bank's state is
two numbers, and "sending" calls the attacker's fallback.
"""

from blockchainkit._validation import integer
from blockchainkit.vm.core.base import ReentrancyResult


def drain_bank(
    other_deposits: int,
    attacker_deposit: int,
    *,
    checks_effects_interactions: bool = False,
    max_depth: int = 1024,
) -> ReentrancyResult:
    """Let an attacker that re-enters on every payment withdraw from a bank.

    Parameters
    ----------
    other_deposits : int
        Funds belonging to everyone else.
    attacker_deposit : int
        The attacker's own deposit, at least 1.
    checks_effects_interactions : bool
        False: the vulnerable order (pay, then zero the balance). True: zero
        the balance before paying.
    max_depth : int
        Maximum call depth (1024 in Ethereum then), bounding the recursion.

    Examples
    --------
    >>> from blockchainkit.vm import drain_bank
    >>> drain_bank(90, 10).stolen, drain_bank(90, 10, checks_effects_interactions=True).stolen
    (90, 0)
    """
    integer(other_deposits, "other_deposits")
    integer(attacker_deposit, "attacker_deposit", 1)
    integer(max_depth, "max_depth", 1)
    bank = other_deposits + attacker_deposit
    balance = attacker_deposit
    withdrawn = calls = 0
    # Each pass is one nested call of withdraw, made from inside the
    # previous call's payment. (A loop rather than recursion, because the
    # 1024-call depth exceeds Python's own recursion limit.)
    for _ in range(max_depth):
        calls += 1
        amount = balance  # Checks: the caller's recorded balance.
        if amount == 0 or bank < amount:
            break
        if checks_effects_interactions:
            balance = 0  # Effects before the interaction.
        bank -= amount
        withdrawn += amount
        # Interaction: the payment runs the attacker's fallback, which calls
        # withdraw again (the next pass) unless the depth limit ends the loop.
        # In the vulnerable order the balance is zeroed only as the calls unwind.
    return ReentrancyResult(withdrawn, attacker_deposit, calls, bank)
