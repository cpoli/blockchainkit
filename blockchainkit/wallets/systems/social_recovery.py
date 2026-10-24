r"""Social-recovery wallets (Buterin, 2021).

A single seed phrase is a single point of failure twice over: lose it and
the coins are gone, let it be copied and they are stolen. A social-recovery
wallet is a contract with one signing key for daily use and a set of
*guardians*, friends, devices or institutions, any m of whom can replace
the signing key. The owner need back up nothing, and a thief with the
signing key alone can be locked out by the guardians.

With n guardians, each independently lost with probability :math:`p_l`
or corrupt with probability :math:`p_c`, recovery fails when fewer than m
are honest, and the wallet is stolen when m are corrupt:

.. math::

   P(\text{theft}) = \sum_{j \ge m} \binom{n}{j} p_c^{\,j} (1 - p_c)^{n-j} .

Raising m trades theft for lockout. Changing the guardians is delayed, so a
thief who takes the signing key cannot replace them before they act.

Teaching differences: guardians are accounts that send transactions, not
signatures collected off chain, and the wallet holds only ether.
"""

from collections.abc import Sequence
from math import comb

from blockchainkit._validation import integer, probability
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.wallets.core.base import RecoveryRisk

GUARDIAN_DELAY = 100
"""int: Blocks between proposing new guardians and being able to apply them."""


def recovery_risk(guardians: int, threshold: int, lost: float, corrupt: float) -> RecoveryRisk:
    """The lockout and theft probabilities of m-of-n guardians failing independently.

    Parameters
    ----------
    guardians, threshold : int
        n and m.
    lost, corrupt : float
        Each guardian's probability of being unreachable, or of colluding
        against the owner; the rest are honest.

    Examples
    --------
    >>> from blockchainkit.wallets import recovery_risk
    >>> risk = recovery_risk(5, 3, lost=0.1, corrupt=0.05)
    >>> round(risk.lockout, 4), round(risk.theft, 5)
    (0.0266, 0.00116)
    """
    integer(threshold, "threshold", 1)
    integer(guardians, "guardians", threshold)
    probability(lost, "lost")
    probability(corrupt, "corrupt")
    if lost + corrupt > 1:
        raise ValueError("lost + corrupt is at most 1")
    honest = 1 - lost - corrupt
    lockout = sum(
        comb(guardians, j) * honest**j * (1 - honest) ** (guardians - j) for j in range(threshold)
    )
    theft = sum(
        comb(guardians, j) * corrupt**j * (1 - corrupt) ** (guardians - j)
        for j in range(threshold, guardians + 1)
    )
    return RecoveryRisk(lockout, theft)


class SocialRecoveryWallet(Contract):
    """A wallet with one owner and m-of-n guardians who can replace the owner.

    Parameters
    ----------
    owner : str
        The account allowed to spend.
    guardians : sequence of str
        Accounts allowed to vote for a new owner.
    threshold : int
        Votes needed.
    """

    layout = ("owner", "guardians", "threshold", "votes", "epoch", "pending")

    def constructor(self, owner: str, guardians: Sequence[str], threshold: int) -> None:
        self.write("owner", owner)
        self._set_guardians(guardians, threshold)

    def _set_guardians(self, guardians: Sequence[str], threshold: int) -> None:
        guardians = tuple(guardians)
        self.require(len(set(guardians)) == len(guardians), "guardians must be distinct")
        self.require(1 <= threshold <= len(guardians), "threshold must be between 1 and n")
        self.write("guardians", guardians)
        self.write("threshold", threshold)

    def receive(self) -> None:
        self.emit("Deposit", sender=self.sender, amount=self.value)

    def owner(self) -> str:
        """The account that may spend."""
        return str(self.read("owner"))

    def execute(self, to: str, amount: int) -> None:
        """Pay ``amount`` to ``to``; only the owner may."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.call(to, None, value=amount)

    def support_recovery(self, new_owner: str) -> bool:
        """A guardian's vote to make ``new_owner`` the owner; returns True once it takes effect.

        Votes count toward the current epoch only: a recovery, or a change
        of guardians, starts a new one.
        """
        self.require(self.sender in self.read("guardians"), "only a guardian")
        epoch = self.read("epoch")
        votes = set(self.read("votes", epoch, new_owner) or ()) | {self.sender}
        if len(votes) < self.read("threshold"):
            self.write("votes", epoch, new_owner, tuple(sorted(votes)))
            return False
        self.write("owner", new_owner)
        self.write("epoch", epoch + 1)
        self.write("pending", 0)  # A recovery cancels a guardian change the thief proposed.
        self.emit("Recovered", owner=new_owner)
        return True

    def propose_guardians(self, guardians: Sequence[str], threshold: int) -> None:
        """The owner proposes new guardians; they apply after :data:`GUARDIAN_DELAY` blocks."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.write("pending", (tuple(guardians), threshold, self.block_number))

    def apply_guardians(self) -> None:
        """Install the proposed guardians once the delay has passed."""
        self.require(self.sender == self.read("owner"), "only the owner")
        pending = self.read("pending")
        self.require(pending, "no guardian change is pending")
        guardians, threshold, proposed = pending
        self.require(self.block_number >= proposed + GUARDIAN_DELAY, "the delay has not passed")
        self._set_guardians(guardians, threshold)
        self.write("pending", 0)
        self.write("epoch", self.read("epoch") + 1)
