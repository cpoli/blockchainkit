# Roadmap

What blockchainkit does not do yet, in priority order.

blockchainkit covers the protocol core in five subpackages: `crypto`,
`structures`, `consensus`, `network` and `vm`; how contracts are designed,
broken and verified in a sixth, `contracts`; and incentives, fees and
markets in a seventh, `economics`; layer-2 scaling and
interoperability in an eighth, `channels`; and zero-knowledge and succinct
proof systems in a ninth, `proofs`; and financial fraud in a tenth,
`fraud`; anonymity and confidentiality in an eleventh, `privacy`; and keys
as users actually hold them in a twelfth, `wallets`, with 15 to 22 history
breakthroughs each, every one with its own gallery example. Every planned
item is done; new items go above **Done**.

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

## Done

Finished items move here with the release they shipped in, as in
CHANGELOG.md.

### 0.3.0 (2026-10-24)

- `wallets`: keys as users actually hold them, with 15 history
  breakthroughs from BCH codes to ERC-4337, each with its own gallery
  example, and an exercise page. Standards are reproduced to their
  published test vectors: Base58Check and P2PKH addresses (with a
  pure-Python RIPEMD-160), Bech32 and Bech32m, PBKDF2 and scrypt, BIP32
  extended keys and BIP39's seed derivation, and RFC 6979 ECDSA on
  secp256k1. BIP39's English word list is replaced by 2048 generated
  four-letter words; P2SH runs on `vm.script`, so it hashes with
  `OP_HASH256` and writes m-of-n as one `OP_IF` branch per signer set;
  threshold ECDSA follows Gennaro and Goldfeder with an ideal MtA in place
  of Paillier; and the social-recovery wallet and ERC-4337's EntryPoint and
  smart account are contracts on `contracts.World`. The history page
  cross-links Shamir, Feldman and MuSig in `crypto`, Script in `vm`, the
  Parity wallets in `contracts`, and address poisoning in `fraud`.
- `privacy`: anonymity and confidentiality on public ledgers, with 15
  history breakthroughs from Chaum's mix-nets to Tornado Cash, each with its
  own gallery example, and an exercise page. Everything works in
  `crypto.TEACHING_GROUP`: hashed-ElGamal mix and onion layers, AOS ring
  signatures (standing in for Rivest, Shamir and Tauman's RSA rings), LSAG
  and MLSAG with CryptoNote's key images, stealth addresses, bitwise
  ring-signature range proofs for confidential amounts, RingCT with one
  input, and Mimblewimble with kernel offsets. Zerocoin's spend proves
  membership with a ring signature over every coin rather than against its
  RSA accumulator; TumbleBit keeps the blinded RSA puzzles but not the
  on-chain fair exchange; and the Tornado-style `Mixer` contract proves
  with the Zerocash circuit of `proofs`, binding the recipient through the
  new-note commitment. Clustering, traceability and the mixer's anonymity
  sets run on seeded simulations. The history page cross-links Chaum's
  blind signatures and Pedersen commitments in `crypto`, Dandelion in
  `network`, and Zerocash and Bulletproofs in `proofs`.
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
