"""Multisig wallets behind a shared library: the two Parity incidents (2017).

Parity's multisig wallet kept its logic in one library contract, and each
wallet was a small stub that forwarded every unknown call to it with
``DELEGATECALL``, running the library's code on the wallet's own storage.

**July 2017.** The library's ``initWallet``, which sets the owners, had no
guard against being called twice, and the stub forwarded it like any other
call. An attacker called it on three wallets, made itself sole owner, and
withdrew about 153,000 ether.

**November 2017.** The fixed library could only be initialized once, but
the library contract itself had never been initialized. A user called
``initWallet`` on the library directly, became its owner, and called
``kill``, which ran ``selfdestruct``. Every wallet's ``DELEGATECALL`` now
reached an address with no code, which succeeds and does nothing: about
513,000 ether were frozen for good.

The wallets here are m-of-n: an action runs when enough owners have signed
it with this package's Schnorr signatures. Parity's owners instead
confirmed by sending transactions.
"""

from collections.abc import Sequence
from typing import Any

from blockchainkit.constants import WALLET_DOMAIN
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.curves import public_key
from blockchainkit.crypto.systems.signatures import deterministic_nonce, sign, verify
from blockchainkit.structures.utils.encoding import canonical_json

PublicKey = tuple[int, int]
Approval = tuple[PublicKey, SchnorrSignature]


def wallet_message(wallet: str, nonce: int, action: str, *params: Any) -> bytes:
    """The bytes an owner signs to approve ``action`` with ``params`` on ``wallet`` at ``nonce``.

    The wallet address and nonce make every approval single-use.
    """
    return WALLET_DOMAIN + canonical_json([wallet, nonce, action, list(params)])


def approve_action(
    private_key: int, wallet: str, nonce: int, action: str, *params: Any
) -> Approval:
    """Sign an action as one owner; returns ``(public_key, signature)``.

    Examples
    --------
    >>> from blockchainkit.contracts import approve_action
    >>> from blockchainkit.crypto import public_key
    >>> owner, signature = approve_action(7, "0xwallet", 0, "execute", "bob", 10)
    >>> owner == public_key(7)
    True
    """
    message = wallet_message(wallet, nonce, action, *params)
    signature = sign(message, private_key, nonce=deterministic_nonce(private_key, message))
    return public_key(private_key), signature


class WalletLibrary(Contract):
    """The shared m-of-n wallet logic, with Parity's July 2017 bug: anyone can re-initialize.

    Meant to run only through :class:`Wallet`'s ``DELEGATECALL``, on the
    wallet's storage.
    """

    layout = ("library", "owners", "threshold", "nonce")

    def init_wallet(self, owners: Sequence[PublicKey], threshold: int) -> None:
        """Set the owners and how many must sign. Nothing stops a second call."""
        self._initialize(owners, threshold)

    def _initialize(self, owners: Sequence[PublicKey], threshold: int) -> None:
        owners = tuple((owner[0], owner[1]) for owner in owners)
        self.require(1 <= threshold <= len(owners), "threshold must be between 1 and the owners")
        self.write("owners", owners)
        self.write("threshold", threshold)

    def _authorize(
        self, action: str, params: tuple[Any, ...], approvals: Sequence[Approval]
    ) -> None:
        nonce = self.read("nonce")
        message = wallet_message(self.address, nonce, action, *params)
        owners = self.read("owners") or ()
        signers = set()
        for owner, signature in approvals:
            owner = (owner[0], owner[1])
            if owner in owners and verify(message, signature, owner):
                signers.add(owner)
        self.require(
            threshold_met(len(signers), self.read("threshold")), "not enough owner signatures"
        )
        self.write("nonce", nonce + 1)

    def execute(self, to: str, amount: int, approvals: Sequence[Approval]) -> None:
        """Pay ``amount`` to ``to``, approved by enough owners."""
        self._authorize("execute", (to, amount), approvals)
        self.call(to, None, value=amount)

    def kill(self, beneficiary: str, approvals: Sequence[Approval]) -> None:
        """Self-destruct, sending the ether to ``beneficiary``, approved by enough owners."""
        self._authorize("kill", (beneficiary,), approvals)
        self.selfdestruct(beneficiary)

    def nonce(self) -> int:
        """Approvals must sign this nonce; it grows with every authorized action."""
        return int(self.read("nonce"))


def threshold_met(signers: int, threshold: int) -> bool:
    """True if ``signers`` distinct valid signatures meet a configured, nonzero ``threshold``."""
    return threshold > 0 and signers >= threshold


class PatchedWalletLibrary(WalletLibrary):
    """The July fix: ``init_wallet`` runs only on uninitialized storage, like the library's own."""

    def init_wallet(self, owners: Sequence[PublicKey], threshold: int) -> None:
        self.require(self.read("threshold") == 0, "already initialized")
        self._initialize(owners, threshold)


class Wallet(Contract):
    """A wallet stub: it holds the ether and storage, and delegates all logic to a library."""

    layout = WalletLibrary.layout

    def constructor(self, library: str, owners: Sequence[PublicKey], threshold: int) -> None:
        self.write("library", library)
        self.delegatecall(library, "init_wallet", owners, threshold)

    def receive(self) -> None:
        self.emit("Deposit", sender=self.sender, amount=self.value)

    def fallback(self, function: str | None, *args: Any) -> Any:
        return self.delegatecall(self.read("library"), function, *args)
