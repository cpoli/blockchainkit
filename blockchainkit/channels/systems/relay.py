"""BTC Relay (2016): a Bitcoin light client inside an Ethereum contract.

A contract on one chain cannot see another chain, so it cannot tell whether
a payment there happened. BTC Relay, launched on Ethereum in 2016, made it
see Bitcoin the way a light client does (Nakamoto's simplified payment
verification). Anyone could submit Bitcoin block headers; the contract
checked that each linked to a stored one and met its proof-of-work target,
and tracked the chain with the most cumulative work. A contract could then
ask whether a transaction was in a block of that chain, with enough blocks
on top, by checking a Merkle proof against the header's root. That made
trustless ether-for-bitcoin swaps possible, and is how later light-client
bridges work.

The relay is only as safe as the work it demands. Here the headers are
:class:`~blockchainkit.structures.systems.block.BlockHeader` objects at
teaching difficulty, without Bitcoin's retargeting, so the contract demands
a fixed ``minimum_difficulty`` instead; without one, anyone could feed it a
heavier chain of worthless headers. Relayers were paid fees in the
deployed contract; here they are not.
"""

from collections.abc import Sequence
from dataclasses import replace

from blockchainkit._validation import integer
from blockchainkit.consensus.systems.pow import expected_trials, target
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.structures.core.base import MerkleProof
from blockchainkit.structures.systems.block import BlockHeader
from blockchainkit.structures.systems.merkle import MerkleTree, verify_proof


def mine_header(
    previous: BlockHeader | None,
    payloads: Sequence[bytes],
    *,
    difficulty: int = 8,
    timestamp: int = 0,
    max_attempts: int = 1_000_000,
) -> BlockHeader:
    """A header committing to ``payloads`` through a Merkle root, with valid proof of work.

    Parameters
    ----------
    previous : BlockHeader or None
        The parent; None for a genesis header.
    payloads : sequence of bytes
        The block's transactions.
    difficulty : int
        Required leading zero bits of the header hash.
    timestamp : int
        The header's timestamp.
    max_attempts : int
        Nonces to try before giving up.

    Raises
    ------
    TimeoutError
        No nonce worked within ``max_attempts``.
    """
    integer(max_attempts, "max_attempts", 1)
    header = BlockHeader(
        previous_hash=bytes(32) if previous is None else previous.hash,
        merkle_root=MerkleTree(payloads).root,
        height=0 if previous is None else previous.height + 1,
        timestamp=timestamp,
        difficulty=difficulty,
    )
    limit = target(difficulty)
    for nonce in range(max_attempts):
        candidate = replace(header, nonce=nonce)
        if int.from_bytes(candidate.hash, "big") <= limit:
            return candidate
    raise TimeoutError(f"no proof of work in {max_attempts} attempts")


class BTCRelay(Contract):
    """Stores proof-of-work headers, follows the heaviest chain, and verifies inclusion.

    Constructor arguments: the ``genesis`` header the relay trusts, and the
    ``minimum_difficulty`` every later header must meet.

    Examples
    --------
    >>> from blockchainkit.channels import BTCRelay, mine_header
    >>> from blockchainkit.contracts import World
    >>> genesis = mine_header(None, [b"coinbase"])
    >>> block = mine_header(genesis, [b"coinbase 1", b"alice pays bob"])
    >>> world = World()
    >>> relay = world.deploy("deployer", BTCRelay, genesis, 8)
    >>> world.transact("relayer", relay, "store_header", block).success
    True
    >>> world.view(relay, "best_height")
    1
    """

    layout = ("headers", "work", "tip", "minimum_difficulty")

    def constructor(self, genesis: BlockHeader, minimum_difficulty: int) -> None:
        self.write("headers", genesis.hash, genesis)
        self.write("work", genesis.hash, expected_trials(genesis.difficulty))
        self.write("tip", genesis.hash)
        self.write("minimum_difficulty", minimum_difficulty)

    def store_header(self, header: BlockHeader) -> None:
        """Accept a header that extends a stored one and carries enough proof of work."""
        parent = self.read("headers", header.previous_hash)
        self.require(parent != 0, "unknown parent")
        self.require(self.read("headers", header.hash) == 0, "header already stored")
        self.require(header.height == parent.height + 1, "wrong height")
        self.require(header.difficulty >= self.read("minimum_difficulty"), "difficulty too low")
        self.require(
            int.from_bytes(header.hash, "big") <= target(header.difficulty), "proof of work missing"
        )
        work = self.read("work", header.previous_hash) + expected_trials(header.difficulty)
        self.write("headers", header.hash, header)
        self.write("work", header.hash, work)
        if work > self.read("work", self.read("tip")):
            self.write("tip", header.hash)
        self.emit("HeaderStored", height=header.height, work=work)

    def best_height(self) -> int:
        """Height of the heaviest stored chain's tip."""
        return int(self.read("headers", self.read("tip")).height)

    def confirmations(self, block_hash: bytes) -> int:
        """Blocks from ``block_hash`` to the heaviest tip, both included; 0 off that chain."""
        header = self.read("headers", block_hash)
        if header == 0:
            return 0
        current = self.read("headers", self.read("tip"))
        while current.height > header.height:
            current = self.read("headers", current.previous_hash)
        if current.hash != block_hash:
            return 0
        return self.best_height() - int(header.height) + 1

    def verify_transaction(
        self, payload: bytes, block_hash: bytes, proof: MerkleProof, confirmations: int
    ) -> bool:
        """True if ``payload`` is in that block, on the heaviest chain, under enough blocks."""
        if self.confirmations(block_hash) < confirmations:
            return False
        return verify_proof(payload, proof, self.read("headers", block_hash).merkle_root)
