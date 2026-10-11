"""Bridge failures of 2022: the Ronin and Wormhole exploits.

A bridge locks coins in a contract on one chain and issues wrapped coins on
another; to release the locked coins, the contract needs evidence that the
wrapped ones were burned. A light-client relay checks that evidence itself;
most bridges instead trust a committee of validators to sign it. The
contract is then exactly as safe as the committee's keys and the code that
checks their signatures, and in 2022 bridges lost more than two billion
dollars to failures of both.

**Ronin** (March 2022). The bridge of the Axie Infinity sidechain released
funds on 5 of 9 validator signatures. Sky Mavis ran four validators, and
had been allowed to sign for a fifth, the Axie DAO's, during a load spike
months before; the permission was never revoked. An attacker who
compromised Sky Mavis's systems held five keys, and withdrew 173,600 ether
and 25.5 million USDC.

**Wormhole** (February 2022). Wormhole's Solana program checked guardian
signatures in one instruction and then, in the next, trusted an account
saying that the check had passed. It took that account from the caller and
never verified that it was the genuine system account. The attacker passed
a forged one, minted 120,000 wrapped ether without any signature, and
redeemed most of it for ether held by the bridge.

Here both are contracts on :class:`~blockchainkit.contracts.systems.world.World`.
Solana's accounts become a caller-supplied verifier contract, and minting
and redeeming wrapped ether happen in one contract rather than on two chains.
"""

from collections.abc import Sequence
from typing import Any

from blockchainkit.channels.utils.scripts import PublicKey, key_pair, signature
from blockchainkit.constants import BRIDGE_DOMAIN
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.signatures import verify
from blockchainkit.structures.utils.encoding import canonical_json

Approval = tuple[PublicKey, SchnorrSignature]


def withdrawal_message(bridge: str, recipient: str, amount: int, nonce: int) -> bytes:
    """The bytes validators sign to release ``amount`` to ``recipient`` from ``bridge``."""
    return BRIDGE_DOMAIN + canonical_json([bridge, recipient, amount, nonce])


def sign_withdrawal(private: int, bridge: str, recipient: str, amount: int, nonce: int) -> Approval:
    """One validator's approval of a withdrawal: ``(public_key, signature)``.

    Examples
    --------
    >>> from blockchainkit.channels import sign_withdrawal
    >>> from blockchainkit.crypto import public_key
    >>> sign_withdrawal(7, "0xbridge", "alice", 10, 0)[0] == public_key(7)
    True
    """
    _, public = key_pair(private)
    return public, signature(private, withdrawal_message(bridge, recipient, amount, nonce))


def _signers(message: bytes, approvals: Sequence[Approval], members: Sequence[Any]) -> int:
    allowed = {(m[0], m[1]) for m in members}
    valid = {
        (key[0], key[1])
        for key, signed in approvals
        if (key[0], key[1]) in allowed and verify(message, signed, (key[0], key[1]))
    }
    return len(valid)


class ValidatorBridge(Contract):
    """Ronin's bridge: locked ether, released on ``threshold`` validator signatures.

    Constructor arguments: the validators' public keys and the threshold.

    Examples
    --------
    >>> from blockchainkit.channels import ValidatorBridge, sign_withdrawal
    >>> from blockchainkit.contracts import World
    >>> from blockchainkit.crypto import public_key
    >>> world = World()
    >>> world.fund("alice", 50)
    >>> keys = range(1, 10)
    >>> bridge = world.deploy("ronin", ValidatorBridge, [public_key(k) for k in keys], 5)
    >>> world.transact("alice", bridge, "deposit", value=50).success
    True
    >>> approvals = [sign_withdrawal(k, bridge, "alice", 50, 0) for k in (1, 2, 3, 4, 5)]
    >>> world.transact("relayer", bridge, "withdraw", "alice", 50, 0, approvals).success
    True
    """

    layout = ("validators", "threshold", "processed")

    def constructor(self, validators: Sequence[PublicKey], threshold: int) -> None:
        self.require(1 <= threshold <= len(validators), "threshold must be between 1 and n")
        self.write("validators", tuple((v[0], v[1]) for v in validators))
        self.write("threshold", threshold)

    def deposit(self) -> None:
        """Lock ether; the validators then mint as much on the other chain."""
        self.emit("Deposit", sender=self.sender, amount=self.value)

    def withdraw(
        self, recipient: str, amount: int, nonce: int, approvals: Sequence[Approval]
    ) -> None:
        """Release ``amount`` to ``recipient``, approved by enough distinct validators."""
        self.require(not self.read("processed", nonce), "withdrawal already processed")
        message = withdrawal_message(self.address, recipient, amount, nonce)
        signers = _signers(message, approvals, self.read("validators"))
        self.require(signers >= self.read("threshold"), "not enough validator signatures")
        self.write("processed", nonce, True)
        self.call(recipient, None, value=amount)


class GuardianVerifier(Contract):
    """Wormhole's signature-verification step: records messages enough guardians signed.

    Constructor arguments: the guardians' public keys and the threshold.
    """

    layout = ("guardians", "threshold", "verified")

    def constructor(self, guardians: Sequence[PublicKey], threshold: int) -> None:
        self.require(1 <= threshold <= len(guardians), "threshold must be between 1 and n")
        self.write("guardians", tuple((g[0], g[1]) for g in guardians))
        self.write("threshold", threshold)

    def verify_signatures(self, message: bytes, approvals: Sequence[Approval]) -> None:
        """Check the guardians' signatures on ``message`` and record its hash as verified."""
        signers = _signers(message, approvals, self.read("guardians"))
        self.require(signers >= self.read("threshold"), "not enough guardian signatures")
        self.write("verified", sha256(message), True)

    def is_verified(self, message_hash: bytes) -> bool:
        """True if the message with this hash passed :meth:`verify_signatures`."""
        return bool(self.read("verified", message_hash))


class ForgedVerifier(Contract):
    """The attacker's stand-in for the verification account: it vouches for everything."""

    def is_verified(self, message_hash: bytes) -> bool:
        return True


class WormholeBridge(Contract):
    """Wrapped ether minted on verified guardian messages, and redeemed for locked ether.

    Constructor arguments: the genuine verifier's address, and whether to
    check that the caller-supplied verifier is that one (the fix).
    """

    layout = ("verifier", "check_verifier", "wrapped", "processed")

    def constructor(self, verifier: str, check_verifier: bool) -> None:
        self.write("verifier", verifier)
        self.write("check_verifier", check_verifier)

    def deposit(self) -> None:
        """Lock ether, to be minted as wrapped ether on another chain."""
        self.emit("Deposit", sender=self.sender, amount=self.value)

    def complete_transfer(self, recipient: str, amount: int, nonce: int, verifier: str) -> None:
        """Mint wrapped ether for a transfer that ``verifier`` says the guardians signed.

        With ``check_verifier`` off, as in the vulnerable program, any
        contract can be passed as the verifier.
        """
        if self.read("check_verifier"):
            self.require(verifier == self.read("verifier"), "not the genuine verifier")
        message = withdrawal_message(self.address, recipient, amount, nonce)
        self.require(self.call(verifier, "is_verified", sha256(message)), "message not verified")
        self.require(not self.read("processed", nonce), "transfer already completed")
        self.write("processed", nonce, True)
        self.write("wrapped", recipient, self.read("wrapped", recipient) + amount)

    def redeem(self, amount: int) -> None:
        """Burn wrapped ether and receive as much locked ether."""
        balance = self.read("wrapped", self.sender)
        self.require(0 < amount <= balance, "not enough wrapped ether")
        self.write("wrapped", self.sender, balance - amount)
        self.call(self.sender, None, value=amount)

    def wrapped_balance(self, account: str) -> int:
        """Wrapped ether held by ``account``."""
        return int(self.read("wrapped", account))
