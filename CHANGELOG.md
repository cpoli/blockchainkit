# Changelog

## [Unreleased]

### Added

- `blockchainkit.contracts`, a sixth subpackage on designing, breaking and
  verifying smart contracts, with a history page of 17 breakthroughs, each
  with its own gallery example, from Floyd and Hoare (1967-1969) to
  Beanstalk's flash-loan governance attack (2022), and an exercise page.
  New APIs: the world-state model `World` and `Contract` (`call`,
  `delegatecall`, `send`, CREATE and CREATE2, events, `selfdestruct`, gas,
  per-call rollback, invariants) with `create_address` and
  `create2_address`; `weakest_precondition`, `check_triple` and
  `run_program`; `symbolic_execute`, `symbolic_bytecode` (for `vm`
  programs) and `solve`; `requires` and `ensures`; `fuzz` and `shrink`;
  Ricardian contracts; `Mint` and `Purse`; ERC-20 and ERC-721 tokens; King
  of the Ether, GovernMental, block-hash and commit-reveal lotteries; the
  Parity wallet libraries; naive and EIP-1967 proxies; a CREATE2 factory;
  and flash-loan governance. Plots: `plot_call_tree`,
  `plot_symbolic_paths` and `plot_storage`.
- `blockchainkit.economics`, a seventh subpackage on incentives, fees and
  markets, with a history page of 16 breakthroughs, each with its own
  gallery example, from Schelling's focal points (1960) to proposer-builder
  separation (2022), and an exercise page. New APIs: `coordination_probability`
  and `schelling_round`; first- and second-price auctions, virtual values,
  equilibrium bids and expected revenue; the logarithmic market scoring
  rule; `block_subsidy`, `issued_supply` and `double_spend_incentive`;
  `simulate_block_rewards`, `mining_gap` and `undercutting_payoffs`;
  `optimal_mining_revenue` and `honest_mining_is_equilibrium`;
  `next_base_fee` and `simulate_fee_market`; `amount_out`,
  `impermanent_loss` and the `ConstantProductPool` contract; Dai's
  `VaultEngine` with `Stablecoin` and `PriceFeed`; the `OracleLender` and
  `OracleAttacker` contracts; `priority_gas_auction`, `sandwich_profit` and
  `sandwich_attack`; and `simulate_pbs`. Plots: `plot_fee_market`,
  `plot_constant_product` and `plot_gas_auction`. The model boundaries page
  gains an "Economic models" section.
- `blockchainkit.channels`, an eighth subpackage on layer-2 scaling and
  interoperability, with a history page of 16 breakthroughs, each with its
  own gallery example, from Reed-Solomon codes (1960) to the Ronin and
  Wormhole bridge exploits (2022), and an exercise page. New APIs:
  `rs_encode`, `rs_recover` and `rs_decode` (Berlekamp-Welch);
  `SpilmanChannel`, `DuplexChannel` with `invalidation_locktimes`,
  `LightningChannel` (revocation keys, shachain secrets, penalties),
  `EltooChannel`, and the `StateChannel` and `PreimageManager` contracts,
  all with Script outputs checked by `vm.verify_script`; `Watchtower`,
  `make_appointment` and PISA's `tower_liable`; `ChannelNetwork` for
  multi-hop HTLC routing and `probe_balance`; `AtomicSwap`; the `BTCRelay`
  contract and `mine_header`; `ValidatorBridge`, `GuardianVerifier` and
  `WormholeBridge`; `PlasmaChain` with Plasma Cash exits;
  `shard_failure_probability` and `atomix_transfer`; `ZKRollup`,
  `OptimisticRollup` and `bisect`; and `extend`, `simulate_sampling` and
  encoding fraud proofs for data availability. Plots: `plot_shares`,
  `plot_route` and `plot_detection`. The model boundaries page gains a
  "Channels, rollups and bridges" section.
- `blockchainkit.proofs`, a ninth subpackage on zero-knowledge and succinct
  proof systems, with a history page of 16 breakthroughs, each with its own
  gallery example, from the Schwartz-Zippel lemma (1980) to Halo (2019),
  and an exercise page. New APIs: polynomial arithmetic, interpolation and
  the FFT over the BabyBear field (`FIELD_PRIME`) and a Fiat-Shamir
  `Transcript`; `identity_test`; `sumcheck` and `multilinear_extension`;
  `tqbf_protocol`; `hadamard_proof` and `pcp_verify`; `kilian_argument`,
  `micali_proof` and `verify_cs_proof`; a toy supersingular
  `PAIRING_CURVE` with the Tate `pairing`; KZG (`trusted_setup`,
  `kzg_commit`, `kzg_open`, `kzg_verify`, `forge_opening`); powers-of-tau
  ceremonies (`contribute`, `verify_contribution`); the R1CS builder
  `Circuit`, `r1cs_to_qap` and `qap_divide`; Groth16; MiMC and a Zerocash
  `ShieldedPool` with `prove_spend`; `PlonkCircuit` and PLONK with
  `permutation_product`; Bulletproofs `range_proof`; `fri_prove` and
  `fri_verify`; a Fibonacci `stark_prove`; and Halo's `ipa_open`,
  `ipa_defer`, `accumulate` and `decide`. Plots: `plot_field_polynomials`,
  `plot_proof_sizes` and `plot_copy_constraints`. The model boundaries page
  gains a "Proof systems" section, and `blockchainkit.constants` the
  `TRANSCRIPT_DOMAIN`, `IPA_GENERATOR_DOMAIN` and `MIMC_DOMAIN` tags.
- `blockchainkit.fraud`, a tenth subpackage on financial fraud on and
  around blockchains, with a history page of 17 breakthroughs, each with its
  own gallery example, from Ponzi's scheme (1920) to address poisoning
  (2022-2023), and an exercise page. New APIs: `simulate_ponzi`,
  `breakeven_growth`, `simulate_lending_ponzi` and `referral_commissions`;
  the `ChainPonzi` contract with `value_flows` and `ponzi_features`;
  `benford_test`; the `MerkleSumTree` with `verify_sum_proof`,
  `liability_tree`, `audit` and `reserve_ratio`; Provisions-style proofs of
  solvency (`SolvencyProver`, `verify_solvency`, OR proofs and bitwise
  range proofs over Pedersen commitments); `reissue_missing` and the
  `Custodian` contract; `verify_source` and `effective_code`; the
  `TokenSale` (DAICO) contract; seven Torres et al. honeypot contracts with
  `explorer_view`; `SellBlockToken`, `HiddenMintToken` and `sell_test`;
  `simulate_bot_market`, `return_by_activity`, `simulate_pump_and_dump`
  and `detect_pumps`; `find_wash_trades` and `simulate_nft_market`; the
  `Drainer` contract with `open_approvals` and `allowance_exposure`; and
  `grind_lookalike` and `poisoning_suspects`. Plots: `plot_ponzi`,
  `plot_benford` and `plot_price_spikes`. The model boundaries page gains
  a "Fraud models" section, and `blockchainkit.constants` the
  `SUM_LEAF_DOMAIN`, `SUM_NODE_DOMAIN`, `SOLVENCY_DOMAIN` and
  `LOOKALIKE_DOMAIN` tags.
- `blockchainkit.privacy`, an eleventh subpackage on anonymity and
  confidentiality on public ledgers, with a history page of 15
  breakthroughs, each with its own gallery example, from Chaum's mix-nets
  (1981) to Tornado Cash (2019), and an exercise page. New APIs: `MixNode`,
  `seal`, `wrap` and `mix_cascade`; `circuit_compromise_rate`,
  `simulate_flows` and `match_flows`; `k_anonymity`, `equivalence_classes`
  and `effective_anonymity_set`; `ring_sign` and `ring_verify`;
  `lsag_sign`, `mlsag_sign`, `key_image` and `linked`; `simulate_payments`,
  `cluster_addresses` and `score_clusters`; `stealth_keys`,
  `stealth_payment`, `owns_output` and `one_time_secret`; `coinjoin` and
  `link_change`; the RSA accumulator, `ZerocoinPool` and
  `prove_zerocoin_spend`; ring-signature range proofs and
  `verify_confidential`; `ringct_spend` and `verify_ringct`;
  `mimblewimble_transaction`, `aggregate` and `cut_through`; the TumbleBit
  `Tumbler` with `run_tumbler`; `simulate_rings`, `chain_reaction` and
  `trace_rings`; and the `Mixer` contract with `prove_withdrawal` and
  `mixer_report`, proving with the Zerocash circuit of `proofs`. Plots:
  `plot_cluster_sizes`, `plot_ring_positions` and `plot_anonymity_sets`.
  The model boundaries page gains a "Privacy models" section, and
  `blockchainkit.constants` the `MIX_DOMAIN`, `RING_DOMAIN`,
  `KEY_IMAGE_DOMAIN`, `STEALTH_DOMAIN`, `KERNEL_DOMAIN`,
  `ACCUMULATOR_DOMAIN` and `TUMBLER_DOMAIN` tags.
- `blockchainkit.wallets`, a twelfth subpackage on keys as users actually
  hold them, with a history page of 15 breakthroughs, each with its own
  gallery example, from BCH codes (1959-1960) to ERC-4337 account
  abstraction (2021), and an exercise page. New APIs: `BCHCode` and
  `minimal_polynomial`; `verhoeff_digit`, `luhn_digit` and
  `detection_rates`; `pbkdf2` and `crack_pin`; `scrypt`, `salsa20_8`,
  `block_mix` and `romix` with a memory-time trade-off; Base58Check,
  `p2pkh_address` and `is_valid_address`; `bech32_encode`,
  `bech32_decode`, `segwit_encode`, `segwit_decode` and `p2wpkh_address`
  for Bech32 and Bech32m; `serialize_script`, `multisig_redeem_script`
  and `verify_p2sh`; BIP32's `master_key`, `derive_private`,
  `derive_public`, `serialize_extended_key` and `recover_parent_private`;
  BIP39's `entropy_to_mnemonic` and `mnemonic_to_seed`; BIP44's
  `derive_path` and `discover_accounts`; `brain_wallet_key` and
  `simulate_brain_drain`; `ecdsa_sign` and `ecdsa_verify`;
  `threshold_keygen` and `threshold_sign`; the `SocialRecoveryWallet`
  contract with `recovery_risk`; and ERC-4337's `EntryPoint`,
  `SmartAccount` and `bundle`. Utilities: RIPEMD-160 and `hash160`,
  compressed secp256k1 keys, and GF(2**m). Plots:
  `plot_detection_rates`, `plot_memory_tradeoff` and `plot_recovery_risk`.
  The model boundaries page gains a "Wallet models" section, and
  `blockchainkit.constants` the `HARDENED_OFFSET`, `BIP32_SEED_KEY`,
  `BIP39_SALT_PREFIX`, `MAX_SCRIPT_ELEMENT_SIZE` and
  `USER_OPERATION_DOMAIN` constants.
- `World.fork()` in `blockchainkit.contracts`: an independent copy of the
  world state on which to try transactions, as a wallet simulates one
  before sending it.
- Domain tags for contract addresses, block hashes, Ricardian contracts,
  lottery commitments and wallet approvals in `blockchainkit.constants`,
  and for channel states, Plasma transfers, rollup state, bridge
  withdrawals and watchtower appointments,
  and a "Contract world model" section in the model boundaries page.

### Fixed

- `consensus.systems.fork_choice` imports `structures` only for type
  checking, so a subpackage that loads `structures` before `consensus` no
  longer hits a circular import.
- `FinalityGadget` no longer depends on vote arrival order: justification and
  finality are recomputed over every recorded vote, so a supermajority link
  recorded before its source was justified now counts once it is.
- `spread_rumor` validates `source` before using it, raising `ValueError`
  rather than `IndexError` for a peer outside the graph.
- `BloomFilter.false_positive_rate` and `BloomFilter.optimal_hash_count`
  validate their arguments (`optimal_hash_count(m, 0)` raised
  `ZeroDivisionError`).
- The GHOST history, module docstring and example no longer claim that
  Ethereum's proof-of-work chain used GHOST for fork choice: it adopted uncle
  rewards but kept heaviest-chain selection.

### Changed

- History pages follow mathematicskit's entry form: an epigraph per page, and
  per entry one prose account with its formula, an *Implementation:* line that
  also states the teaching-vs-production difference, *References:*, and the
  gallery link. The "In plain language", "Reading the experiment" and
  "Experiment" blocks, the admonitions and the in-entry doctests are folded
  in or removed. The history index is reduced to its overview.
- The history pages of `crypto`, `consensus`, `network`, `vm`, `contracts`,
  `economics`, `channels`, `proofs` and `fraud` are rewritten for readers new
  to the field: each introduction and entry opens with the problem the
  breakthrough solved, defines its terms in plain language, and spells out
  algorithms as numbered steps.
- The documentation's landing page is titled "Learn How Blockchains Work in
  Python" and links the sibling toolkits.
- Gallery examples follow mathematicskit's layout: raw docstrings without
  section headings or trailing links, one import cell, and `plt.show()`. The
  Merkle-proof example's exercise moved to the end, and the capstone is now
  `structures/chain/plot_01_payment_lifecycle.py`.
- `subtree_work` and `ghost_tip` compute every subtree's work in one pass.

## [0.2.0] - 2026-10-04

The package is aligned with its kit-family siblings, and every subpackage now
follows its field through at least 15 breakthroughs, each with its own
experiment.

### Added

- Tutorials across subpackages, every line run by the doctest build: *Life of
  a payment*, *Nonces everywhere*, *Hashes everywhere* and *Who do you
  trust?*.
- Exercise pages, one per subpackage, with 40 worked solutions in collapsed
  boxes, each run by the doctest build. They replace the single solutions page.
- A "Teaching vs production" note on every history entry that adapts a
  deployed protocol, naming the difference.
- README figures, regenerated by `docs/make_readme_figure.py` and
  `docs/make_readme_subpackage_figures.py`.
- Execution history: 16 breakthroughs, each with its own gallery example,
  from reverse Polish notation (1924-1957) to the BeautyChain overflow
  (2018). New APIs: `execute(..., arguments=...)`, the Forth words `OVER` and
  `ROT`, `REVERT`, and the shared `STACK_EFFECTS` table; `validate_program`;
  `assemble` (labels); `to_rpn` and `compile_expression`; `verify_bytecode`
  and `VerificationResult`; `run_turing_machine`, `enumerate_machines` and
  `busy_beaver` (reproducing S(2) = 6); Bitcoin-style Script with
  `verify_script`, `p2pkh_locking`/`p2pkh_unlocking` and `htlc_locking`
  (`OP_CHECKLOCKTIMEVERIFY`); the contracts `vending_machine` and
  `batch_transfer` (BEC overflow, with a SafeMath option); `drain_bank`
  (DAO reentrancy); and the plot `plot_stack_height`.
- Network history: 17 breakthroughs, each with its own gallery example, from
  Erdős-Rényi random graphs (1959) to Dandelion (2017). New APIs: `Graph`,
  `erdos_renyi`, `ring_lattice`, `watts_strogatz`, `barabasi_albert` and
  `complete_graph`; `lamport_timestamps`, `vector_timestamps`,
  `happened_before` and `concurrent`; `spread_rumor` (push, pull, push-pull)
  and `pittel_rounds`; `reliable_broadcast` (Bracha); `ReplicatedRegister`
  (CAP); `KademliaNetwork`, `xor_distance` and `node_id`; `AddressManager`
  and `eclipse_probability`; `relay_cost`, `compact_block_relay` and
  `short_id`; `fork_rate` and `simulate_fork_rate`; `first_spy_precision`;
  `SimulatedNetwork.from_graph` and `SimulatedNetwork.messages_sent`; the
  plots `plot_graph`, `plot_space_time` and `plot_rumor_spread`; and the
  `COMPACT_BLOCK_DOMAIN` constant.
- Consensus history: 17 breakthroughs, each with its own gallery example,
  from the gambler's ruin (1656) to Casper FFG (2017). New APIs:
  `oral_messages` (Byzantine generals); `ben_or` (randomized consensus, also
  used to show the FLP adversary); `view_changes` (partial synchrony);
  `modular_square_root` (Dwork-Naor pricing); `pbft_round` and
  `quorum_size`; `attacker_success_probability` (whitepaper section 11, checked
  against its table); `retarget` and `simulate_difficulty`; `ghost_tip` and
  `subtree_work`; `selfish_mining_revenue`, `selfish_mining_threshold` and
  `simulate_selfish_mining`; `fork_voting_payoffs` (nothing at stake);
  `sortition`; and `FinalityGadget` (Casper FFG with slashing detection).
- Structures history: 15 breakthroughs, each with its own gallery example,
  from double-entry bookkeeping (1494) to Merkle mountain ranges (2016). New
  APIs: `Ledger.total_supply`; `BloomFilter`; `hash_chain` and
  `verify_one_time_password`; `BlockHeader`, `Block.to_header()` and
  `verify_header_chain` for light clients; `bitcoin_merkle_root` (Bitcoin's
  duplicated-leaf convention, for CVE-2012-2459); `MerkleTree.consistency_proof`
  and `verify_consistency` (RFC 6962/9162); `UTXOSet`, `UTXOTransaction`,
  `OutPoint` and `Coin`; `Transaction.unsigned_id` (SegWit-style);
  `SparseMerkleTree` with membership and non-membership proofs; and
  `MerkleMountainRange`.
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

## [0.1.0] - 2026-10-04

Initial local release, never published.

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
