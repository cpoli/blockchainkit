"""Chaum's mix-nets: untraceable mail from layered encryption and shuffling (1981).

A sender who wants to hide who it writes to encrypts its message for the
recipient, then for the last mix, then for the one before, like nested
envelopes. Each mix removes one layer, which tells it only the next hop.
It collects a *batch* of messages, removes their layers, and sends them on
in a random order. An observer of every wire sees messages go in and come
out, but the layers change their bytes and the shuffle changes their order,
so it cannot match them. One honest mix in the cascade is enough.

Each layer here is hashed ElGamal in the teaching group: a fresh
``R = g**k``, and the plaintext XORed with a keystream from the shared
``R**x = X**k``. Chaum used RSA and padded every message to one length;
these layers grow by the hop name and 8 bytes each.
"""

from collections.abc import Sequence
from random import Random

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.constants import MIX_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.privacy.core.base import MixRun
from blockchainkit.privacy.utils.groups import keystream_xor

_WIDTH = 8


def _encode(hop: str, inner: bytes) -> bytes:
    name = hop.encode()
    return len(name).to_bytes(2, "big") + name + inner


def _decode(plain: bytes) -> tuple[str, bytes]:
    size = int.from_bytes(plain[:2], "big")
    return plain[2 : 2 + size].decode(), plain[2 + size :]


def seal(plain: bytes, public: int, ephemeral: int, group: DHGroup = TEACHING_GROUP) -> bytes:
    """Encrypt ``plain`` to the holder of ``public`` with the one-time secret ``ephemeral``.

    >>> from blockchainkit.privacy import MixNode, seal
    >>> node = MixNode("m", 1234)
    >>> node.open(seal(b"hi", node.public, 99))
    b'hi'
    """
    integer(ephemeral, "ephemeral", 1)
    shared = pow(public, ephemeral, group.p)
    announce = pow(group.g, ephemeral, group.p)
    return announce.to_bytes(_WIDTH, "big") + keystream_xor(shared, plain, MIX_DOMAIN)


class MixNode:
    """A mix (or an onion router): a named key pair that removes one layer at a time.

    Parameters
    ----------
    name : str
        The address other nodes send to.
    secret : int
        Its private key, in ``[1, q)``.
    group : DHGroup
        The group of the keys.
    """

    def __init__(self, name: str, secret: int, group: DHGroup = TEACHING_GROUP) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        self.name = name
        self.group = group
        self.public = group.public(secret)
        self._secret = secret

    def open(self, sealed: bytes) -> bytes:
        """Remove the encryption of :func:`seal`.

        Raises
        ------
        ValueError
            The announced key is not in the group: the message was not
            sealed for any key.
        """
        p, q = self.group.p, self.group.q
        announce = int.from_bytes(sealed[:_WIDTH], "big")
        if not 1 < announce < p or pow(announce, q, p) != 1:
            raise ValueError("malformed layer")
        return keystream_xor(pow(announce, self._secret, p), sealed[_WIDTH:], MIX_DOMAIN)

    def peel(self, onion: bytes) -> tuple[str, bytes]:
        """Remove one layer and return ``(next hop, what to send it)``."""
        return _decode(self.open(onion))


def wrap(
    message: bytes,
    route: Sequence[MixNode],
    recipient: str,
    rng: Random,
    group: DHGroup = TEACHING_GROUP,
) -> bytes:
    """Wrap ``message`` for ``recipient`` in one layer per node of ``route``, innermost last.

    Only the nodes' names and public keys are used, as a sender would know them.

    Examples
    --------
    >>> from random import Random
    >>> from blockchainkit.privacy import MixNode, wrap
    >>> route = [MixNode("m1", 11), MixNode("m2", 22)]
    >>> onion = wrap(b"hello", route, "bob", Random(0))
    >>> hop, inner = route[0].peel(onion)
    >>> hop, route[1].peel(inner)
    ('m2', ('bob', b'hello'))
    """
    if not route:
        raise ValueError("the route needs at least one node")
    onion = message
    hops = [node.name for node in route[1:]] + [recipient]
    for node, hop in zip(reversed(route), reversed(hops), strict=True):
        onion = seal(_encode(hop, onion), node.public, rng.randrange(1, group.q), group)
    return onion


def mix_cascade(onions: Sequence[bytes], mixes: Sequence[MixNode], *, seed: int = 0) -> MixRun:
    """Send a batch of onions through a cascade of mixes, each shuffling its output.

    Every onion must be wrapped for exactly this cascade.

    Raises
    ------
    ValueError
        An onion's next hop is not the next mix of the cascade.
    """
    check_seed(seed)
    if not mixes:
        raise ValueError("the cascade needs at least one mix")
    rng = Random(seed)
    batch = tuple(onions)
    batches, permutations = [batch], []
    hops: list[str] = []
    for k, mix in enumerate(mixes):
        peeled = [mix.peel(onion) for onion in batch]
        if k + 1 < len(mixes) and any(hop != mixes[k + 1].name for hop, _ in peeled):
            raise ValueError(f"an onion leaving {mix.name} is not addressed to the next mix")
        order = list(range(len(batch)))
        rng.shuffle(order)
        permutations.append(tuple(order))
        hops = [peeled[i][0] for i in order]
        batch = tuple(peeled[i][1] for i in order)
        batches.append(batch)
    return MixRun(tuple(batches), tuple(permutations), tuple(zip(hops, batch, strict=True)))
