"""Cumulative-work fork selection for a fixed-difficulty chain."""

from blockchainkit.consensus.systems.pow import expected_trials, valid_pow
from blockchainkit.structures.systems.block import Block
from blockchainkit.structures.systems.ledger import Ledger


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

    Keeping a full snapshot per block makes reorganizations easy to inspect,
    at a memory cost proportional to blocks times accounts. Real nodes keep
    one state and undo data instead.
    """

    def __init__(self, genesis: Block, initial_state: Ledger | None = None) -> None:
        if genesis.height != 0 or genesis.previous_hash != bytes(32) or genesis.transactions:
            raise ValueError("genesis must have height zero, zero parent, and no transactions")
        if not valid_pow(genesis):
            raise ValueError("genesis proof of work is invalid")
        self._blocks = {genesis.hash: genesis}
        self._states = {genesis.hash: Ledger() if initial_state is None else initial_state}
        self._work = {genesis.hash: expected_trials(genesis.difficulty)}
        self._tip = genesis.hash
        self._difficulty = genesis.difficulty

    def __repr__(self) -> str:
        return (
            f"Blockchain(height={self.tip.height}, blocks={len(self._blocks)}, "
            f"tip={self._tip.hex()[:16]}..., cumulative_work={self.cumulative_work})"
        )

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
