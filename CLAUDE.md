# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An educational, typed Python toolkit for cryptography and blockchain systems: five domain subpackages (`crypto`, `structures`, `consensus`, `network`, `vm`) that follow each idea from its history and mathematics to a small API, a gallery experiment, and a notebook. Conventionally imported as `bk`. It is deliberately *not* production cryptography: tiny RSA/DH parameters, variable-time curve arithmetic, non-BIP-340 Schnorr, and non-Bitcoin/Ethereum wire formats. Keep those model boundaries explicit.

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

CI (`.github/workflows/ci.yml`) runs tests on Python 3.10-3.14, the quality checks, and the docs build (HTML and doctest).

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

Determinism is a design requirement: randomness comes from explicit seeds, and signing takes an explicit `signing_nonce`.

## Conventions

- Changing hash domains, serialization, validation, or tie-breaking changes consensus behavior: update `docs/source/protocol.rst`, tests, examples, and `CHANGELOG.md` together.
- Coverage is 100% (enforced in `pyproject.toml`); add real boundary and failure tests, never exclusions. Tests use `hypothesis` for property tests and check independent vectors, algebraic identities, or failure behavior.
- Math single-letter names (`n`, `k`, `x`, `p`, `q`) are intentional; see the ruff ignores in `pyproject.toml`.
- Public functions need type annotations and NumPy-style docstrings. Sphinx uses napoleon with `nitpicky`, so new types referenced in docstrings may need `napoleon_type_aliases` or `nitpick_ignore` entries in `docs/source/conf.py`. New algorithms cite their source.
- History is a first-class deliverable. There is one page per subpackage, `docs/source/history/<subpackage>_breakthroughs.rst`, with at least 15 breakthroughs. Each breakthrough cites a primary source, explains the original problem and key mechanism, links the API, distinguishes the original protocol from the teaching adaptation, and links its own gallery example(s) with `.. minigallery::`. No example is shared between two breakthroughs, and each example's title names its breakthrough. When the match is unclear, change the example, not the breakthrough.
- Tutorials (`docs/source/tutorials/`) and exercise pages (`docs/source/exercises/<subpackage>.rst`) use `.. doctest::`, so `make doctest` runs every line; exercise solutions sit in `.. dropdown::` boxes. An example's docstring ends with "The history behind this experiment: :doc:`/history/<subpackage>_breakthroughs`." and, only if the exercise has a worked solution, "See :doc:`/exercises/<subpackage>` for a worked solution to the exercise." History entries that adapt a deployed protocol carry a "Teaching vs production" admonition linking `/protocol`.
- Examples live in `examples/<subpackage>/<topic>/plot_NN_<name>.py`, each topic folder with a `README.rst`; sphinx-gallery renders them under `docs/source/api/gallery/` (generated; never edit) and offers notebooks and JupyterLite. `notebooks/quickstart.ipynb` is the only committed notebook. Examples use `# %%` cells, fixed seeds, small bounded searches, assertions, a "What to look for" section, and an exercise.
