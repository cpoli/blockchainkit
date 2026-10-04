"""Simplified payment verification: checking a chain of headers without blocks.

Nakamoto's whitepaper (section 8) observed that a client can verify a payment
without downloading the blockchain: keep only the block headers, check that
they link and carry proof of work, and ask for a Merkle proof that the
transaction is in one of them. Trust shifts to an assumption: the
heaviest header chain is the one honest miners extended.
"""

from collections.abc import Sequence

from blockchainkit.consensus.systems.pow import expected_trials, target
from blockchainkit.structures.systems.block import BlockHeader


def verify_header_chain(headers: Sequence[BlockHeader]) -> int:
    """Check that headers link by hash and carry their proof of work.

    Parameters
    ----------
    headers : sequence of BlockHeader
        Consecutive headers, oldest first (not necessarily from genesis).

    Returns
    -------
    int
        The expected work they represent, the sum of ``2**difficulty``.

    Raises
    ------
    ValueError
        The list is empty, a header does not link to its predecessor, or a
        hash misses its target.

    Examples
    --------
    >>> import blockchainkit as bk
    >>> genesis = bk.consensus.mine(bk.structures.Block(difficulty=4)).block
    >>> bk.structures.verify_header_chain([genesis.to_header()])
    16
    """
    if not headers:
        raise ValueError("an empty header chain proves nothing")
    work = 0
    for index, header in enumerate(headers):
        if index and (
            header.previous_hash != headers[index - 1].hash
            or header.height != headers[index - 1].height + 1
        ):
            raise ValueError(f"header {index} does not link to its predecessor")
        if int.from_bytes(header.hash, "big") > target(header.difficulty):
            raise ValueError(f"header {index} misses its proof of work target")
        work += expected_trials(header.difficulty)
    return work
