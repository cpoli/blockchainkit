# Changelog

## Unreleased

### Changed

- The package uses the kit-family layout: one subpackage per domain with
  `core/`, `systems/`, `utils/` and `tests/`, shared validation in
  `_validation.py`, and every consensus-relevant constant in `constants.py`.
  Public `bk.<subpackage>.<name>` imports are unchanged.
- A wrong argument *type* (bool, float, string) now raises `TypeError`; an
  out-of-range integer still raises `ValueError`. `multiply` reports the two
  cases separately.
- Mining varies only the header nonce: `Block.merkle_root` and `Block.hash`
  are cached, and `Block.header(nonce=...)` builds a candidate header without
  rebuilding the Merkle tree. Mining a 20-transaction block is about 59 times
  faster per attempt (2 µs instead of 118 µs).
- `verify` skips the subgroup-membership multiplications when Hasse's bound
  proves the cofactor is 1 (new `Curve.cofactor_is_one`), halving the cost of
  verification on secp256k1.
- `Ledger`, `Blockchain`, `MerkleTree` and `SimulatedNetwork` have readable
  `repr`s.

### Fixed

- `Transaction` rejects a `signature` that is not a `SchnorrSignature`;
  before, the block hash raised `AttributeError` later.
- `execute` raises `VMError`, not `TypeError`, for a non-string opcode.
- `Curve` accepts secp256k1's field prime and group order only in their own
  roles; swapping them no longer skips the primality check.
- A receive callback that raises no longer leaves the payload marked seen.
- `eventual_catch_up` rejects non-numeric fractions, and `StakeSampler` and
  `SimulatedNetwork` reject non-integer seeds.

## 0.1.0 — initial local release

- Five typed subpackages for cryptography, authenticated structures, consensus
  experiments, peer simulation, and bounded execution.
- Sphinx history chapter covering 15 milestones with primary references.
- Twelve executable gallery experiments and matching generated notebooks.
- Signed account transfers, replay checks, atomic ledger updates, and fork
  state restoration through cumulative-work chain selection.
- Explicit teaching scope and package-specific serialization conventions.

- Full statement and branch coverage, with 112 tests and a 100% coverage gate.
- Stake sampling uses cumulative integer weights and binary search; Merkle proof
  validation removes a redundant guard already implied by the checked path length.

- Guided seven-lesson course with learning objectives, prerequisites, checkpoints,
  and executable worked answers for all thirteen experiments.
- Payment-lifecycle capstone with local pending queues, partitioned mining,
  synchronization, reorganization, reinclusion, and replay rejection.
- Merkle-proof and VM stack trace figures; historical overview and dependency map.
