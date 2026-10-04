"""Cryptographic foundations: hashing, public keys, sharing, curves, and proofs."""

from blockchainkit.crypto.core.base import (
    CollisionResult,
    DiscreteLogResult,
    FeldmanShares,
    LamportKeyPair,
    Point,
    PuzzleSolution,
    SchnorrSignature,
)
from blockchainkit.crypto.systems.asymmetric import (
    TEACHING_GROUP,
    DHGroup,
    RSAKeyPair,
    rsa_blind,
    rsa_keypair,
    rsa_unblind,
)
from blockchainkit.crypto.systems.commitments import (
    commit,
    pedersen_commit,
    pedersen_generators,
    verify_commitment,
)
from blockchainkit.crypto.systems.curves import (
    SECP256K1,
    TOY_CURVE,
    Curve,
    add,
    encode_point,
    enumerate_points,
    multiply,
    public_key,
)
from blockchainkit.crypto.systems.discrete_log import (
    baby_step_giant_step,
    pohlig_hellman,
)
from blockchainkit.crypto.systems.hashing import (
    find_collision,
    hamming_distance,
    hash256,
    sha256,
    truncated_hash,
)
from blockchainkit.crypto.systems.lamport import (
    lamport_keypair,
    lamport_sign,
    lamport_verify,
)
from blockchainkit.crypto.systems.mac import (
    hmac_sha256,
    naive_mac,
)
from blockchainkit.crypto.systems.merkle_damgard import (
    SHA256_IV,
    length_extension,
    merkle_damgard_sha256,
    sha256_compress,
    sha256_padding,
)
from blockchainkit.crypto.systems.multisig import (
    aggregate_public_keys,
    musig_coefficients,
    musig_sign,
)
from blockchainkit.crypto.systems.one_time_pad import (
    one_time_pad,
    xor_bytes,
)
from blockchainkit.crypto.systems.puzzles import (
    merkle_puzzles,
    solve_puzzle,
)
from blockchainkit.crypto.systems.sharing import (
    feldman_split,
    feldman_verify,
    recover_secret,
    split_secret,
)
from blockchainkit.crypto.systems.signatures import (
    challenge,
    deterministic_nonce,
    recover_reused_nonce_key,
    sign,
    simulate_transcript,
    verify,
    verify_transcript,
)
from blockchainkit.crypto.utils.primes import (
    is_prime,
)

__all__ = [
    "CollisionResult",
    "DiscreteLogResult",
    "FeldmanShares",
    "LamportKeyPair",
    "Point",
    "PuzzleSolution",
    "SchnorrSignature",
    "DHGroup",
    "RSAKeyPair",
    "TEACHING_GROUP",
    "rsa_blind",
    "rsa_keypair",
    "rsa_unblind",
    "commit",
    "pedersen_commit",
    "pedersen_generators",
    "verify_commitment",
    "SECP256K1",
    "TOY_CURVE",
    "Curve",
    "add",
    "encode_point",
    "enumerate_points",
    "multiply",
    "public_key",
    "baby_step_giant_step",
    "pohlig_hellman",
    "find_collision",
    "hamming_distance",
    "hash256",
    "sha256",
    "truncated_hash",
    "lamport_keypair",
    "lamport_sign",
    "lamport_verify",
    "hmac_sha256",
    "naive_mac",
    "SHA256_IV",
    "length_extension",
    "merkle_damgard_sha256",
    "sha256_compress",
    "sha256_padding",
    "aggregate_public_keys",
    "musig_coefficients",
    "musig_sign",
    "one_time_pad",
    "xor_bytes",
    "merkle_puzzles",
    "solve_puzzle",
    "feldman_split",
    "feldman_verify",
    "recover_secret",
    "split_secret",
    "challenge",
    "deterministic_nonce",
    "recover_reused_nonce_key",
    "sign",
    "simulate_transcript",
    "verify",
    "verify_transcript",
    "is_prime",
]
