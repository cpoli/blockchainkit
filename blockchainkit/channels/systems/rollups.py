r"""Rollups: zk-rollups (2018) and optimistic rollups (2019).

A rollup executes transactions off chain but posts them, compressed, to the
chain, with the state root they lead to. Because the data is on chain,
anyone can rebuild the state; what remains is to convince the chain that
the posted root is right. There are two ways.

**zk-rollups** (Barry Whitehat's *roll_up*, and Buterin's proposal, 2018)
post a succinct *validity proof* with each batch. The contract accepts the
new root only if the proof verifies, which costs a constant amount of gas
however many transactions the batch holds, so the cost per transaction
falls toward that of its calldata alone:

.. math::

   g(n) = \frac{G_{\text{verify}}}{n} + 16\,b,

for ``n`` transactions of ``b`` bytes each, against 21,000 gas for a
transfer on chain.

**Optimistic rollups** (Adler and Quintyne-Collins, 2019) post no proof.
A root becomes final after a challenge window, during which anyone who
recomputes the batch and disagrees can prove fraud. The proof is found by
*bisection* (Kalodner et al., Arbitrum, 2018): asserter and challenger
compare intermediate state roots, halving the disputed range each round,
until they disagree about a single transaction, which the chain re-executes.
That takes :math:`\lceil \log_2 n \rceil` rounds, and a withdrawal must
wait out the window.

Here invalid transactions, such as overdrafts, are skipped rather than
rejecting the batch, as rollups do. There is no proof system yet: a
:class:`~blockchainkit.channels.core.base.ValidityProof` states what it
proves, and verification re-executes the batch on the state rebuilt from
the posted data, standing in for a SNARK verifier.
"""

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import FraudProof, Transfer, ValidityProof
from blockchainkit.constants import ROLLUP_DOMAIN
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.systems.merkle import MerkleTree
from blockchainkit.structures.utils.encoding import canonical_json

CALLDATA_GAS_PER_BYTE = 16
"""Gas per nonzero byte of calldata (EIP-2028)."""

TRANSFER_GAS = 21_000
"""Gas of a plain transfer on chain."""


def state_root(balances: Mapping[str, int]) -> bytes:
    """Merkle root over the accounts' ``(name, balance)`` leaves, sorted by name."""
    leaves = [ROLLUP_DOMAIN + canonical_json([a, balances[a]]) for a in sorted(balances)]
    return MerkleTree(leaves).root


def batch_digest(batch: Sequence[Transfer]) -> bytes:
    """Hash of a batch's transactions, as posted on chain."""
    return sha256(
        ROLLUP_DOMAIN + canonical_json([[t.sender, t.recipient, t.amount] for t in batch])
    )


def apply_transfer(balances: Mapping[str, int], transfer: Transfer) -> dict[str, int]:
    """The balances after ``transfer``; unchanged if it overdraws or moves nothing."""
    after = dict(balances)
    amount = transfer.amount
    if amount > 0 and after.get(transfer.sender, 0) >= amount:
        after[transfer.sender] -= amount
        after[transfer.recipient] = after.get(transfer.recipient, 0) + amount
    return after


def execute_batch(
    balances: Mapping[str, int], batch: Sequence[Transfer]
) -> tuple[dict[str, int], tuple[bytes, ...]]:
    """Run a batch; return the final balances and the trace of state roots.

    The trace has ``len(batch) + 1`` roots: before the batch, then after each transaction.

    Examples
    --------
    >>> from blockchainkit.channels import Transfer, execute_batch
    >>> after, trace = execute_batch({"alice": 5}, [Transfer("alice", "bob", 3)])
    >>> after, len(trace)
    ({'alice': 2, 'bob': 3}, 2)
    """
    state = dict(balances)
    roots = [state_root(state)]
    for transfer in batch:
        state = apply_transfer(state, transfer)
        roots.append(state_root(state))
    return state, tuple(roots)


def batch_gas(transactions: int, *, bytes_per_transaction: int, fixed_gas: int) -> int:
    """Gas to post a batch: a fixed cost (proof verification, root update) plus its calldata.

    Examples
    --------
    >>> from blockchainkit.channels import batch_gas
    >>> batch_gas(1_000, bytes_per_transaction=12, fixed_gas=300_000) / 1_000
    492.0
    """
    integer(transactions, "transactions", 1)
    integer(bytes_per_transaction, "bytes_per_transaction")
    integer(fixed_gas, "fixed_gas")
    return fixed_gas + transactions * bytes_per_transaction * CALLDATA_GAS_PER_BYTE


class ZKRollup:
    """A rollup contract that accepts a new state root only with a validity proof.

    Parameters
    ----------
    balances : Mapping
        The genesis state.
    verifier_gas : int
        Gas to verify one proof (a Groth16 verification costs about 200,000 to 300,000).
    bytes_per_transaction : int
        Calldata per compressed transaction.

    Examples
    --------
    >>> from blockchainkit.channels import Transfer, ZKRollup
    >>> rollup = ZKRollup({"alice": 10})
    >>> batch = [Transfer("alice", "bob", 4)]
    >>> gas = rollup.submit(batch, rollup.prove(batch))
    >>> dict(rollup.balances), gas
    ({'alice': 6, 'bob': 4}, 300192)
    """

    def __init__(
        self,
        balances: Mapping[str, int],
        *,
        verifier_gas: int = 300_000,
        bytes_per_transaction: int = 12,
    ) -> None:
        for amount in balances.values():
            integer(amount, "balance")
        integer(verifier_gas, "verifier_gas")
        integer(bytes_per_transaction, "bytes_per_transaction")
        self.verifier_gas, self.bytes_per_transaction = verifier_gas, bytes_per_transaction
        self.balances: Mapping[str, int] = MappingProxyType(dict(balances))
        self.root = state_root(balances)

    def prove(
        self, batch: Sequence[Transfer], *, claimed_root: bytes | None = None
    ) -> ValidityProof:
        """The operator proves the batch's effect on the current state.

        Raises
        ------
        ValueError
            ``claimed_root`` is not the batch's true result: a sound proof
            system has no proof of a false statement.
        """
        after, _ = execute_batch(self.balances, batch)
        new_root = state_root(after)
        if claimed_root is not None and claimed_root != new_root:
            raise ValueError("no proof exists for a false state transition")
        return ValidityProof(self.root, new_root, batch_digest(batch))

    def submit(self, batch: Sequence[Transfer], proof: ValidityProof) -> int:
        """Post a batch and its proof; return the gas it cost.

        Raises
        ------
        ValueError
            The proof is for another state, batch, or result.
        """
        if proof.old_root != self.root or proof.batch_digest != batch_digest(batch):
            raise ValueError("the proof is for another state or batch")
        after, _ = execute_batch(self.balances, batch)  # Stands in for SNARK verification.
        if state_root(after) != proof.new_root:
            raise ValueError("the proof does not verify")
        self.balances, self.root = MappingProxyType(after), proof.new_root
        return batch_gas(
            max(len(batch), 1),
            bytes_per_transaction=self.bytes_per_transaction,
            fixed_gas=self.verifier_gas,
        )


def bisect(claimed: Sequence[bytes], honest: Sequence[bytes]) -> tuple[int, int]:
    """Find the first transaction whose result two traces disagree on, by halving.

    Both traces start from the same root and end in different ones.

    Returns
    -------
    tuple of int
        The disputed transaction's index and the rounds it took.

    Examples
    --------
    >>> from blockchainkit.channels import bisect
    >>> bisect(list(b"abcdefgh"), list(b"abcdeXYZ"))
    (4, 3)
    """
    if len(claimed) != len(honest) or len(claimed) < 2:
        raise ValueError("traces must have the same length, at least 2")
    if claimed[0] != honest[0] or claimed[-1] == honest[-1]:
        raise ValueError("traces must agree at the start and disagree at the end")
    low, high, rounds = 0, len(claimed) - 1, 0
    while high - low > 1:
        middle = (low + high) // 2
        if claimed[middle] == honest[middle]:
            low = middle
        else:
            high = middle
        rounds += 1
    return low, rounds


class OptimisticRollup:
    """A rollup contract that accepts state roots unless someone proves fraud in time.

    Parameters
    ----------
    balances : Mapping
        The genesis state.
    window : int
        Blocks an assertion can be challenged.
    bond : int
        What a proposer stakes on each assertion, paid to a successful challenger.

    Examples
    --------
    >>> from blockchainkit.channels import OptimisticRollup, Transfer, execute_batch, state_root
    >>> rollup = OptimisticRollup({"alice": 10}, window=100)
    >>> batch = [Transfer("alice", "bob", 4), Transfer("bob", "carol", 1)]
    >>> _, trace = execute_batch({"alice": 10}, batch)
    >>> forged = (*trace[:2], state_root({"alice": 6, "bob": 3, "mallory": 1}))
    >>> rollup.propose("mallory", batch, forged, height=1)
    0
    >>> rollup.challenge(0, "carol", height=50).step
    1
    >>> dict(rollup.payouts)
    {'carol': 10}
    """

    def __init__(self, balances: Mapping[str, int], *, window: int, bond: int = 10) -> None:
        for amount in balances.values():
            integer(amount, "balance")
        integer(window, "window", 1)
        integer(bond, "bond")
        self.window, self.bond = window, bond
        self.balances: Mapping[str, int] = MappingProxyType(dict(balances))
        self.root = state_root(balances)
        self.pending: list[tuple[str, tuple[Transfer, ...], tuple[bytes, ...], int]] = []
        self.payouts: dict[str, int] = {}

    def propose(
        self, proposer: str, batch: Sequence[Transfer], trace: Sequence[bytes], *, height: int
    ) -> int:
        """Post a batch with its claimed trace of state roots, and a bond; return its index.

        The contract checks only that the trace starts at the previous claimed root.
        """
        integer(height, "height")
        if len(trace) != len(batch) + 1:
            raise ValueError("the trace needs one root per transaction, plus the starting root")
        previous = self.pending[-1][2][-1] if self.pending else self.root
        if trace[0] != previous:
            raise ValueError("the trace does not start at the previous root")
        self.pending.append((proposer, tuple(batch), tuple(trace), height + self.window))
        return len(self.pending) - 1

    def challenge(self, index: int, challenger: str, *, height: int) -> FraudProof | None:
        """Re-execute pending assertion ``index``; on fraud, discard it and every later one.

        Returns
        -------
        FraudProof or None
            The single wrong step, or None if the assertion is correct.
        """
        integer(height, "height")
        _, batch, trace, deadline = self.pending[index]
        if height >= deadline:
            raise ValueError("the challenge window is over")
        state = dict(self.balances)
        for _, earlier, _, _ in self.pending[:index]:
            state, _ = execute_batch(state, earlier)
        _, honest = execute_batch(state, batch)
        if honest[-1] == trace[-1]:
            return None
        step, rounds = bisect(trace, honest)
        del self.pending[index:]
        self.payouts[challenger] = self.payouts.get(challenger, 0) + self.bond
        return FraudProof(step, rounds, trace[step + 1], honest[step + 1])

    def finalize(self, *, height: int) -> int:
        """Make final every assertion whose window has closed; return how many."""
        integer(height, "height")
        done = 0
        while self.pending and self.pending[0][3] <= height:
            _, batch, trace, _ = self.pending.pop(0)
            after, _ = execute_batch(self.balances, batch)
            self.balances, self.root = MappingProxyType(after), trace[-1]
            done += 1
        return done
