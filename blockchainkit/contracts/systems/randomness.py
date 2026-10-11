"""Randomness on a deterministic machine: block hashes and commit-reveal (2016).

Every node must compute the same result, so a contract has no private
source of randomness. Early lotteries drew from the previous block's hash,
but any contract called in the same block reads the same hash: an attacker
contract computes the winning number and plays only when it wins. (Miners
could also withhold blocks with unwelcome hashes.)

A *commit-reveal* scheme removes the shortcut. Each player first publishes
a hash of a secret with a random salt, then, after every commitment is in,
reveals the secret; the draw combines all of them. Nobody can choose a
secret after seeing the others, but the last player to reveal still sees
the outcome first and can refuse to reveal, a bias that verifiable delay
functions and RANDAO's penalties aim to remove.
"""

from blockchainkit.constants import CONTRACT_COMMIT_DOMAIN
from blockchainkit.contracts.systems.world import Contract
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.structures.utils.encoding import canonical_json

LOTTERY_OUTCOMES = 10
"""The block-hash lottery draws a number in ``range(10)``."""


def commitment(player: str, secret: int, salt: int) -> int:
    """Hash binding ``player`` to ``secret``; the salt stops a guess-and-check of small secrets.

    The player's address is hashed in, so that copying someone else's
    commitment does not let a second player reveal the same secret.

    Examples
    --------
    >>> from blockchainkit.contracts import commitment
    >>> commitment("alice", 7, 1) == commitment("alice", 7, 1) != commitment("bob", 7, 1)
    True
    """
    return int.from_bytes(
        sha256(CONTRACT_COMMIT_DOMAIN + canonical_json([player, secret, salt])), "big"
    )


class BlockhashLottery(Contract):
    """Pays the whole pot to a player who guesses ``blockhash(previous block) % 10``."""

    layout = ("stake",)

    def constructor(self, stake: int) -> None:
        self.write("stake", stake)

    def play(self, guess: int) -> bool:
        """Pay the stake and guess; win the pot if the guess is right."""
        self.require(self.value == self.read("stake"), "pay exactly the stake")
        drawn = self.blockhash(self.block_number - 1) % LOTTERY_OUTCOMES
        if guess != drawn:
            return False
        self.call(self.sender, None, value=self.ether_balance())
        return True


class LotteryPredictor(Contract):
    """Computes the block-hash lottery's draw in the same block, and plays only to win."""

    layout = ("owner",)

    def constructor(self) -> None:
        self.write("owner", self.sender)

    def attack(self, lottery: str, stake: int) -> bool:
        """Play ``lottery`` with the number it is about to draw."""
        guess = self.blockhash(self.block_number - 1) % LOTTERY_OUTCOMES
        won = self.call(lottery, "play", guess, value=stake)
        self.call(self.read("owner"), None, value=self.ether_balance())
        return bool(won)

    def receive(self) -> None:
        pass


class CommitRevealLottery(Contract):
    """A lottery drawn from every player's secret, committed first and revealed later.

    Players commit (paying the stake) until block ``commit_end``, reveal
    until ``reveal_end``, and anyone may then settle: the winner is player
    ``xor of revealed secrets % players``. A player who never reveals
    forfeits the stake.
    """

    layout = ("stake", "commit_end", "reveal_end", "players", "count", "commitments", "seed")

    def constructor(self, stake: int, commit_blocks: int, reveal_blocks: int) -> None:
        self.write("stake", stake)
        self.write("commit_end", self.block_number + commit_blocks)
        self.write("reveal_end", self.block_number + commit_blocks + reveal_blocks)

    def commit(self, digest: int) -> None:
        """Join with a :func:`commitment` and the stake, during the commit phase."""
        self.require(self.block_number <= self.read("commit_end"), "commit phase is over")
        self.require(self.value == self.read("stake"), "pay exactly the stake")
        self.require(self.read("commitments", self.sender) == 0, "already committed")
        count = self.read("count")
        self.write("players", count, self.sender)
        self.write("count", count + 1)
        self.write("commitments", self.sender, digest)

    def reveal(self, secret: int, salt: int) -> None:
        """Open the commitment, during the reveal phase."""
        number = self.block_number
        self.require(
            self.read("commit_end") < number <= self.read("reveal_end"), "not the reveal phase"
        )
        stored = self.read("commitments", self.sender)
        self.require(
            stored != 0 and stored == commitment(self.sender, secret, salt), "wrong secret"
        )
        self.write("commitments", self.sender, 1)  # Revealed: cannot reveal twice.
        self.write("seed", self.read("seed") ^ secret)

    def settle(self) -> str:
        """After the reveal phase, pay the pot to the drawn player and return it."""
        self.require(self.block_number > self.read("reveal_end"), "reveal phase not over")
        count = self.read("count")
        self.require(count > 0, "no players")
        winner = str(self.read("players", self.read("seed") % count))
        self.call(winner, None, value=self.ether_balance())
        return winner
