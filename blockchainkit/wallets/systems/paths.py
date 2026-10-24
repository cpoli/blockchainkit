r"""Multi-account derivation paths (Palatinus and Rusnak, BIP44, 2014).

BIP32 allows any tree; for one seed to restore the same wallet in another
program, the programs must agree on where keys sit. BIP44 fixes five levels,

.. math::

   m / 44' / \text{coin}' / \text{account}' / \text{change} / \text{index},

with hardened purpose, coin type (0 for Bitcoin, 60 for Ether) and account,
then a chain for receiving (0) or change (1) addresses, and the address
index. A restoring wallet cannot know how many addresses were used, so it
scans: on each account's receiving chain it derives addresses until 20 in a
row are unused (the gap limit), and it stops at the first unused account.
Coins sent to an address past a gap of 20 are safe but invisible.
"""

from collections.abc import Collection, Sequence

from blockchainkit._validation import integer
from blockchainkit.constants import HARDENED_OFFSET
from blockchainkit.wallets.core.base import AccountScan, ExtendedKey
from blockchainkit.wallets.systems.base58 import p2pkh_address
from blockchainkit.wallets.systems.hd import derive_private, derive_public, neuter

GAP_LIMIT = 20
"""int: Unused addresses in a row after which BIP44 discovery stops."""


def parse_path(path: str) -> tuple[int, ...]:
    """Turn ``"m/44'/0'/0'/0/5"`` into child indices, hardened ones offset by ``2**31``.

    ``'`` and ``h`` both mark a hardened index.

    Examples
    --------
    >>> from blockchainkit.wallets import parse_path
    >>> parse_path("m/44'/0'/0'/0/5")
    (2147483692, 2147483648, 2147483648, 0, 5)
    """
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    parts = path.split("/")
    if parts[0] != "m":
        raise ValueError("a path starts with m")
    indices = []
    for part in parts[1:]:
        hardened = part.endswith(("'", "h"))
        digits = part[:-1] if hardened else part
        if not digits.isascii() or not digits.isdigit() or int(digits) >= HARDENED_OFFSET:
            raise ValueError(f"bad path component {part!r}")
        indices.append(int(digits) + (HARDENED_OFFSET if hardened else 0))
    return tuple(indices)


def format_path(indices: Sequence[int]) -> str:
    """Write child indices as a path, hardened ones with ``'``."""
    parts = ["m"]
    for index in indices:
        integer(index, "index")
        if index >= 2 * HARDENED_OFFSET:
            raise ValueError("index is a 32-bit number")
        hardened = index >= HARDENED_OFFSET
        parts.append(f"{index - HARDENED_OFFSET}'" if hardened else str(index))
    return "/".join(parts)


def derive_path(key: ExtendedKey, path: str) -> ExtendedKey:
    """Derive the key at ``path`` below ``key``.

    An extended public key can follow only normal (non-hardened) steps.

    Examples
    --------
    >>> from blockchainkit.wallets import derive_path, master_key, serialize_extended_key
    >>> key = derive_path(master_key(bytes(range(16))), "m/0'/1")
    >>> serialize_extended_key(key)[:12]
    'xprv9wTYmMFd'
    """
    for index in parse_path(path):
        key = derive_private(key, index) if key.is_private else derive_public(key, index)
    return key


def bip44_path(coin: int, account: int, change: int, index: int) -> str:
    """The BIP44 path ``m/44'/coin'/account'/change/index``."""
    for value, name in ((coin, "coin"), (account, "account"), (index, "index")):
        integer(value, name)
    if change not in (0, 1):
        raise ValueError("change is 0 (receiving) or 1 (change)")
    return f"m/44'/{coin}'/{account}'/{change}/{index}"


def discover_accounts(
    master: ExtendedKey,
    used: Collection[str],
    *,
    coin: int = 0,
    gap_limit: int = GAP_LIMIT,
    max_accounts: int = 10,
) -> AccountScan:
    """Restore a wallet from its master key by BIP44 account discovery.

    Parameters
    ----------
    master : ExtendedKey
        The master extended private key.
    used : collection of str
        The addresses that have appeared on the chain (P2PKH, compressed).
    coin : int
        The coin type.
    gap_limit : int
        Unused receiving addresses in a row that end an account's scan.
    max_accounts : int
        A bound on the accounts scanned.

    Examples
    --------
    >>> from blockchainkit.wallets import derive_path, discover_accounts, master_key, p2pkh_address
    >>> master = master_key(bytes(range(16)))
    >>> used = {p2pkh_address(derive_path(master, "m/44'/0'/0'/0/1").public)}
    >>> discover_accounts(master, used, gap_limit=3).found
    ("m/44'/0'/0'/0/1",)
    """
    integer(gap_limit, "gap_limit", 1)
    integer(max_accounts, "max_accounts", 1)
    found: list[str] = []
    derived = accounts = 0
    for account in range(max_accounts):
        chain = neuter(derive_path(master, f"m/44'/{coin}'/{account}'/0"))
        gap, index, any_used = 0, 0, False
        while gap < gap_limit:
            derived += 1
            if p2pkh_address(derive_public(chain, index).public) in used:
                found.append(bip44_path(coin, account, 0, index))
                gap, any_used = 0, True
            else:
                gap += 1
            index += 1
        if not any_used:
            break
        accounts += 1
    return AccountScan(accounts, tuple(found), derived)
