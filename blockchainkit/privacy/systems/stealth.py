"""Stealth addresses: one published address, a fresh key for every payment (CryptoNote, 2013).

Reusing an address links every payment to it; asking each payer for a new
one needs a conversation. CryptoNote, the protocol behind Monero, lets the
payer derive a fresh one-time key from a single published address
:math:`(A, B) = (g^a, g^b)`. The payer picks :math:`r`, publishes
:math:`R = g^r` with the transaction, and pays to

.. math::

   P = g^{H(A^r)} B .

Only the payee can recognise it, since :math:`A^r = R^a` needs either
:math:`r` or :math:`a`, and only the payee can spend it, with the key
:math:`x = H(R^a) + b`. The *view key* :math:`a` alone finds incoming
payments without being able to spend them, so it can be handed to an
auditor. To everyone else, the outputs paid to one address look unrelated.

CryptoNote hashes the output's index in the transaction along with
:math:`R^a`; here the index is an argument, 0 by default.
"""

from blockchainkit._validation import integer
from blockchainkit.constants import STEALTH_DOMAIN
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP, DHGroup
from blockchainkit.privacy.core.base import StealthKeys, StealthOutput
from blockchainkit.privacy.utils.groups import hash_to_scalar


def stealth_keys(
    view_secret: int, spend_secret: int, group: DHGroup = TEACHING_GROUP
) -> StealthKeys:
    """A wallet's view and spend key pairs; the two public keys form its address.

    >>> from blockchainkit.privacy import stealth_keys
    >>> keys = stealth_keys(5, 7)
    >>> keys.view_public != keys.spend_public
    True
    """
    return StealthKeys(
        view_secret, spend_secret, group.public(view_secret), group.public(spend_secret)
    )


def _scalar(shared: int, index: int, group: DHGroup) -> int:
    return hash_to_scalar(STEALTH_DOMAIN, shared, index, group=group)


def stealth_payment(
    view_public: int,
    spend_public: int,
    ephemeral: int,
    *,
    index: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> StealthOutput:
    """Pay the address ``(A, B)`` at a one-time key, using the payer's secret ``r``.

    Examples
    --------
    >>> from blockchainkit.privacy import owns_output, stealth_keys, stealth_payment
    >>> bob = stealth_keys(5, 7)
    >>> output = stealth_payment(bob.view_public, bob.spend_public, ephemeral=1234)
    >>> owns_output(output, bob.view_secret, bob.spend_public)
    True
    """
    integer(index, "index")
    shared = group.shared(view_public, ephemeral)
    p = group.p
    one_time = pow(group.g, _scalar(shared, index, group), p) * spend_public % p
    return StealthOutput(one_time, group.public(ephemeral))


def owns_output(
    output: StealthOutput,
    view_secret: int,
    spend_public: int,
    *,
    index: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> bool:
    """Whether ``output`` pays the wallet: the scan that needs only the view key."""
    integer(index, "index")
    shared = group.shared(output.tx_public, view_secret)
    p = group.p
    return pow(group.g, _scalar(shared, index, group), p) * spend_public % p == output.one_time_key


def one_time_secret(
    output: StealthOutput,
    view_secret: int,
    spend_secret: int,
    *,
    index: int = 0,
    group: DHGroup = TEACHING_GROUP,
) -> int:
    """The private key ``x = H(R**a) + b`` that spends ``output``.

    Raises
    ------
    ValueError
        The output does not pay this wallet.
    """
    integer(index, "index")
    shared = group.shared(output.tx_public, view_secret)
    secret = (_scalar(shared, index, group) + spend_secret) % group.q
    if pow(group.g, secret, group.p) != output.one_time_key:
        raise ValueError("the output does not pay this wallet")
    return secret
