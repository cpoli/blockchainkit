"""Approval phishing ("ice phishing") on ERC-20 allowances (2022).

An ERC-20 ``approve`` lets a spender move the owner's tokens later, without
asking again. Decentralized exchanges ask for an unlimited allowance once,
to save their users a transaction per trade, so users learned to grant
them without reading. An ice-phishing site, named by Microsoft in February
2022, asks for the same signature on behalf of an attacker's contract, and
the attacker empties the wallet whenever it likes, even months later.
Nothing about the victim's keys is stolen; the allowance is the key.

:func:`open_approvals` reads a wallet's standing allowances from its
``Approval`` events, and :func:`allowance_exposure` measures what each
spender could take now. Revoking means approving 0.
"""

from collections.abc import Iterable

from blockchainkit.contracts.core.base import Receipt
from blockchainkit.contracts.systems.world import Contract, World

UNLIMITED = 2**256 - 1
"""The "infinite" allowance that interfaces ask for, the largest 256-bit integer."""


class Drainer(Contract):
    """An attacker's contract that sweeps tokens its victims approved it to spend."""

    layout = ("attacker",)

    def constructor(self) -> None:
        self.write("attacker", self.sender)

    def sweep(self, token: str, victim: str) -> int:
        """Move as much of ``victim``'s ``token`` as the allowance allows to the attacker."""
        attacker = self.read("attacker")
        self.require(self.sender == attacker, "only the attacker")
        allowed = self.call(token, "allowance", victim, self.address)
        amount = min(allowed, self.call(token, "balance_of", victim))
        if amount:
            self.call(token, "transfer_from", victim, attacker, amount)
        return int(amount)


def open_approvals(receipts: Iterable[Receipt], owner: str) -> dict[tuple[str, str], int]:
    """The latest allowance ``owner`` set for each ``(token, spender)``, from its Approval events.

    Allowances set to 0, that is revoked, are left out.
    """
    latest: dict[tuple[str, str], int] = {}
    for receipt in receipts:
        for event in receipt.events:
            if event.name == "Approval" and event.fields.get("owner") == owner:
                latest[(event.emitter, event.fields["spender"])] = event.fields["amount"]
    return {key: amount for key, amount in latest.items() if amount}


def allowance_exposure(world: World, owner: str, approvals: Iterable[tuple[str, str]]) -> int:
    """Tokens that the spenders of ``approvals``, ``(token, spender)`` pairs, could take now.

    The spenders of one token can together move their allowances, up to
    the owner's balance of it.
    """
    allowed: dict[str, int] = {}
    for token, spender in approvals:
        allowed[token] = allowed.get(token, 0) + world.view(token, "allowance", owner, spender)
    return sum(
        min(total, world.view(token, "balance_of", owner)) for token, total in allowed.items()
    )
