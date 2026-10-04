"""Small contracts written for the stack machine.

* :func:`vending_machine`: Szabo's (1994) example of a contract enforced by
  a mechanism rather than a court: pay at least the price and an item and
  your change come out; otherwise nothing happens.
* :func:`batch_transfer`: the token function behind the 2018 BeautyChain
  (BEC) exploit, where ``count * value`` overflowed 256 bits.

Both are assembled with :func:`~blockchainkit.vm.systems.assembler.assemble`
and run with :func:`~blockchainkit.vm.systems.stack_machine.execute`.
"""

from collections.abc import Sequence

from blockchainkit._validation import integer
from blockchainkit.vm.core.base import Instruction
from blockchainkit.vm.systems.assembler import assemble

STOCK, PRICE, REVENUE = 0, 1, 2
"""Storage slots of the vending machine."""


def vending_machine() -> tuple[Instruction, ...]:
    """A vending machine: argument ``payment``; storage holds stock, price and revenue.

    On success the stock drops by one, the revenue grows by the price, and
    the change ``payment - price`` is left on the stack. Paying too little,
    or buying from an empty machine, reverts, so neither side can be cheated.

    Examples
    --------
    >>> from blockchainkit.vm import execute, vending_machine
    >>> result = execute(vending_machine(), arguments=(5,), storage={0: 3, 1: 2})
    >>> result.stack, dict(result.storage)
    ((3,), {0: 2, 1: 2, 2: 2})
    """
    return assemble(
        f"""
        # stack: payment
            DUP
            LOAD {PRICE}
            LT              # payment < price?
            JZ paid
            REVERT          # too little: nothing happens
        paid:
            LOAD {STOCK}
            JZ sold_out
            LOAD {STOCK}
            PUSH 1
            SUB
            STORE {STOCK}   # hand over one item
            LOAD {REVENUE}
            LOAD {PRICE}
            ADD
            STORE {REVENUE}
            LOAD {PRICE}
            SUB             # change = payment - price
            STOP
        sold_out:
            REVERT
        """
    )


def batch_transfer(
    sender: int, recipients: Sequence[int], *, checked: bool = False
) -> tuple[Instruction, ...]:
    """Pay ``value`` (the one argument) from ``sender`` to each recipient.

    Balances live in storage, one slot per account. Like BeautyChain's
    ``batchTransfer``, the program computes ``amount = count * value``,
    checks the sender's balance against ``amount``, debits ``amount`` once
    and credits ``value`` to every recipient. The multiplication wraps
    modulo ``2**256``: with two recipients and ``value = 2**255``, ``amount``
    is 0, every check passes, and each recipient receives ``2**255`` tokens
    from nothing. ``checked=True`` adds the SafeMath test
    ``amount / count == value``, which rejects the overflow.

    Examples
    --------
    >>> from blockchainkit.vm import batch_transfer, execute
    >>> program = batch_transfer(1, [2, 3])
    >>> dict(execute(program, arguments=(10,), storage={1: 100}).storage)
    {1: 80, 2: 10, 3: 10}
    """
    integer(sender, "sender")
    if not recipients:
        raise ValueError("provide at least one recipient")
    for account in recipients:
        integer(account, "recipient")
    count = len(recipients)
    overflow_check = (
        f"""
            DUP             # value amount amount
            PUSH {count}
            DIV             # value amount amount/count
            ROT             # amount amount/count value
            DUP
            ROT             # amount value value amount/count
            EQ
            JZ overflow     # SafeMath: the product must divide back
            SWAP            # value amount
        """
        if checked
        else ""
    )
    credits = "\n".join(
        f"""
            DUP
            LOAD {account}
            ADD
            STORE {account}"""
        for account in recipients
    )
    return assemble(
        f"""
        # stack: value
            DUP
            JZ zero_value   # require(value > 0)
            DUP
            PUSH {count}
            MUL             # value amount   (wraps modulo 2**256)
            {overflow_check}
            DUP
            LOAD {sender}
            SWAP
            LT              # balance < amount?
            JZ funded
            REVERT          # balance too low
        funded:
            LOAD {sender}
            SWAP
            SUB
            STORE {sender}  # debit amount once
            {credits}
            DROP
            STOP
        zero_value:
            REVERT
        {"overflow:" if checked else ""}
            {"REVERT" if checked else ""}
        """
    )
