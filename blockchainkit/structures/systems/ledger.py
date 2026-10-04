"""Immutable account balances and nonces, updated atomically by signed transfers."""

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.constants import DEFAULT_CHAIN_ID
from blockchainkit.structures.systems.transaction import Transaction


class Ledger:
    """An immutable view of account balances and next expected nonces.

    Initial balances are a shared simulation configuration, not a minting
    transaction. All peers must start with the same allocation and chain ID.
    Applying a batch returns a new state; failures leave the old state intact.
    """

    def __init__(
        self,
        balances: Mapping[str, int] | None = None,
        nonces: Mapping[str, int] | None = None,
        *,
        chain_id: str = DEFAULT_CHAIN_ID,
    ) -> None:
        if not isinstance(chain_id, str) or not 1 <= len(chain_id) <= 128:
            raise ValueError("chain_id must contain 1 to 128 characters")
        for mapping in (balances or {}, nonces or {}):
            for account, value in mapping.items():
                if not isinstance(account, str) or len(account) != 64:
                    raise ValueError("account IDs must be 64 hex characters")
                if any(c not in "0123456789abcdef" for c in account):
                    raise ValueError("account IDs must be lowercase hex")
                integer(value, "account value")
        self._balances = MappingProxyType(dict(balances or {}))
        self._nonces = MappingProxyType(dict(nonces or {}))
        self._chain_id = chain_id

    @property
    def balances(self) -> Mapping[str, int]:
        """Read-only account balances in integer units."""
        return self._balances

    @property
    def nonces(self) -> Mapping[str, int]:
        """Read-only next expected sequence numbers (missing accounts start at 0)."""
        return self._nonces

    @property
    def chain_id(self) -> str:
        """Return the signature domain accepted by this ledger."""
        return self._chain_id

    def apply(self, transactions: Iterable[Transaction]) -> "Ledger":
        """Validate and atomically apply transfers in order, returning a new ledger.

        Rejects invalid signatures, wrong chain IDs, replayed/out-of-order
        nonces, and insufficient funds. Self-transfers still consume a nonce.
        """
        balances, nonces = dict(self.balances), dict(self.nonces)
        for tx in transactions:
            if tx.chain_id != self.chain_id or not tx.is_valid():
                raise ValueError("wrong chain ID or invalid signature")
            sender = tx.sender_address
            if tx.nonce != nonces.get(sender, 0):
                raise ValueError("unexpected account nonce (replay or out-of-order transfer)")
            if tx.amount > balances.get(sender, 0):
                raise ValueError("insufficient funds")
            balances[sender] = balances.get(sender, 0) - tx.amount
            balances[tx.recipient] = balances.get(tx.recipient, 0) + tx.amount
            nonces[sender] = tx.nonce + 1
        return Ledger(balances, nonces, chain_id=self.chain_id)
