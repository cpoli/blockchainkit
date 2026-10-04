# Changelog

## Unreleased

### Added

- Cryptography history: 22 breakthroughs, each with its own gallery example,
  from the one-time pad (1917-1949) to MuSig (2018). New APIs behind them:
  `one_time_pad`/`xor_bytes`; `baby_step_giant_step` and `pohlig_hellman`;
  `merkle_puzzles`/`solve_puzzle`; `lamport_keypair`/`lamport_sign`/
  `lamport_verify`; `find_collision`/`truncated_hash`; a readable
  Merkle-Damgard SHA-256 (`merkle_damgard_sha256`, `sha256_compress`,
  `sha256_padding`) with `length_extension`; `naive_mac` and `hmac_sha256`;
  `pedersen_commit`/`pedersen_generators`; `feldman_split`/`feldman_verify`;
  `TEACHING_GROUP`, a 62-bit safe-prime group; `simulate_transcript`;
  `deterministic_nonce` (RFC 6979, checked against the RFC's vectors); and
  `musig_coefficients`/`aggregate_public_keys`/`musig_sign`.
- `visualizers/` in every subpackage (Matplotlib, imported explicitly; plain
  `import blockchainkit` still loads only the standard library):
  `plot_curve_points`, `plot_hamming_distances`, `plot_merkle_tree`,
  `plot_proof_trace`, `plot_block_tree`, `plot_mining_trials`,
  `plot_stake_shares`, `plot_gossip_timeline`, `plot_execution_trace`.
  Matplotlib and NumPy are now runtime dependencies; the `examples` extra is
  gone.
- `execute(..., trace=True)` records a `TraceStep` after every instruction,
  following jumps; a failed run carries its partial trace in `VMError.trace`.
  `execute(..., gas_costs=...)` prices opcodes individually (each at least 1).
- `MerkleTree.levels`, `MerkleTree.leaf_count`, and `trace_proof`, which
  returns a `MerkleTrace` of `ProofStep`s, even for a proof that fails.
- `Blockchain.blocks`, `tips()`, `work_at()` and `state_at()` to inspect
  side forks.
- `enumerate_points` lists every point of a small curve.

### Changed

- The documentation follows the kit-family structure: generated hub pages per
  subpackage, per-subpackage API pages, a `history/` directory with one
  breakthroughs page per subpackage (each entry with its own *References:*
  line and `minigallery`), an examples index, tutorials (the guided course and
  solutions), and JupyterLite launch buttons. Examples moved to
  `examples/<subpackage>/<topic>/`. The committed per-example notebooks and
  their sync scripts are replaced by sphinx-gallery downloads and a single
  `notebooks/quickstart.ipynb`.
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
