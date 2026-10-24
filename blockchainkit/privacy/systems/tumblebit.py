r"""TumbleBit: an untrusted payment hub that cannot link payers to payees (Heilman et al., 2017).

A *tumbler* mixes coins by receiving from payers and paying payees. A
centralised mixer can steal and can see who paid whom. TumbleBit removes
both risks with RSA puzzles. For each payee the tumbler issues a
*promise*: a puzzle :math:`z = \\epsilon^{e} \bmod N` and its payment token
encrypted under :math:`\\epsilon`. Only the tumbler, with its RSA secret,
can solve the puzzle. The payee *blinds* the puzzle,

.. math::

   z' = z \\cdot \rho^{e} \bmod N ,

and gives :math:`z'` to a payer, who pays the tumbler to solve it. The
tumbler returns :math:`\\epsilon \rho`, the payer passes it on, and the payee
divides by :math:`\rho` to get :math:`\\epsilon` and open its token. The
tumbler saw :math:`z` with the payee and :math:`z'` with the payer, which
are unrelated numbers to it: the same blinding as Chaum's blind signatures.

TumbleBit makes each step a fair exchange on chain, with hash-locked
escrows and cut-and-choose, so the tumbler cannot take a payment without
solving the puzzle or promise a token it does not deliver. This model
keeps only the puzzles and blinding, and the token is a byte string.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.constants import TUMBLER_DOMAIN
from blockchainkit.crypto.systems.asymmetric import RSAKeyPair, rsa_blind, rsa_keypair, rsa_unblind
from blockchainkit.privacy.core.base import PuzzlePromise, TumblerRun
from blockchainkit.privacy.utils.groups import keystream_xor

_SMALLER_FACTOR = 2_147_483_659
TUMBLER_KEY = rsa_keypair(_SMALLER_FACTOR, 2_148_483_661, 65_537)
"""RSAKeyPair: A 62-bit textbook RSA key for the tumbler's puzzles."""


class Tumbler:
    """The tumbler: promises puzzles to payees and sells their solutions to payers.

    It keeps the log a curious tumbler would keep: every puzzle it promised,
    and every puzzle it was paid to solve.

    Parameters
    ----------
    key : RSAKeyPair
        Its RSA key; the puzzles are under its public half.
    """

    def __init__(self, key: RSAKeyPair = TUMBLER_KEY) -> None:
        self.key = key
        self.promised: list[tuple[str, int]] = []
        self.solved: list[tuple[str, int]] = []

    def promise(self, payee: str, token: bytes, rng: Random) -> PuzzlePromise:
        """Lock ``token`` under a fresh puzzle for ``payee``."""
        epsilon = rng.randrange(2, self.key.n)
        puzzle = pow(epsilon, self.key.e, self.key.n)
        self.promised.append((payee, puzzle))
        return PuzzlePromise(puzzle, keystream_xor(epsilon, token, TUMBLER_DOMAIN))

    def solve(self, payer: str, puzzle: int) -> int:
        """Solve ``puzzle`` for a payer who paid for it: ``puzzle**d mod N``."""
        integer(puzzle, "puzzle")
        self.solved.append((payer, puzzle))
        return pow(puzzle, self.key.d, self.key.n)


def open_promise(promise: PuzzlePromise, solution: int) -> bytes:
    """Decrypt the token of ``promise`` with the puzzle's solution ``epsilon``."""
    return keystream_xor(solution, promise.sealed, TUMBLER_DOMAIN)


def run_tumbler(
    pairs: Sequence[tuple[str, str]], *, blind: bool = True, seed: int = 0
) -> TumblerRun:
    """Pay each ``(payer, payee)`` pair through one tumbler.

    With ``blind=False`` the payee hands its puzzle to the payer unblinded,
    and the tumbler's two logs match.
    """
    check_seed(seed)
    rng = Random(seed)
    tumbler = Tumbler()
    key = tumbler.key
    paid = []
    for payer, payee in pairs:
        token = f"pay {payee}".encode()
        promise = tumbler.promise(payee, token, rng)
        rho = rng.randrange(2, _SMALLER_FACTOR)  # Below both factors, so invertible mod N.
        handed = rsa_blind(promise.puzzle, rho, key) if blind else promise.puzzle
        answer = tumbler.solve(payer, handed)
        epsilon = rsa_unblind(answer, rho, key) if blind else answer
        paid.append(open_promise(promise, epsilon) == token)
    return TumblerRun(tuple(tumbler.promised), tuple(tumbler.solved), tuple(paid))


def tumbler_links(run: TumblerRun) -> tuple[tuple[str, str], ...]:
    """``(payer, payee)`` pairs the tumbler links because the same puzzle reached it twice."""
    payees: dict[int, str] = {puzzle: payee for payee, puzzle in run.promised}
    return tuple((payer, payees[puzzle]) for payer, puzzle in run.solved if puzzle in payees)
