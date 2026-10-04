"""Practical Byzantine Fault Tolerance (Castro and Liskov 1999): the normal-case round.

With n = 3f + 1 replicas, any two quorums of 2f + 1 overlap in at least f + 1
replicas, so at least one honest replica is in both. A replica *prepares* a
value after 2f matching prepare messages and *commits* it after 2f + 1
matching commits. Two honest replicas can then never commit different values
in one view, even if the leader equivocates, as long as at most f replicas
are faulty.
"""

from collections.abc import Set

from blockchainkit._validation import integer
from blockchainkit.consensus.core.base import PBFTResult


def quorum_size(replicas: int) -> int:
    """Return 2f + 1 for the largest f with n >= 3f + 1.

    >>> from blockchainkit.consensus import quorum_size
    >>> quorum_size(4), quorum_size(7)
    (3, 5)
    """
    integer(replicas, "replicas", 4)
    return 2 * ((replicas - 1) // 3) + 1


def pbft_round(
    replicas: int, faulty: Set[int], value: str, *, equivocate: bool = False, other: str = "B"
) -> PBFTResult:
    """Run one PBFT pre-prepare / prepare / commit exchange with leader 0.

    Faulty replicas send prepare and commit messages for *both* values to
    everyone, the most confusing thing they can do. A faulty leader with
    ``equivocate=True`` pre-prepares ``value`` to the first half of the honest
    replicas and ``other`` to the rest.

    Parameters
    ----------
    replicas : int
        Number of replicas n, at least 4.
    faulty : set of int
        Faulty replica numbers. The protocol is sized for f = (n - 1) // 3;
        pass more to see safety fail.
    value, other : str
        The leader's value, and the conflicting one an equivocating leader
        also sends.

    Returns
    -------
    PBFTResult
        What each honest replica prepared and committed.
    """
    f = (quorum_size(replicas) - 1) // 2
    if any(r not in range(replicas) for r in faulty):
        raise ValueError("faulty replicas must be replica numbers")
    honest = [r for r in range(replicas) if r not in faulty]
    faulty_backups = len(faulty - {0})

    # 1. Pre-prepare: the leader (replica 0) proposes a value to each replica.
    equivocating = 0 in faulty and equivocate
    split = (len(honest) + 1) // 2
    proposal = {r: other if equivocating and i >= split else value for i, r in enumerate(honest)}

    # 2. Prepare: honest backups echo their proposal; faulty backups echo both values.
    def prepares(v: str) -> int:
        return sum(1 for r in honest if r != 0 and proposal[r] == v) + faulty_backups

    prepared = {r: proposal[r] if prepares(proposal[r]) >= 2 * f else None for r in honest}

    # 3. Commit: honest replicas commit what they prepared; faulty ones commit both.
    def commits(v: str) -> int:
        return sum(1 for r in honest if prepared[r] == v) + len(faulty)

    committed = {
        r: v if v is not None and commits(v) >= 2 * f + 1 else None for r, v in prepared.items()
    }
    return PBFTResult(prepared, committed)
