"""Plasma (Poon and Buterin, 2017): child chains secured by exit games.

Plasma moves whole blocks off chain. An operator runs a child chain and
posts only each block's Merkle root to a root-chain contract. The contract
cannot check the child chain's transactions, and the operator may withhold
blocks or include invalid ones; what keeps coins safe is that their owner
can always *exit*: prove on the root chain that it owns a coin, then wait
out a challenge period during which anyone can prove the exit wrong.

This module follows Plasma Cash (Buterin, 2018), the simplest exit
game. Every coin is indivisible and has its own slot in a
sparse Merkle tree, so each block proves either the coin's transfer or that
the coin did not move. An exit presents the coin's last transfer and the
one before it, and a challenger answers with one of:

- a *spend*: a later transfer signed by the exiting owner, so it no longer
  owns the coin;
- a *double spend*: a different transfer signed by the previous owner,
  included between the two blocks, so the exiting transfer was never valid.

Plasma Cash's third challenge, an invalid history answered by its owner,
and the bonds that pay challengers are omitted here.
"""

from collections.abc import Sequence
from dataclasses import replace

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import CoinTransfer, InclusionProof, PlasmaExit
from blockchainkit.channels.utils.scripts import PublicKey, signature
from blockchainkit.constants import PLASMA_DOMAIN
from blockchainkit.crypto.systems.signatures import verify
from blockchainkit.structures.systems.sparse_merkle import SparseMerkleTree, verify_sparse_proof
from blockchainkit.structures.utils.encoding import canonical_json


def transfer_message(coin: int, owner: PublicKey, parent_block: int) -> bytes:
    """The bytes the previous owner signs to send ``coin`` to ``owner``."""
    return PLASMA_DOMAIN + canonical_json([coin, list(owner), parent_block])


def sign_transfer(private: int, coin: int, owner: PublicKey, parent_block: int) -> CoinTransfer:
    """Send ``coin`` to ``owner``, signed by its current owner, who received it in ``parent_block``.

    Examples
    --------
    >>> from blockchainkit.channels import sign_transfer
    >>> from blockchainkit.crypto import public_key
    >>> sign_transfer(7, 0, public_key(5), 1).parent_block
    1
    """
    integer(coin, "coin")
    integer(parent_block, "parent_block", 1)
    return CoinTransfer(
        coin, owner, parent_block, signature(private, transfer_message(coin, owner, parent_block))
    )


def _leaf(transfer: CoinTransfer) -> bytes:
    signed = None
    if transfer.signature is not None:
        signed = [list(transfer.signature.commitment), transfer.signature.response]
    return canonical_json([transfer.coin, list(transfer.owner), transfer.parent_block, signed])


def _key(coin: int) -> bytes:
    return coin.to_bytes(8, "big")


class PlasmaChain:
    """A Plasma Cash root-chain contract and the operator's child-chain blocks.

    Parameters
    ----------
    period : int
        Blocks an exit waits for challenges.
    depth : int
        Depth of each block's sparse Merkle tree; coins are numbered below ``2 ** depth``.

    Examples
    --------
    >>> from blockchainkit.channels import PlasmaChain, sign_transfer
    >>> from blockchainkit.crypto import public_key
    >>> chain = PlasmaChain(period=7)
    >>> deposit = chain.deposit(public_key(7))  # Alice deposits coin 0 in block 1.
    >>> block = chain.submit_block([sign_transfer(7, 0, public_key(5), 1)])  # To Bob.
    >>> exit_id = chain.start_exit(chain.prove(0, block), deposit, height=10)
    >>> chain.finalize(exit_id, height=17).owner == public_key(5)
    True
    """

    def __init__(self, *, period: int = 7, depth: int = 16) -> None:
        integer(period, "period", 1)
        integer(depth, "depth", 1)
        self.period, self.depth = period, depth
        self.roots: dict[int, bytes] = {}  # Root-chain storage.
        self.blocks: dict[int, dict[int, CoinTransfer]] = {}  # The operator's data.
        self._trees: dict[int, SparseMerkleTree] = {}
        self.coins = 0
        self.exits: list[PlasmaExit] = []
        self.exited: set[int] = set()

    def _publish(self, transfers: Sequence[CoinTransfer]) -> int:
        tree, moved = SparseMerkleTree(self.depth), {}
        for transfer in transfers:
            if not 0 <= transfer.coin < self.coins or transfer.coin in moved:
                raise ValueError("each block moves each existing coin at most once")
            tree = tree.set(_key(transfer.coin), _leaf(transfer))
            moved[transfer.coin] = transfer
        number = len(self.roots) + 1
        self.roots[number] = tree.root
        self.blocks[number], self._trees[number] = moved, tree
        return number

    def deposit(self, owner: PublicKey) -> InclusionProof:
        """Lock a new coin on the root chain, which makes its deposit block itself."""
        if self.coins >= 2**self.depth:
            raise ValueError("no coin slots left")
        self.coins += 1
        number = self._publish([CoinTransfer(self.coins - 1, owner, 0)])
        return self.prove(self.coins - 1, number)

    def submit_block(self, transfers: Sequence[CoinTransfer]) -> int:
        """The operator commits a block of transfers; the root chain checks none of them."""
        return self._publish(transfers)

    def prove(self, coin: int, block: int) -> InclusionProof:
        """The operator's proof of ``coin``'s transfer in ``block``.

        Raises
        ------
        ValueError
            The block does not move the coin.
        """
        if coin not in self.blocks[block]:
            raise ValueError(f"coin {coin} did not move in block {block}")
        proof = self._trees[block].prove(_key(coin))
        return InclusionProof(self.blocks[block][coin], block, proof)

    def _included(self, item: InclusionProof) -> bool:
        root = self.roots.get(item.block)
        return (
            root is not None
            and item.proof.key == _key(item.transfer.coin)
            and item.proof.value == _leaf(item.transfer)
            and verify_sparse_proof(item.proof, root)
        )

    @staticmethod
    def _signed_by(transfer: CoinTransfer, owner: PublicKey) -> bool:
        message = transfer_message(transfer.coin, transfer.owner, transfer.parent_block)
        return transfer.signature is not None and verify(message, transfer.signature, owner)

    def start_exit(
        self, exiting: InclusionProof, parent: InclusionProof | None, *, height: int
    ) -> int:
        """Claim a coin with its last transfer and the one before it; return the exit's id.

        A coin that has not moved since its deposit exits with ``parent=None``.

        Raises
        ------
        ValueError
            A proof fails, or the exiting transfer does not spend ``parent``.
        """
        integer(height, "height")
        transfer = exiting.transfer
        if transfer.coin in self.exited:
            raise ValueError("the coin has already exited")
        if not self._included(exiting):
            raise ValueError("the exiting transfer is not in that block")
        if parent is None:
            if transfer.signature is not None or transfer.parent_block != 0:
                raise ValueError("only a deposit can exit without its parent")
        elif not (
            self._included(parent)
            and parent.transfer.coin == transfer.coin
            and transfer.parent_block == parent.block < exiting.block
            and self._signed_by(transfer, parent.transfer.owner)
        ):
            raise ValueError("the exiting transfer does not validly spend its parent")
        parent_block = 0 if parent is None else parent.block
        self.exits.append(
            PlasmaExit(
                transfer.coin, transfer.owner, exiting.block, parent_block, height + self.period
            )
        )
        return len(self.exits) - 1

    def _pending(self, exit_id: int) -> PlasmaExit:
        found = self.exits[exit_id]
        if found.status != "pending":
            raise ValueError(f"exit {exit_id} is {found.status}")
        return found

    def challenge(self, exit_id: int, evidence: InclusionProof, *, height: int) -> bool:
        """Cancel a pending exit with a spend or a double spend of its coin; True if it worked."""
        integer(height, "height")
        pending = self._pending(exit_id)
        transfer = evidence.transfer
        if height >= pending.deadline or transfer.coin != pending.coin:
            return False
        if not self._included(evidence):
            return False
        spent = (
            evidence.block > pending.block
            and transfer.parent_block == pending.block
            and self._signed_by(transfer, pending.owner)
        )
        previous = self.blocks.get(pending.parent_block, {}).get(pending.coin)
        double = (
            previous is not None
            and pending.parent_block < evidence.block < pending.block
            and transfer.parent_block == pending.parent_block
            and self._signed_by(transfer, previous.owner)
        )
        if not (spent or double):
            return False
        self.exits[exit_id] = replace(pending, status="challenged")
        return True

    def finalize(self, exit_id: int, *, height: int) -> PlasmaExit:
        """Release the coin to an unchallenged exit once its period is over."""
        integer(height, "height")
        pending = self._pending(exit_id)
        if height < pending.deadline:
            raise ValueError("the challenge period is not over")
        if pending.coin in self.exited:
            raise ValueError("the coin has already exited")
        self.exited.add(pending.coin)
        self.exits[exit_id] = replace(pending, status="finalized")
        return self.exits[exit_id]
