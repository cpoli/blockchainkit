"""Account state and cumulative-work fork selection for a fixed-difficulty chain."""

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from blockchainkit.consensus.pow import expected_trials, valid_pow
from blockchainkit.crypto.number_theory import integer
from blockchainkit.structures.block import Block
from blockchainkit.structures.transaction import Transaction


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
        chain_id: str = "blockchainkit-demo",
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


class Blockchain:
    """Store valid forks and select the tip with greatest cumulative work.

    Parameters
    ----------
    genesis : Block
        Mined, empty height-zero block with a zero parent hash.
    initial_state : Ledger, optional
        Shared initial allocation and chain ID.

    Notes
    -----
    Difficulty is fixed by genesis; a child cannot lower its own target.
    Equal-work ties select the lexicographically smaller hash, so peers with
    the same block set converge independent of arrival order. This teaching
    tie-break is not Bitcoin's first-seen behavior. Each fork retains its own
    ledger snapshot, so reorganizations restore balances and nonces.
    """

    def __init__(self, genesis: Block, initial_state: Ledger | None = None) -> None:
        if genesis.height != 0 or genesis.previous_hash != bytes(32) or genesis.transactions:
            raise ValueError("genesis must have height zero, zero parent, and no transactions")
        if not valid_pow(genesis):
            raise ValueError("genesis proof of work is invalid")
        self._blocks = {genesis.hash: genesis}
        self._states = {genesis.hash: initial_state or Ledger()}
        self._work = {genesis.hash: expected_trials(genesis.difficulty)}
        self._tip = genesis.hash
        self._difficulty = genesis.difficulty

    @property
    def tip(self) -> Block:
        """Return the selected canonical tip."""
        return self._blocks[self._tip]

    @property
    def state(self) -> Ledger:
        """Return the selected tip's validated ledger snapshot."""
        return self._states[self._tip]

    @property
    def cumulative_work(self) -> int:
        """Return total expected hash trials represented by the canonical chain."""
        return self._work[self._tip]

    def contains(self, block_hash: bytes) -> bool:
        """Return whether this node already knows a block, including side forks."""
        return block_hash in self._blocks

    def add(self, block: Block) -> bool:
        """Validate and store a child; return whether the preferred tip changed.

        Unknown parents raise ValueError. Networking experiments can buffer
        such blocks until their parents arrive. Duplicate blocks are ignored.
        """
        digest = block.hash
        if digest in self._blocks:
            return False
        parent = self._blocks.get(block.previous_hash)
        if parent is None:
            raise ValueError("unknown parent")
        if block.height != parent.height + 1 or block.timestamp < parent.timestamp:
            raise ValueError("invalid height or timestamp before parent")
        if block.difficulty != self._difficulty or not valid_pow(block):
            raise ValueError("invalid difficulty or proof of work")
        state = self._states[parent.hash].apply(block.transactions)
        work = self._work[parent.hash] + expected_trials(block.difficulty)
        self._blocks[digest], self._states[digest], self._work[digest] = block, state, work
        preferred = work > self._work[self._tip] or (
            work == self._work[self._tip] and digest < self._tip
        )
        if preferred:
            self._tip = digest
        return preferred

    def canonical_blocks(self) -> tuple[Block, ...]:
        """Return the selected chain from genesis through tip."""
        result = [self.tip]
        while result[-1].height:
            result.append(self._blocks[result[-1].previous_hash])
        return tuple(reversed(result))
