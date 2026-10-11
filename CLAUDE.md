# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An educational, typed Python toolkit for cryptography and blockchain systems: ten domain subpackages (`crypto`, `structures`, `consensus`, `network`, `vm`, `contracts`, `economics`, `channels`, `proofs`, `fraud`) that follow each idea from its history and mathematics to a small API, a gallery experiment, and a notebook. Conventionally imported as `bk`. It is deliberately *not* production cryptography: tiny RSA/DH parameters, variable-time curve arithmetic, a 35-bit toy pairing curve whose setup secrets can be brute-forced, proof systems over a 31-bit field, non-BIP-340 Schnorr, and non-Bitcoin/Ethereum wire formats. Keep those model boundaries explicit.

blockchainkit is a sibling package to `../mathematicskit`, `../physicskit`, `../chemistrykit` and `../tbkit`, and is being aligned with their architecture and conventions (see `PLAN.md` for the phases and what is done). When a convention here seems underspecified, check how mathematicskit handles the equivalent case rather than inventing a new one.

## Commands

```bash
# setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# lint / format (line length 100)
ruff check .
ruff format .

# unit tests: must stay at 100% statement and branch coverage
pytest -q --cov=blockchainkit --cov-branch --cov-report=term-missing
pytest blockchainkit/vm/tests
pytest blockchainkit/vm/tests/test_vm.py::test_binary_semantics -q

# docstring examples
pytest --doctest-modules blockchainkit --ignore-glob="*/tests/*"

# type check (strict, blocking in CI)
mypy

# docs: re-executes every examples/*/*/plot_*.py; warnings are errors (nitpicky = True)
cd docs && MPLBACKEND=Agg make html && MPLBACKEND=Agg make doctest

python -m build
```

CI: `.github/workflows/ci.yml` runs lint, tests on Python 3.10-3.15 on Linux and macOS, the package build (`twine check`, no tests in the wheel), and mypy; `docs.yml` runs the HTML and doctest builds. `release.yml` runs on a `vX.Y.Z` tag: the tag must match `__version__`, CITATION.cff's `version` and a `## [X.Y.Z] - date` CHANGELOG section; it publishes to PyPI (trusted publisher, environment `pypi`), creates the GitHub Release, and deploys the docs to gh-pages.

## Architecture

**One subpackage per domain**, each at `blockchainkit/<name>/` with its own `tests/` directory (not a top-level `tests/`). Every subpackage uses the same internal layout: `core/base.py` (shared types and frozen result dataclasses, never bare tuples), `systems/` (concrete constructions and protocols, one module per family), `utils/` (supporting helpers that are not a model themselves; only where needed), `visualizers/` (matplotlib plotting: functions take `ax=None` and return the `Axes`), and `tests/`. `import blockchainkit` must stay stdlib-only: nothing outside `visualizers/` imports matplotlib or numpy, and subpackage `__init__.py` files do not import `visualizers`. Each subpackage's `__init__.py` re-exports the public names of its `core` and `systems` layers, and `blockchainkit/tests/test_package.py` checks that.

Shared across all subpackages:
- `blockchainkit/_validation.py`: `integer()` is the argument validator used everywhere (rejects bools and non-ints, with an inclusive lower bound); `seed()`, `probability()` and `positive()` validate seeds, values in [0, 1], and positive finite reals.
- `blockchainkit/constants.py`: the single home for consensus-relevant constants (Merkle and commitment and Schnorr domain tags, `UINT64_LIMIT`, `WORD_MODULUS`, `DEFAULT_CHAIN_ID`). Never inline a domain tag or bound in a module.

The subpackages:
- `crypto`: the foundation. `systems/hashing.sha256` is the common hash; `systems/signatures` builds Schnorr on `systems/curves`; `utils/primes.is_prime` is a deterministic Miller-Rabin bounded to 2**64.
- `structures`: `Transaction` (signed account transfers, `utils/encoding.canonical_json`) → `Block` (frozen dataclass; the header commits to a `MerkleTree` root) → `Ledger` (immutable balances and nonces; `apply` returns a new ledger or raises, leaving the old one intact) → `Blockchain` (stores all valid blocks, selects the tip by cumulative work, restores state on reorg).
- `consensus`: `systems/pow` (`mine`, `valid_pow`, `expected_trials`), `systems/catch_up`, `systems/pos.StakeSampler`. Layering: `structures.systems.chain` imports `consensus.systems.pow`, while `pow` and `core.base.MiningResult` refer to `Block` only under `TYPE_CHECKING` to avoid a cycle.
- `network`: `systems/gossip.SimulatedNetwork`, a deterministic discrete-event gossip simulator (latency ranges, partitions, duplicate suppression by payload hash; `from_graph` builds one from a `systems/topology.Graph`). The other systems modules are small models, one per history breakthrough: topologies, logical clocks, epidemics, Bracha broadcast, a CAP register, Kademlia, an eclipse-attack address table, relay costs, fork rates, and Dandelion. Payloads are opaque bytes; it is not coupled to `structures`.
- `vm`: `systems/stack_machine.execute()` over `(opcode, operand)` tuples; a 256-bit modular stack machine with gas, storage, call `arguments`, and atomic failure. `STACK_EFFECTS` is the single table of opcode stack effects, shared with `systems/verifier`. Other systems modules: `assembler` (labels), `expressions` (RPN), `turing` (busy beaver), `script` (Bitcoin-style Script on byte strings, separate from the stack machine), `programs` (vending machine, BEC batch transfer), and `reentrancy` (a Python model of the DAO). Independent of the ledger.
- `contracts`: `systems/world` is a world-state model of the EVM's call semantics: `World` (accounts, per-contract storage, gas, `transact`/`deploy`/`view`, rollback of a reverted call and its sub-calls) and `Contract` (subclasses declare a `layout` of storage fields and write public methods; `call`, `delegatecall`, `send` with the 2,300 stipend, `create`/CREATE2, events, `selfdestruct`, and an `invariant` checked after every call). The other systems modules are contracts built on it, one family per history breakthrough (tokens, payments, randomness, wallets, proxies, factory, governance, ricardian, capabilities), and the verification tools (`hoare`, `symbolic`, `design_by_contract`, `fuzzing`) over the small language of `utils/expressions`. `symbolic_bytecode` executes `vm` programs symbolically.
- `economics`: incentives, fees and markets, as pure functions and seeded simulations, one systems module per family: `coordination` and `oracles` (focal points, SchellingCoin), `auctions` (Vickrey, Myerson) and `lmsr`, `rewards` (subsidy, halving, Nakamoto's double-spend incentive, using `consensus.attacker_success_probability`), `fee_only` (Carlsten), `mining_games` (a bounded MDP for a miner's best response, solved by bisection and relative value iteration), `fee_market` (EIP-1559 over a simulated mempool), `ordering` (priority gas auctions, sandwiches) and `pbs` (builder auctions over `consensus.StakeSampler`). `amm` (`ConstantProductPool`) and `lending` (Dai's `VaultEngine`, the bZx-style `OracleLender` and `OracleAttacker`) are contracts on `contracts.World`.
- `channels`: layer-2 scaling and interoperability, one systems module per family. Channel outputs are `vm.script` programs judged by `verify_script` (`utils/scripts`: 2-of-2 as two `OP_CHECKSIG`s, relative delays as `OP_CHECKLOCKTIMEVERIFY` against the output's age, since Script has no `OP_CHECKMULTISIG` or CSV): `micropayment` (Spilman), `duplex` (invalidation trees), `lightning` (revocation keys `S + B`, shachain via `structures.hash_chain`), `eltoo`, `swaps` (HTLCs). `relay` (`BTCRelay`), `state_channels` (Sprites' adjudicator and preimage manager) and `bridges` (Ronin, Wormhole) are contracts on `contracts.World`. `routing.ChannelNetwork` is built on `network.Graph`, and `probing` on it. `reed_solomon` (over `utils/field`) underlies `data_availability`; `plasma` uses `structures.SparseMerkleTree`; `rollups` has zk (a re-executing stand-in for a SNARK verifier) and optimistic (bisection) rollups; `sharding` has OmniLedger's committee risk and Atomix. `blockchainkit/__init__.py` imports `channels` before `consensus`, so `consensus.systems.fork_choice` imports `structures` only under `TYPE_CHECKING`.

- `proofs`: zero-knowledge and succinct proof systems, one systems module per breakthrough. `utils/polynomials` (coefficient tuples, Lagrange interpolation, the radix-2 FFT over the BabyBear field `FIELD_PRIME = 15 * 2**27 + 1`), `utils/transcript.Transcript` (Fiat-Shamir) and `utils/groups` are shared by everything. `pairing` is a symmetric reduced Tate pairing on `PAIRING_CURVE` (y**2 = x**3 + x over a 35-bit prime, subgroup order = `FIELD_PRIME`, built on `crypto.Curve`), used by `kzg`, `ceremony`, `groth16`, `plonk` and `zerocash` (a shielded pool proving with Groth16 over the R1CS of `circuits.Circuit`, hashing with MiMC). `bulletproofs` and `halo` work in `crypto.TEACHING_GROUP`; `fri` and `stark` commit with `structures.MerkleTree`; `kilian` commits the Hadamard PCP of `pcp` the same way. Interactive protocols (`sumcheck`, `ip_pspace`, `pcp`, `kilian_argument`) draw the verifier's challenges from a seed; non-interactive ones from a `Transcript`.
- `fraud`: financial fraud on and around blockchains, one systems module per family. `ponzi` (Ponzi's and BitConnect-style simulations, the `ChainPonzi` contract, `value_flows`/`ponzi_features` over receipts), `benford`, `reserves` (Maxwell's proofs of liabilities over `utils/merkle_sum.MerkleSumTree`), `provisions` (Pedersen commitments with CDS OR proofs and bitwise range proofs), `custody` (Mt. Gox's `reissue_missing`, FTX's `Custodian`), `verification`, `token_sales` (DAICO), `honeypots` (Torres et al.; the Solidity quirks are reproduced by effect, never compiled), `rug_pulls` (`sell_test` uses `World.fork()`), `manipulation`, `wash_trading` (rings via `network.Graph`), `phishing` and `poisoning`. Scam contracts run on `contracts.World`; each scam example's docstring shows the Solidity the victim reads.

Determinism is a design requirement: randomness comes from explicit seeds, and signing takes an explicit `signing_nonce`.

## Conventions

- Changing hash domains, serialization, validation, or tie-breaking changes consensus behavior: update `docs/source/protocol.rst`, tests, examples, and `CHANGELOG.md` together.
- Coverage is 100% (enforced in `pyproject.toml`); add real boundary and failure tests, never exclusions. Tests use `hypothesis` for property tests and check independent vectors, algebraic identities, or failure behavior.
- Math single-letter names (`n`, `k`, `x`, `p`, `q`) are intentional; see the ruff ignores in `pyproject.toml`.
- Public functions need type annotations and NumPy-style docstrings. Sphinx uses napoleon with `nitpicky`, so new types referenced in docstrings may need `napoleon_type_aliases` or `nitpick_ignore` entries in `docs/source/conf.py`. New algorithms cite their source.
- History is a first-class deliverable. There is one page per subpackage, `docs/source/history/<subpackage>_breakthroughs.rst`, with at least 15 breakthroughs. Entries follow mathematicskit's form: a `YEAR -- Title` heading that names the breakthrough, prose on the original problem and key mechanism with a `.. math::` block, an *Implementation:* line that links the API and states how the teaching version differs from the deployed protocol, a *References:* line citing a primary source, and `.. minigallery::` linking its own gallery example(s). Each page opens with an epigraph. No labelled sub-blocks, admonitions or doctests inside entries. No example is shared between two breakthroughs, and each example's title names its breakthrough. When the match is unclear, change the example, not the breakthrough.
- Tutorials (`docs/source/tutorials/`) and exercise pages (`docs/source/exercises/<subpackage>.rst`) use `.. doctest::`, so `make doctest` runs every line; exercise solutions sit in `.. dropdown::` boxes. An example's exercise cell ends with "A worked solution is in :doc:`/exercises/<subpackage>`." only if a worked solution exists.
- Examples live in `examples/<subpackage>/<topic>/plot_NN_<name>.py`, each topic folder with a `README.rst`; sphinx-gallery renders them under `docs/source/api/gallery/` (generated; never edit) and offers notebooks and JupyterLite. `notebooks/quickstart.ipynb` is the only committed notebook. Examples follow mathematicskit's layout: an `r"""` docstring with the title and plain paragraphs (no section headings), one `# %%` cell holding every import, then `# %%` sections with fixed seeds, small bounded searches and assertions, `plt.show()` closing the last figure cell, and a final `# Exercise` cell.

# Output Guidelines
- **Be Concise:** Provide direct code and answers first. Omit setup text, fluff, and conversational responses.
- **Code Generation:** Output only updated code blocks, functions, or unified diffs. Never output full files unless instructed.
- **Explanations:** Limit inline code comments. Explain high-level logic in 1–2 bullet points after the code block.
- **Format:** Use bulleted lists and tables for comparisons instead of paragraph blocks.