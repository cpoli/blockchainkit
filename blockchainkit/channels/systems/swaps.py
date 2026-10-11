"""Atomic cross-chain swaps (Tier Nolan, 2013).

Alice has coins on chain A and wants Bob's coins on chain B, and neither
trusts the other to pay second. Tier Nolan's protocol makes the exchange
all-or-nothing with one secret and two hash time-locked contracts (HTLCs).
Alice picks a secret ``s`` and locks her coins on A to Bob, payable against
the preimage of ``h = SHA256(s)``, refundable to her after ``T_A``. Bob,
seeing that lock, locks his coins on B to Alice against the same ``h``,
refundable after ``T_B``. Alice claims on B by revealing ``s``, which Bob
then reads from chain B and uses to claim on A.

The timeouts must satisfy ``T_A > T_B`` with a margin: Alice must reveal
``s`` before ``T_B`` to be paid, and Bob then has until ``T_A`` to use it.
With the order reversed, Alice can take her refund on A and still claim on
B before Bob's refund unlocks, and Bob loses.
"""

from blockchainkit._validation import integer
from blockchainkit.channels.core.base import SwapOutcome
from blockchainkit.channels.utils.scripts import channel_message, key_pair, signature
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.vm.systems.script import (
    ScriptItem,
    encode_signature,
    htlc_locking,
    verify_script,
)


class AtomicSwap:
    """Alice's ``amount_a`` on chain A for Bob's ``amount_b`` on chain B.

    Both chains share one block height in this model. Each claim and refund
    is a spend of an HTLC output judged by
    :func:`~blockchainkit.vm.systems.script.verify_script`.

    Parameters
    ----------
    alice_key, bob_key : int
        The parties' private keys.
    secret : bytes
        Alice's preimage.
    amount_a, amount_b : int
        The coins each party locks.
    timeout_a, timeout_b : int
        Refund heights of Alice's lock on A and Bob's lock on B.

    Examples
    --------
    >>> from blockchainkit.channels import AtomicSwap
    >>> swap = AtomicSwap(7, 5, b"s3cret", amount_a=10, amount_b=3, timeout_a=48, timeout_b=24)
    >>> swap.lock_bob()
    >>> swap.claim_b(height=5), swap.claim_a(height=6)
    (True, True)
    >>> swap.outcome().completed
    True
    """

    def __init__(
        self,
        alice_key: int,
        bob_key: int,
        secret: bytes,
        *,
        amount_a: int,
        amount_b: int,
        timeout_a: int,
        timeout_b: int,
    ) -> None:
        if not isinstance(secret, bytes):
            raise TypeError("secret must be bytes")
        integer(amount_a, "amount_a", 1)
        integer(amount_b, "amount_b", 1)
        integer(timeout_a, "timeout_a", 1)
        integer(timeout_b, "timeout_b", 1)
        self._alice, self._alice_public = key_pair(alice_key, "alice_key")
        self._bob, self._bob_public = key_pair(bob_key, "bob_key")
        self._secret = secret
        self.payment_hash = sha256(secret)
        self.amounts = (amount_a, amount_b)
        self.timeouts = (timeout_a, timeout_b)
        # Alice locks first, so her lock on chain A exists from the start.
        self.lock_a: tuple[ScriptItem, ...] = htlc_locking(
            self.payment_hash, self._bob_public, self._alice_public, timeout_a
        )
        self.lock_b: tuple[ScriptItem, ...] | None = None
        self.revealed: bytes | None = None
        self.spent: dict[str, str] = {}

    def lock_bob(self) -> None:
        """Bob, having seen Alice's lock, locks his coins on B to Alice against the same hash."""
        if self.lock_b is not None:
            raise ValueError("Bob has already locked")
        self.lock_b = htlc_locking(
            self.payment_hash, self._alice_public, self._bob_public, self.timeouts[1]
        )

    def _spend(self, chain: str, by: str, branch: tuple[ScriptItem, ...], height: int) -> bool:
        integer(height, "height")
        lock = self.lock_a if chain == "A" else self.lock_b
        if lock is None or chain in self.spent:
            return False
        message = channel_message("swap", self.payment_hash.hex(), chain, by)
        key = self._alice if by == "alice" else self._bob
        unlocking = (encode_signature(signature(key, message)), *branch)
        if not verify_script(unlocking, lock, message=message, locktime=height).valid:
            return False
        self.spent[chain] = by
        return True

    def claim_b(self, *, height: int) -> bool:
        """Alice claims Bob's coins on B, revealing the secret on chain B."""
        claimed = self._spend("B", "alice", (self._secret, "OP_TRUE"), height)
        if claimed:
            self.revealed = self._secret
        return claimed

    def claim_a(self, *, height: int) -> bool:
        """Bob claims Alice's coins on A, if the secret has appeared on chain B."""
        if self.revealed is None:
            return False
        return self._spend("A", "bob", (self.revealed, "OP_TRUE"), height)

    def refund_a(self, *, height: int) -> bool:
        """Alice takes her coins on A back; Script accepts it from ``timeout_a``."""
        return self._spend("A", "alice", ("OP_FALSE",), height)

    def refund_b(self, *, height: int) -> bool:
        """Bob takes his coins on B back; Script accepts it from ``timeout_b``."""
        return self._spend("B", "bob", ("OP_FALSE",), height)

    def outcome(self) -> SwapOutcome:
        """Coins each party has received on A and B so far."""
        received = {"alice": [0, 0], "bob": [0, 0]}
        for index, chain in enumerate("AB"):
            if chain in self.spent:
                received[self.spent[chain]][index] = self.amounts[index]
        alice, bob = received["alice"], received["bob"]
        return SwapOutcome((alice[0], alice[1]), (bob[0], bob[1]), self.revealed is not None)
