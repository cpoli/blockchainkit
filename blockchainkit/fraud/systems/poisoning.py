"""Address poisoning with look-alike addresses (2022-2023).

An Ethereum address is 40 hexadecimal digits that nobody reads in full:
wallets shorten it to its first and last few characters, and users copy
the one they paid last from their transaction history. An address poisoner
watches for a payment from a victim to a counterparty, grinds an address
whose first and last characters match the counterparty's, and sends the
victim a worthless transfer from it, so that the look-alike appears in the
victim's history. The next time the victim copies the counterparty's
address from there, it pays the poisoner.

Matching :math:`k` hex characters takes about :math:`16^k` tries, so a few
seconds of computing fool a user who checks four characters at each end.
:func:`grind_lookalike` finds such an address, and
:func:`poisoning_suspects` flags the senders of tiny transfers whose
address resembles one the victim paid.
"""

from collections.abc import Iterable

from blockchainkit._validation import integer
from blockchainkit._validation import seed as check_seed
from blockchainkit.constants import LOOKALIKE_DOMAIN
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.fraud.core.base import Flow, LookalikeAddress
from blockchainkit.structures.utils.encoding import canonical_json


def _hex(address: str) -> str:
    if not isinstance(address, str):
        raise TypeError("addresses must be strings")
    digits = address[2:] if address.startswith("0x") else address
    if len(digits) != 40 or any(c not in "0123456789abcdef" for c in digits):
        raise ValueError("an address is 40 lowercase hex digits, optionally after 0x")
    return digits


def candidate_address(seed: int, index: int) -> str:
    """The ``index``-th address a grinder with ``seed`` tries: 20 bytes of a hash."""
    check_seed(seed)
    integer(index, "index")
    return "0x" + sha256(LOOKALIKE_DOMAIN + canonical_json([seed, index]))[-20:].hex()


def matched_characters(address: str, target: str, prefix: int = 4, suffix: int = 4) -> int:
    """How many of the first ``prefix`` and last ``suffix`` hex digits two addresses share.

    Characters are counted from each end until the first mismatch.

    Examples
    --------
    >>> from blockchainkit.fraud import matched_characters
    >>> a = "0x" + "ab12" + "0" * 32 + "cd34"
    >>> b = "0x" + "ab19" + "f" * 32 + "cd34"
    >>> matched_characters(a, b)
    7
    """
    left, right = _hex(address), _hex(target)
    integer(prefix, "prefix")
    integer(suffix, "suffix")
    if prefix + suffix > 40:
        raise ValueError("prefix and suffix cannot cover more than 40 digits")
    start = next((i for i in range(prefix) if left[i] != right[i]), prefix)
    end = next((i for i in range(suffix) if left[-1 - i] != right[-1 - i]), suffix)
    return start + end


def looks_alike(address: str, target: str, prefix: int = 4, suffix: int = 4) -> bool:
    """True if two different addresses agree on the digits a hurried user checks."""
    if _hex(address) == _hex(target):
        return False
    return matched_characters(address, target, prefix, suffix) == prefix + suffix


def grind_lookalike(
    target: str, *, prefix: int = 2, suffix: int = 2, seed: int = 0, max_trials: int = 1 << 20
) -> LookalikeAddress:
    """Generate addresses until one matches ``target``'s first and last digits.

    Each candidate matches with probability :math:`16^{-(\\text{prefix} +
    \\text{suffix})}`, so the expected number of trials is
    :math:`16^{\\text{prefix} + \\text{suffix}}`.

    Raises
    ------
    RuntimeError
        No match within ``max_trials``.
    """
    _hex(target)
    integer(max_trials, "max_trials", 1)
    for index in range(max_trials):
        address = candidate_address(seed, index)
        if looks_alike(address, target, prefix, suffix):
            return LookalikeAddress(address, target, index + 1, prefix + suffix)
    raise RuntimeError(f"no look-alike found in {max_trials} trials")


def poisoning_suspects(
    flows: Iterable[Flow], victim: str, *, prefix: int = 4, suffix: int = 4, dust: int = 1
) -> tuple[str, ...]:
    """Senders of transfers of at most ``dust`` to ``victim`` that resemble an address it paid.

    The look-alike must appear only after the victim paid the real address.
    """
    paid: list[str] = []
    suspects: list[str] = []
    for flow in flows:
        if flow.sender == victim:
            paid.append(flow.recipient)
        elif (
            flow.recipient == victim
            and flow.amount <= dust
            and flow.sender not in suspects
            and any(looks_alike(flow.sender, real, prefix, suffix) for real in paid)
        ):
            suspects.append(flow.sender)
    return tuple(suspects)
