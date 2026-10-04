"""The unspent-transaction-output (UTXO) model of Bitcoin (2008).

There are no accounts. Value lives in *coins*, outputs of earlier
transactions, each owned by an address. A transaction consumes whole coins
as inputs and creates new ones as outputs; any value not assigned to an
output is the miner's fee. A coin can be spent once: double spending is
the attempt to use one input twice.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

from blockchainkit._validation import integer
from blockchainkit.constants import UINT64_LIMIT, UTXO_DOMAIN
from blockchainkit.crypto.core.base import SchnorrSignature
from blockchainkit.crypto.systems.curves import public_key
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.signatures import deterministic_nonce, sign, verify
from blockchainkit.structures.core.base import Coin, OutPoint
from blockchainkit.structures.systems.transaction import address
from blockchainkit.structures.utils.accounts import is_account_id
from blockchainkit.structures.utils.encoding import canonical_json


@dataclass(frozen=True)
class UTXOTransaction:
    """Spend whole coins and create new ones.

    Parameters
    ----------
    inputs : tuple of OutPoint
        Coins to consume, each at most once.
    outputs : tuple
        ``(owner_address, amount)`` pairs; amounts are positive integers.
    witnesses : tuple
        One ``(public_key, SchnorrSignature)`` per input, added by
        :meth:`signed`.
    """

    inputs: tuple[OutPoint, ...]
    outputs: tuple[tuple[str, int], ...]
    witnesses: tuple[tuple[tuple[int, int], SchnorrSignature], ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.inputs or not self.outputs:
            raise ValueError("a transaction needs inputs and outputs")
        if len(set(self.inputs)) != len(self.inputs):
            raise ValueError("an input cannot be listed twice")
        for owner, amount in self.outputs:
            if not is_account_id(owner):
                raise ValueError("output owners must be account identifiers")
            integer(amount, "amount", 1)
            if amount >= UINT64_LIMIT:
                raise ValueError("amounts must fit unsigned 64-bit integers")

    def payload(self) -> bytes:
        """Return the bytes each input's owner signs."""
        return canonical_json(
            {
                "domain": UTXO_DOMAIN,
                "inputs": [[i.txid.hex(), i.index] for i in self.inputs],
                "outputs": [list(o) for o in self.outputs],
            }
        )

    @property
    def txid(self) -> bytes:
        """Return the hash of the unsigned payload; outputs are named by it."""
        return sha256(self.payload())

    def signed(self, privates: Sequence[int]) -> "UTXOTransaction":
        """Return a copy with one signature per input, keys given in input order.

        Each witness is the signer's public key and a Schnorr signature over
        :meth:`payload` with an RFC 6979 nonce. Whether the key owns the coin
        is checked by :meth:`UTXOSet.apply`.
        """
        if len(privates) != len(self.inputs):
            raise ValueError("give exactly one private key per input")
        payload = self.payload()
        witnesses = tuple(
            (public_key(x), sign(payload, x, nonce=deterministic_nonce(x, payload)))
            for x in privates
        )
        return replace(self, witnesses=witnesses)

    def fee(self, utxos: "UTXOSet") -> int:
        """Return inputs minus outputs: what the miner may claim."""
        return sum(utxos[i].amount for i in self.inputs) - sum(a for _, a in self.outputs)


class UTXOSet:
    """An immutable set of unspent coins; applying a transaction returns a new set.

    Examples
    --------
    >>> import blockchainkit as bk
    >>> alice = bk.structures.address(bk.crypto.public_key(7))
    >>> bk.structures.UTXOSet.genesis({alice: 50}).balance(alice)
    50
    """

    def __init__(self, coins: Mapping[OutPoint, Coin]) -> None:
        self._coins = dict(coins)

    @classmethod
    def genesis(cls, allocations: Mapping[str, int]) -> "UTXOSet":
        """Create one coin per address from an initial allocation."""
        coins = {}
        for index, (owner, amount) in enumerate(sorted(allocations.items())):
            coins[OutPoint(sha256(b"genesis"), index)] = Coin(owner, amount)
        return cls(coins)

    def __getitem__(self, outpoint: OutPoint) -> Coin:
        return self._coins[outpoint]

    def __contains__(self, outpoint: object) -> bool:
        return outpoint in self._coins

    def __len__(self) -> int:
        return len(self._coins)

    def __repr__(self) -> str:
        return f"UTXOSet(coins={len(self)}, total={sum(c.amount for c in self._coins.values())})"

    def coins_of(self, owner: str) -> tuple[OutPoint, ...]:
        """Return the outpoints of every coin an address owns, sorted."""
        return tuple(sorted(o for o, coin in self._coins.items() if coin.owner == owner))

    def balance(self, owner: str) -> int:
        """Return the total value of an address's coins (a wallet's view)."""
        return sum(self._coins[o].amount for o in self.coins_of(owner))

    def apply(self, tx: UTXOTransaction) -> "UTXOSet":
        """Validate a transaction and return the set after it.

        Raises
        ------
        ValueError
            An input is spent or unknown, a witness is missing or does not
            match the coin's owner, or outputs exceed inputs.
        """
        if len(tx.witnesses) != len(tx.inputs):
            raise ValueError("every input needs a signature")
        for outpoint, (key, signature) in zip(tx.inputs, tx.witnesses, strict=True):
            if outpoint not in self._coins:
                raise ValueError(f"{outpoint} is not an unspent output")
            owner = self._coins[outpoint].owner
            if address(key) != owner or not verify(tx.payload(), signature, key):
                raise ValueError(f"bad signature for {outpoint}")
        if tx.fee(self) < 0:
            raise ValueError("outputs exceed inputs")
        coins = {o: c for o, c in self._coins.items() if o not in tx.inputs}
        for index, (owner, amount) in enumerate(tx.outputs):
            coins[OutPoint(tx.txid, index)] = Coin(owner, amount)
        return UTXOSet(coins)
