r"""Hierarchical deterministic wallets (Wuille, BIP32, 2012).

Early wallets drew every key at random, so a backup was stale as soon as
the next key was made. BIP32 derives a whole tree of secp256k1 keys from
one seed. An extended key is a key k with a 32-byte chain code c, and child
i comes from

.. math::

   I = \mathrm{HMAC\text{-}SHA512}(c,\ \mathrm{data}), \qquad
   k_i = I_L + k \bmod n, \qquad c_i = I_R,

where the data is the parent's compressed public key and i for a normal
child, or the private key and i for a *hardened* child, i >= 2**31.
Because :math:`k_i G = I_L G + K`, a normal child's public key follows from
the parent's public key alone: a shop can hold the extended public key and
make a fresh address for every order, with no private key on its server.

The price is that the extended public key and any one normal child's
private key reveal the parent's private key, :math:`k = k_i - I_L`. Hardened
children cut that link, which is why account keys are hardened.
"""

import hashlib
import hmac

from blockchainkit._validation import integer
from blockchainkit.constants import BIP32_SEED_KEY, HARDENED_OFFSET
from blockchainkit.crypto.systems.curves import SECP256K1, add, public_key
from blockchainkit.crypto.systems.hashing import hash256
from blockchainkit.wallets.core.base import ExtendedKey
from blockchainkit.wallets.systems.base58 import base58_encode, base58check_decode
from blockchainkit.wallets.utils.keys import compress, decompress
from blockchainkit.wallets.utils.ripemd160 import hash160

EXTENDED_KEY_VERSIONS = {"xprv": 0x0488ADE4, "xpub": 0x0488B21E}
"""dict: The 4-byte version prefixes of serialized mainnet extended keys."""

_N = SECP256K1.order


def _hmac512(key: bytes, data: bytes) -> tuple[int, bytes]:
    digest = hmac.new(key, data, hashlib.sha512).digest()
    return int.from_bytes(digest[:32], "big"), digest[32:]


def master_key(seed: bytes) -> ExtendedKey:
    """The master extended private key: HMAC-SHA512 of the seed under ``"Bitcoin seed"``.

    Parameters
    ----------
    seed : bytes
        16 to 64 bytes, such as a BIP39 seed.

    Examples
    --------
    >>> from blockchainkit.wallets import master_key
    >>> master = master_key(bytes(range(16)))  # BIP32 test vector 1
    >>> hex(master.private)[:10]
    '0xe8f32e72'
    """
    if not isinstance(seed, bytes) or not 16 <= len(seed) <= 64:
        raise ValueError("seed must be 16 to 64 bytes")
    key, chain_code = _hmac512(BIP32_SEED_KEY, seed)
    if not 0 < key < _N:
        raise ValueError("this seed gives an invalid master key; use another")  # p < 2**-127
    return ExtendedKey(chain_code, public_key(key), key, 0, 0, bytes(4))


def fingerprint(key: ExtendedKey) -> bytes:
    """The first 4 bytes of ``HASH160`` of the key's compressed public key."""
    return hash160(compress(key.public))[:4]


def derive_private(parent: ExtendedKey, index: int) -> ExtendedKey:
    """BIP32's CKDpriv: child ``index`` of an extended private key.

    Indices from ``2**31`` (written ``i'``) are hardened.
    """
    if parent.private is None:
        raise ValueError("deriving a private child needs the parent's private key")
    integer(index, "index")
    if index >= 2**32:
        raise ValueError("index is a 32-bit number")
    if index >= HARDENED_OFFSET:
        data = b"\x00" + parent.private.to_bytes(32, "big")
    else:
        data = compress(parent.public)
    tweak, chain_code = _hmac512(parent.chain_code, data + index.to_bytes(4, "big"))
    child = (tweak + parent.private) % _N
    if tweak >= _N or child == 0:
        raise ValueError("invalid child; BIP32 skips to the next index")  # p < 2**-127
    return ExtendedKey(
        chain_code, public_key(child), child, parent.depth + 1, index, fingerprint(parent)
    )


def derive_public(parent: ExtendedKey, index: int) -> ExtendedKey:
    """BIP32's CKDpub: child ``index``'s public key from the parent's public key alone.

    Raises
    ------
    ValueError
        ``index`` is hardened: that needs the private key.
    """
    integer(index, "index")
    if index >= HARDENED_OFFSET:
        raise ValueError("hardened children cannot be derived from a public key")
    data = compress(parent.public) + index.to_bytes(4, "big")
    tweak, chain_code = _hmac512(parent.chain_code, data)
    if tweak >= _N:
        raise ValueError("invalid child; BIP32 skips to the next index")  # p < 2**-127
    child = add(public_key(tweak), parent.public, SECP256K1)
    if child is None:
        raise ValueError("invalid child; BIP32 skips to the next index")  # p < 2**-127
    return ExtendedKey(chain_code, child, None, parent.depth + 1, index, fingerprint(parent))


def neuter(key: ExtendedKey) -> ExtendedKey:
    """The extended public key: the same key and chain code, without the private key."""
    return ExtendedKey(
        key.chain_code, key.public, None, key.depth, key.index, key.parent_fingerprint
    )


def serialize_extended_key(key: ExtendedKey) -> str:
    """The 78-byte serialization in Base58Check: ``xprv...`` or ``xpub...``.

    Examples
    --------
    >>> from blockchainkit.wallets import master_key, neuter, serialize_extended_key
    >>> serialize_extended_key(neuter(master_key(bytes(range(16)))))[:12]
    'xpub661MyMwA'
    """
    if key.private is None:
        version, body = EXTENDED_KEY_VERSIONS["xpub"], compress(key.public)
    else:
        version, body = EXTENDED_KEY_VERSIONS["xprv"], b"\x00" + key.private.to_bytes(32, "big")
    data = (
        version.to_bytes(4, "big")
        + bytes([key.depth])
        + key.parent_fingerprint
        + key.index.to_bytes(4, "big")
        + key.chain_code
        + body
    )
    return base58_encode(data + hash256(data)[:4])


def parse_extended_key(text: str) -> ExtendedKey:
    """Read an ``xprv`` or ``xpub`` string back into an extended key.

    Raises
    ------
    ValueError
        A bad checksum, length, version or key.
    """
    version_byte, rest = base58check_decode(text)
    data = bytes([version_byte]) + rest
    if len(data) != 78:
        raise ValueError("an extended key is 78 bytes")
    version = int.from_bytes(data[:4], "big")
    depth, parent, index = data[4], data[5:9], int.from_bytes(data[9:13], "big")
    chain_code, body = data[13:45], data[45:]
    if version == EXTENDED_KEY_VERSIONS["xprv"]:
        private = int.from_bytes(body[1:], "big")
        if body[0] != 0 or not 0 < private < _N:
            raise ValueError("not a valid private key")
        return ExtendedKey(chain_code, public_key(private), private, depth, index, parent)
    if version == EXTENDED_KEY_VERSIONS["xpub"]:
        return ExtendedKey(chain_code, decompress(body), None, depth, index, parent)
    raise ValueError("unknown extended-key version")


def recover_parent_private(parent: ExtendedKey, child_private: int, index: int) -> int:
    r"""The leaked-xpub attack: a parent's private key from its xpub and one child's key.

    For a normal (non-hardened) child, :math:`k = k_i - I_L \bmod n`, and
    :math:`I_L` needs only the parent's public key and chain code.

    Examples
    --------
    >>> from blockchainkit.wallets import derive_private, master_key, neuter
    >>> from blockchainkit.wallets import recover_parent_private
    >>> master = master_key(bytes(range(16)))
    >>> child = derive_private(master, 7)
    >>> recover_parent_private(neuter(master), child.private, 7) == master.private
    True
    """
    integer(child_private, "child_private", 1)
    integer(index, "index")
    if index >= HARDENED_OFFSET:
        raise ValueError("a hardened child does not reveal its parent")
    data = compress(parent.public) + index.to_bytes(4, "big")
    tweak, _ = _hmac512(parent.chain_code, data)
    return (child_private - tweak) % _N
