"""Cryptographic foundations: hashing, public keys, sharing, curves, and proofs."""

from blockchainkit.crypto.asymmetric import DHGroup, RSAKeyPair, rsa_blind, rsa_keypair, rsa_unblind
from blockchainkit.crypto.curves import (
    SECP256K1,
    TOY_CURVE,
    Curve,
    Point,
    add,
    encode_point,
    multiply,
    public_key,
)
from blockchainkit.crypto.hashing import (
    commit,
    hamming_distance,
    hash256,
    sha256,
    verify_commitment,
)
from blockchainkit.crypto.sharing import recover_secret, split_secret
from blockchainkit.crypto.signatures import (
    SchnorrSignature,
    challenge,
    recover_reused_nonce_key,
    sign,
    verify,
    verify_transcript,
)

__all__ = [
    "SECP256K1",
    "TOY_CURVE",
    "Curve",
    "Point",
    "add",
    "encode_point",
    "multiply",
    "public_key",
    "commit",
    "hamming_distance",
    "hash256",
    "sha256",
    "verify_commitment",
    "DHGroup",
    "RSAKeyPair",
    "rsa_blind",
    "rsa_keypair",
    "rsa_unblind",
    "recover_secret",
    "split_secret",
    "SchnorrSignature",
    "challenge",
    "recover_reused_nonce_key",
    "sign",
    "verify",
    "verify_transcript",
]
