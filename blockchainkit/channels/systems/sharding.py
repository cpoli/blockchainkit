r"""Sharding: OmniLedger (Kokoris-Kogias, Jovanovic, Gasser, Gailly, Syta and Ford, 2018).

Splitting the validators into shards, each keeping its own part of the
ledger, multiplies throughput by the number of shards, but each shard is
only as safe as its own committee. OmniLedger assigns validators to shards
at random every epoch, from unbiasable randomness (RandHound), so an
adversary controlling a fraction of all validators cannot choose where they
land. A Byzantine-fault-tolerant committee of ``m`` fails if a third or more
of it is malicious, which for ``M`` malicious validators out of ``N`` has
the hypergeometric probability

.. math::

   P(X \ge m/3) = \sum_{x \ge m/3} \frac{\binom{M}{x}\binom{N-M}{m-x}}{\binom{N}{m}}.

It falls exponentially with the committee size, which is why shards must
stay large. Transactions that spend coins on several shards use Atomix, a
client-driven atomic commit: every input shard first *locks* the input and
returns a proof of acceptance or rejection; if all accept, the client
presents the proofs to the output shard to commit, and otherwise to the
input shards to unlock. RandHound is replaced here by a seeded shuffle, and
proofs of acceptance by the shards' own word.
"""

from collections.abc import Mapping, Sequence
from math import ceil, comb
from random import Random
from types import MappingProxyType

from blockchainkit._validation import integer, probability
from blockchainkit._validation import seed as check_seed
from blockchainkit.channels.core.base import AtomixResult


def shard_failure_probability(
    validators: int, malicious: int, shard_size: int, *, threshold: float = 1 / 3
) -> float:
    """Chance that a random committee of ``shard_size`` is at least ``threshold`` malicious.

    Examples
    --------
    >>> from blockchainkit.channels import shard_failure_probability
    >>> f"{shard_failure_probability(1_000, 250, 100):.4f}"
    '0.0214'
    """
    integer(validators, "validators", 1)
    integer(malicious, "malicious")
    integer(shard_size, "shard_size", 1)
    probability(threshold, "threshold")
    if malicious > validators or shard_size > validators:
        raise ValueError("malicious and shard_size cannot exceed validators")
    first = ceil(threshold * shard_size)
    total = comb(validators, shard_size)
    tail = sum(
        comb(malicious, x) * comb(validators - malicious, shard_size - x)
        for x in range(first, min(malicious, shard_size) + 1)
    )
    return tail / total


def assign_shards(validators: int, shards: int, *, seed: int = 0) -> tuple[tuple[int, ...], ...]:
    """Shuffle validators ``0 .. validators - 1`` into ``shards`` committees of near-equal size.

    Examples
    --------
    >>> from blockchainkit.channels import assign_shards
    >>> [len(c) for c in assign_shards(10, 3, seed=1)]
    [4, 3, 3]
    """
    integer(validators, "validators", 1)
    integer(shards, "shards", 1)
    check_seed(seed)
    if shards > validators:
        raise ValueError("more shards than validators")
    order = list(range(validators))
    Random(seed).shuffle(order)
    return tuple(tuple(sorted(order[i::shards])) for i in range(shards))


def compromised_epochs(
    validators: int, malicious: int, shards: int, *, epochs: int, seed: int = 0
) -> float:
    """Fraction of epochs in which some committee is a third or more malicious.

    Validators ``0 .. malicious - 1`` are the malicious ones; every epoch
    reshuffles the committees.
    """
    integer(malicious, "malicious")
    integer(epochs, "epochs", 1)
    check_seed(seed)
    rng = Random(seed)
    failed = 0
    for _ in range(epochs):
        committees = assign_shards(validators, shards, seed=rng.randrange(2**32))
        if any(3 * sum(v < malicious for v in c) >= len(c) for c in committees):
            failed += 1
    return failed / epochs


def atomix_transfer(
    shards: Sequence[Mapping[str, int]],
    inputs: Sequence[tuple[int, str, int]],
    output: tuple[int, str],
) -> AtomixResult:
    """Spend ``inputs`` on several shards and credit their total to ``output``, atomically.

    Parameters
    ----------
    shards : sequence of Mapping
        Each shard's balances.
    inputs : sequence of tuple
        ``(shard, account, amount)`` to spend.
    output : tuple
        ``(shard, account)`` to credit.

    Returns
    -------
    AtomixResult
        The shards' balances after commit, or after abort and unlock.

    Examples
    --------
    >>> from blockchainkit.channels import atomix_transfer
    >>> shards = [{"alice": 5}, {"alice": 3}, {}]
    >>> atomix_transfer(shards, [(0, "alice", 5), (1, "alice", 3)], (2, "bob")).committed
    True
    >>> atomix_transfer(shards, [(0, "alice", 5), (1, "alice", 4)], (2, "bob")).rejected
    (1,)
    """
    state = [dict(balances) for balances in shards]
    for shard, _, amount in inputs:
        integer(shard, "shard")
        integer(amount, "amount", 1)
        if shard >= len(state):
            raise ValueError("no such shard")
    if not 0 <= output[0] < len(state):
        raise ValueError("no such shard")
    # Phase 1: each input shard locks the input, or rejects it.
    locked, rejected = [], []
    for shard, account, amount in inputs:
        if state[shard].get(account, 0) >= amount:
            state[shard][account] -= amount
            locked.append((shard, account, amount))
        else:
            rejected.append(shard)
    # Phase 2: commit on the output shard, or unlock every accepted input.
    if rejected:
        for shard, account, amount in locked:
            state[shard][account] += amount
    else:
        total = sum(amount for _, _, amount in inputs)
        state[output[0]][output[1]] = state[output[0]].get(output[1], 0) + total
    frozen = tuple(MappingProxyType(balances) for balances in state)
    return AtomixResult(not rejected, frozen, tuple(rejected))
