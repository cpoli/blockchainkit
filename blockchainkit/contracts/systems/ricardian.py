"""Ricardian contracts: legal prose bound to code by a hash (Grigg, 1996).

Ian Grigg designed the Ricardian contract for issuing bonds and currencies
on the Ricardo payment system. One document is at once a legal contract a
person can read and a set of parameters a program can parse; the issuer
signs it, and its hash names the instrument. Every payment cites that hash,
so there is never a question which terms a payment was made under, and
changing one word of the prose creates a different instrument.

Here a :class:`~blockchainkit.contracts.core.base.RicardianContract` holds
the prose, with ``{name}`` placeholders for its parameters, and the
issuer's Schnorr signature over its digest. :class:`RicardianToken` is an
ERC-20 token that stores the digest and accepts only payments that cite it.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

from blockchainkit.constants import RICARDIAN_DOMAIN
from blockchainkit.contracts.core.base import RicardianContract
from blockchainkit.contracts.systems.tokens import ERC20
from blockchainkit.crypto.systems.curves import public_key
from blockchainkit.crypto.systems.hashing import sha256
from blockchainkit.crypto.systems.signatures import deterministic_nonce, sign, verify
from blockchainkit.structures.utils.encoding import canonical_json


def ricardian_digest(text: str, parameters: Mapping[str, int | str]) -> bytes:
    """SHA-256 of the domain tag and the canonical encoding of the prose and parameters."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    for name, value in parameters.items():
        if not isinstance(name, str) or type(value) not in (int, str):
            raise TypeError("parameters map names to integers or strings")
    text.format(**parameters)  # Every placeholder must have a parameter.
    return sha256(RICARDIAN_DOMAIN + canonical_json({"parameters": dict(parameters), "text": text}))


def ricardian_contract(
    text: str, parameters: Mapping[str, int | str], issuer_key: int
) -> RicardianContract:
    """Write and sign a Ricardian contract.

    Parameters
    ----------
    text : str
        The terms, with a ``{name}`` placeholder for each parameter.
    parameters : mapping
        Values the program reads, such as the supply.
    issuer_key : int
        The issuer's private key; signing is deterministic (RFC 6979 style).

    Examples
    --------
    >>> from blockchainkit.contracts import ricardian_contract, verify_ricardian
    >>> bond = ricardian_contract("Pays {coupon}% a year.", {"coupon": 5}, issuer_key=7)
    >>> bond.rendered, verify_ricardian(bond)
    ('Pays 5% a year.', True)
    """
    digest = ricardian_digest(text, parameters)
    signature = sign(digest, issuer_key, nonce=deterministic_nonce(issuer_key, digest))
    return RicardianContract(
        text, MappingProxyType(dict(parameters)), public_key(issuer_key), signature, digest
    )


def verify_ricardian(contract: RicardianContract) -> bool:
    """True if the digest matches the prose and parameters and the issuer signed it."""
    if ricardian_digest(contract.text, contract.parameters) != contract.digest:
        return False
    return verify(contract.digest, contract.signature, contract.issuer)


class RicardianToken(ERC20):
    """An ERC-20 token issued under a Ricardian contract, whose payments must cite its hash."""

    layout: ClassVar[tuple[str, ...]] = (*ERC20.layout, "terms")

    def constructor(self, terms: str, supply: int) -> None:  # type: ignore[override]
        super().constructor(supply)
        self.write("terms", terms)

    def terms(self) -> str:
        """The identifier of the contract the token was issued under."""
        return str(self.read("terms"))

    def transfer_under(self, terms: str, to: str, amount: int) -> bool:
        """Transfer, citing the terms; a payment citing other terms reverts."""
        self.require(terms == self.read("terms"), "payment cites different terms")
        return self.transfer(to, amount)
