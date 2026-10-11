# Roadmap

What blockchainkit does not do yet, in priority order.

blockchainkit covers the protocol core in five subpackages: `crypto`,
`structures`, `consensus`, `network` and `vm`; how contracts are designed,
broken and verified in a sixth, `contracts`; and incentives, fees and
markets in a seventh, `economics`; layer-2 scaling and
interoperability in an eighth, `channels`; and zero-knowledge and succinct
proof systems in a ninth, `proofs`; and financial fraud in a tenth,
`fraud`, with 15 to 22 history breakthroughs each, every one with its own
gallery example. Items 1 and 2 are smaller and could instead become modules
in `crypto` and `structures`.

Each item lists why it matters, the current state, and a sketch of the
approach. The candidate breakthroughs are a draft: verify each date against
its primary source while writing the history page, and, as in Phase 5 of
`PLAN.md`, change the example rather than the breakthrough when the match is
unclear.

The project conventions apply to every new subpackage:
- the standard layout: `core/base.py` with frozen result dataclasses,
  `systems/`, `utils/`, `visualizers/`, and `tests/` at 100% statement and
  branch coverage;
- `import blockchainkit` stays standard-library only, with no new runtime
  dependencies;
- parameters small enough to inspect, with every departure from the deployed
  protocol stated in the history entry's *Implementation:* line and in
  `docs/source/protocol.rst`;
- explicit seeds, strict `mypy`, and NumPy-style docstrings that cite their
  source;
- a history page with at least 15 breakthroughs, each with its own gallery
  example, and an exercise page.

## 1. `privacy`: anonymity and confidentiality on public ledgers

**Why.** A public ledger is a permanent record of who paid whom. Users need
to know what it reveals, and which techniques hide senders, receivers and
amounts.

**Now.** Pieces are spread across the package: blind signatures and Pedersen
commitments in `crypto`, Dandelion in `network`. The history pages should
cross-link these rather than duplicate them.

**Approach.** Address-clustering heuristics on a simulated transaction
graph; CoinJoin and its anonymity set; ring signatures over the teaching
curve; stealth addresses; and confidential amounts from Pedersen
commitments. Candidate breakthroughs:

1. 1981: Chaum's mix-nets
2. 2001: ring signatures (Rivest, Shamir and Tauman)
3. 2002: k-anonymity (Sweeney) and anonymity sets
4. 2004: onion routing in Tor
5. 2004: linkable ring signatures and key images
6. 2013: Meiklejohn et al., *A Fistful of Bitcoins*: clustering addresses
7. 2013: CryptoNote stealth addresses
8. 2013: CoinJoin
9. 2013: Zerocoin
10. 2015: confidential transactions
11. 2016: RingCT
12. 2016: Mimblewimble and transaction cut-through
13. 2017: TumbleBit, an untrusted payment hub
14. 2018: traceability in Monero (Möser et al.)
15. 2019: Tornado Cash and mixer contracts

Could instead be a `privacy` module in `crypto` plus history entries spread
across existing pages, if a sixth to eighth subpackage is too many.

## 2. `wallets`: keys as users actually hold them

**Why.** Most lost funds are lost through key handling, not broken
cryptography: weak brain wallets, mistyped addresses, lost backups, a single
point of failure. The package derives keys from integers and never shows
encodings, derivation or recovery.

**Now.** `crypto` has key generation from integers, Shamir and Feldman
sharing, and MuSig. `structures.address` is a plain SHA-256 hex digest.

**Approach.** Address encodings with checksums; key stretching; BIP32 child
key derivation on secp256k1; mnemonic encoding with a small word list;
multisig and threshold signing built on `crypto`. Candidate breakthroughs:

1. 1959-1960: BCH error-correcting codes, the basis of Bech32
2. 1969: Verhoeff's check digit and detecting transpositions
3. 2000: PBKDF2 key stretching
4. 2009: scrypt and memory-hard key derivation
5. 2009: Base58Check addresses
6. 2012: pay-to-script-hash and multisig
7. 2012: hierarchical deterministic wallets (BIP32)
8. 2013: mnemonic seed phrases (BIP39)
9. 2014: multi-account derivation paths (BIP44)
10. 2016: the brain-wallet drain (Vasek et al.)
11. 2017: Bech32 addresses (BIP173)
12. 2018: threshold ECDSA (Gennaro and Goldfeder)
13. 2020: Bech32m (BIP350) and a checksum flaw
14. 2021: social-recovery wallets
15. 2021: account abstraction (ERC-4337)

Could instead be modules in `crypto` (key derivation, threshold signing) and
`structures` (address encodings).

## Done

Finished items move here with the release they shipped in, as in
CHANGELOG.md.

### Unreleased

- `fraud`: financial fraud on and around blockchains, with 17 history
  breakthroughs from Ponzi's scheme to address poisoning, each with its own
  gallery example, and an exercise page. Scam contracts (a chain Ponzi,
  seven Torres et al. honeypots, a token sale with a DAICO tap, sell-block
  and hidden-mint tokens, an approval drainer, a custodian that lends
  deposits) run on `contracts.World`, each showing in its example the
  Solidity its victim reads; the Solidity-level honeypot quirks are
  reproduced by their effect only. Detectors are pure functions over
  simulated transfers, trades and prices, and proofs of reserves,
  liabilities and solvency use a Merkle sum tree in `utils/` and Pedersen
  commitments. `World.fork()` was added to `contracts` for the sell test.
  The ICO entry is dated 2017-2018 (PlexCoin and the DAICO) rather than
  2020, and address poisoning 2022-2023, to match their sources.
- `proofs`: zero-knowledge and succinct proof systems, with 16 history
  breakthroughs from the Schwartz-Zippel lemma to Halo, each with its own
  gallery example, and an exercise page. Polynomials and FFTs over the
  BabyBear field in `utils/`; sum-check, IP = PSPACE, the Hadamard PCP and
  Kilian and Micali arguments; a toy supersingular pairing curve for KZG,
  powers-of-tau ceremonies, Groth16 and PLONK; Zerocash as a shielded pool
  on Groth16; and Bulletproofs, FRI, a Fibonacci STARK and Halo's
  accumulation in the teaching group. `channels`' zk-rollup still uses its
  re-executing stand-in for a validity proof.
- `channels`: layer-2 scaling and interoperability, with 16 history
  breakthroughs from Reed-Solomon codes to the Ronin and Wormhole bridge
  exploits, each with its own gallery example, and an exercise page.
  Channel outputs are `vm.script` programs; the relay, state channel and
  bridges are contracts on `contracts.World`; the routing network is built
  on `network.Graph`. Rollups use a validity-proof stand-in that
  re-executes the batch, since it was written before `proofs`.
- `economics`: incentives, fees and markets, with 16 history breakthroughs
  from Schelling's focal points to proposer-builder separation, each with
  its own gallery example, and an exercise page. Auctions, oracles, rewards
  and mining games are pure functions and seeded simulations; the exchange,
  the stablecoin and the manipulated lender are contracts on
  `contracts.World`.
- `contracts`: a world-state model of contracts calling contracts, the
  contracts and attacks of 17 history breakthroughs from Floyd and Hoare to
  Beanstalk, each with its own gallery example, the verification tools
  (Hoare triples, symbolic execution of programs and of `vm` bytecode,
  design by contract, fuzzing), and an exercise page. The three contract
  entries of `vm` stayed there, cross-linked.
- History pages and gallery examples in mathematicskit's form: one prose
  account per breakthrough with *Implementation:* and *References:* lines,
  examples with a plain docstring and one import cell, and a docs home page
  with Subpackages, History, Examples and API.
- `FinalityGadget` justification no longer depends on vote arrival order.

### 0.2.0 (2026-10-04)

- The kit-family layout: five subpackages with `core/`, `systems/`,
  `utils/`, `visualizers/` and per-subpackage tests.
- Code-review fixes: header-only mining, faster verification on prime-order
  curves, and consistent exception types.
- Execution and Merkle-proof traces, block-tree accessors, and visualizers.
- Documentation in the family structure: subpackage hubs, API pages, and
  JupyterLite.
- History: 87 breakthroughs across the five subpackages, each with its own
  gallery example.
- Tutorials and per-subpackage exercise pages with solutions executed in the
  docs build.
- Tag-driven release to PyPI, docs on GitHub Pages, and a Zenodo version DOI.
