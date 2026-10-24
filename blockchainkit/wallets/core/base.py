"""Result containers for blockchainkit.wallets."""

from dataclasses import dataclass
from typing import Any

from blockchainkit.constants import HARDENED_OFFSET
from blockchainkit.crypto.core.base import SchnorrSignature


@dataclass(frozen=True)
class BCHDecoding:
    """What a BCH decoder made of a received word.

    Attributes
    ----------
    message : tuple of int
        The k message bits read from the corrected word.
    codeword : tuple of int
        The n-bit codeword after correction (the received word if nothing
        could be corrected).
    errors : tuple of int
        Positions flipped back, counted from the left.
    corrected : bool
        False if the decoder found more errors than it can correct; the
        word is then returned unchanged. True does not prove the word is
        right: beyond t errors the decoder can land on a wrong codeword.
    """

    message: tuple[int, ...]
    codeword: tuple[int, ...]
    errors: tuple[int, ...]
    corrected: bool


@dataclass(frozen=True)
class DetectionRates:
    """The share of typing errors a check-digit scheme catches.

    Attributes
    ----------
    scheme : str
        The scheme's name.
    single_errors : float
        Share of single wrong digits detected.
    transpositions : float
        Share of swaps of two adjacent, different digits detected.
    """

    scheme: str
    single_errors: float
    transpositions: float


@dataclass(frozen=True)
class CrackResult:
    """An exhaustive search for a short secret behind a stretched key.

    Attributes
    ----------
    secret : str or None
        The secret found, or None if no candidate matched.
    guesses : int
        Candidates tried.
    hash_calls : int
        Calls to the underlying keyed hash (HMAC), the attacker's real cost.
    """

    secret: str | None
    guesses: int
    hash_calls: int


@dataclass(frozen=True)
class RomixCost:
    """What one run of scrypt's ROMix cost, with some of its table forgotten.

    Attributes
    ----------
    n : int
        The cost parameter: the table has ``n`` entries.
    r : int
        The block size parameter: each entry is ``128 * r`` bytes.
    stored : int
        Table entries kept in memory.
    block_mixes : int
        Calls to BlockMix, the unit of time.
    """

    n: int
    r: int
    stored: int
    block_mixes: int

    @property
    def memory(self) -> int:
        """Bytes of table kept."""
        return 128 * self.r * self.stored


@dataclass(frozen=True)
class ExtendedKey:
    """A BIP32 extended key: a key and its chain code, and where it sits in the tree.

    Attributes
    ----------
    chain_code : bytes
        32 bytes of extra entropy that, with the key, derive the children.
    public : tuple of int
        The public key point.
    private : int or None
        The private key, or None for an extended public key.
    depth : int
        0 for the master key, 1 for its children, and so on.
    index : int
        This key's child number; at least ``2**31`` if hardened.
    parent_fingerprint : bytes
        The first 4 bytes of the parent's ``HASH160``; zeros for the master.
    """

    chain_code: bytes
    public: tuple[int, int]
    private: int | None
    depth: int
    index: int
    parent_fingerprint: bytes

    @property
    def hardened(self) -> bool:
        """True if this key was derived with a hardened index."""
        return self.index >= HARDENED_OFFSET

    @property
    def is_private(self) -> bool:
        """True if the private key is known."""
        return self.private is not None


@dataclass(frozen=True)
class AccountScan:
    """The outcome of BIP44 account discovery.

    Attributes
    ----------
    accounts : int
        Accounts found with at least one used address.
    found : tuple of str
        Paths of the used addresses found, in scan order.
    derived : int
        Addresses derived and checked.
    """

    accounts: int
    found: tuple[str, ...]
    derived: int


@dataclass(frozen=True)
class BrainDrain:
    """A simulated population of brain wallets, and the thieves sweeping them.

    Attributes
    ----------
    wallets : int
        Wallets funded.
    weak : int
        Wallets whose passphrase came from the common phrasebook.
    drained : int
        Wallets emptied by a thief.
    delays : tuple of int
        For each drained wallet, the blocks between deposit and theft.
    hauls : tuple of int
        Wallets taken by each thief, in the order the thieves were given.
    """

    wallets: int
    weak: int
    drained: int
    delays: tuple[int, ...]
    hauls: tuple[int, ...]


@dataclass(frozen=True)
class Bech32Decoding:
    """A decoded Bech32 or Bech32m string.

    Attributes
    ----------
    hrp : str
        The human-readable part, in lower case (``"bc"`` for Bitcoin).
    data : tuple of int
        The 5-bit values of the data part, checksum removed.
    encoding : str
        ``"bech32"`` or ``"bech32m"``: which checksum constant matched.
    """

    hrp: str
    data: tuple[int, ...]
    encoding: str


@dataclass(frozen=True)
class WitnessProgram:
    """A segregated-witness output: a version and a program.

    Attributes
    ----------
    version : int
        0 to 16; version 0 is P2WPKH or P2WSH, version 1 Taproot.
    program : bytes
        2 to 40 bytes: a key or script hash, or a Taproot key.
    """

    version: int
    program: bytes


@dataclass(frozen=True)
class EcdsaSignature:
    """An ECDSA signature: the x coordinate of the nonce point, and the response.

    Attributes
    ----------
    r, s : int
        Both in [1, n); ``s`` is normalized to the lower half, as Bitcoin requires.
    """

    r: int
    s: int


@dataclass(frozen=True)
class KeyShares:
    """A secp256k1 key generated jointly, held as Shamir shares.

    Attributes
    ----------
    public : tuple of int
        The joint public key. Its private key was never computed by anyone.
    threshold : int
        Shares needed to sign.
    shares : tuple of tuple
        Each party's ``(index, share)``.
    commitments : tuple of tuple
        Each dealer's Feldman commitments to its polynomial's coefficients.
    """

    public: tuple[int, int]
    threshold: int
    shares: tuple[tuple[int, int], ...]
    commitments: tuple[tuple[tuple[int, int], ...], ...]


@dataclass(frozen=True)
class ThresholdSigning:
    """An ECDSA signature produced jointly by a threshold of key holders.

    Attributes
    ----------
    signature : EcdsaSignature
        An ordinary ECDSA signature under the joint public key.
    signers : tuple of int
        The parties that took part.
    conversions : int
        Multiplicative-to-additive conversions run, each a two-party
        protocol: the price of ECDSA's nonlinearity.
    """

    signature: EcdsaSignature
    signers: tuple[int, ...]
    conversions: int


@dataclass(frozen=True)
class RecoveryRisk:
    """How a guardian scheme fails: by locking its owner out, or by robbing them.

    Attributes
    ----------
    lockout : float
        Probability that fewer than the threshold of guardians are honest
        and reachable, so that a lost key cannot be replaced.
    theft : float
        Probability that at least the threshold of guardians are corrupt,
        and can take the wallet.
    """

    lockout: float
    theft: float


@dataclass(frozen=True)
class UserOperation:
    """An ERC-4337 user operation: what an account owner asks its account to do.

    Attributes
    ----------
    sender : str
        The smart account that will run it.
    nonce : int
        The account's operation counter, so that each operation runs once.
    function : str
        The account function to call, such as ``"execute"``.
    args : tuple
        Its arguments.
    fee : int
        Ether the account pays the bundler, a stand-in for gas times gas price.
    signature : SchnorrSignature or None
        The owner's signature over the operation's hash; None until signed.
    """

    sender: str
    nonce: int
    function: str
    args: tuple[Any, ...]
    fee: int
    signature: SchnorrSignature | None = None
