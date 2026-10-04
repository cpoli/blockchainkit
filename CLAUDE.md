# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`blockchainkit` (imported as `bk`) is an educational, typed, pure-Python library (no runtime
dependencies, Python ≥3.10) teaching cryptography and blockchain ideas through a chain of
history → mathematics → small API → gallery experiment → notebook. It is deliberately *not*
production cryptography: tiny RSA/DH parameters, variable-time curve arithmetic, non-BIP-340
Schnorr, non-Bitcoin/Ethereum wire formats. Keep those model boundaries explicit.

## Commands

```bash
python -m pip install -e ".[dev]"          # full toolchain (extras: test, examples, notebooks, docs)
pytest --cov=blockchainkit --cov-branch --cov-report=term-missing   # must be 100% stmt+branch
pytest tests/test_vm.py::test_binary_semantics                     # single test
pytest --doctest-modules src/blockchainkit                         # module doctests
ruff check . && ruff format --check .       # line length 100; examples/ ignore E402
mypy                                        # strict, over src/blockchainkit only
python -m build

# Docs: executes every gallery example; warnings are errors (nitpicky = True)
sphinx-build -W --keep-going -b html docs/source docs/build/html
sphinx-build -W --keep-going -b doctest docs/source docs/build/doctest
python scripts/sync_notebooks.py            # copy generated notebooks → notebooks/ (needs HTML build first)
python scripts/verify_notebooks.py          # execute notebooks in fresh kernels → build/executed-notebooks/
```

Set `MPLBACKEND=Agg` for headless doc builds. CI (`.github/workflows/ci.yml`) also runs
`git diff --exit-code -- notebooks` after syncing, so committed notebooks must match the
regenerated ones.

## Architecture

Five subpackages under `src/blockchainkit/`, each re-exporting its public API from `__init__.py`:

- `crypto` — foundation layer. `number_theory.integer()` is the shared argument validator used
  across *all* subpackages (rejects bools/non-ints); `hashing.sha256` is the common hash.
  `signatures` builds Schnorr on `curves`.
- `structures` — `Transaction` (signed account transfers, `canonical_json` encoding) →
  `Block` (frozen dataclass; header commits to a `MerkleTree` root) → `Ledger` (immutable
  balances/nonces snapshot; `apply` returns a new ledger or raises, leaving the old one intact)
  → `Blockchain` (stores all valid blocks, selects the tip by cumulative work, recomputes state
  on reorg).
- `consensus` — `pow` (`mine`, `valid_pow`, `expected_trials`) and `pos.StakeSampler`.
  Note the layering: `structures.chain` imports `consensus.pow`, while `pow` refers to `Block`
  only via string annotations to avoid a cycle.
- `network` — `SimulatedNetwork`, a deterministic discrete-event gossip simulator (latency
  ranges, partitions, duplicate suppression by payload hash). Payloads are opaque bytes; it is
  not coupled to `structures`.
- `vm` — `execute()` over `(opcode, arg)` tuples; 256-bit modular stack machine with gas,
  storage, and atomic failure. Independent of the ledger.

Determinism is a design requirement: randomness comes from explicit seeds, and signing takes
an explicit `signing_nonce`.

## Conventions

- Changing hash domains, serialization, validation, or tie-breaking changes consensus
  behavior: update `docs/source/protocol.rst`, tests, examples, and `CHANGELOG.md` together.
- Coverage threshold is 100% (enforced in `pyproject.toml`); add real boundary/failure tests,
  never exclusions. Tests use `hypothesis` for property tests and should check independent
  vectors, algebraic identities, or failure behavior.
- Public functions need type annotations and NumPy-style docstrings (Sphinx uses napoleon with
  `nitpicky`, so new types referenced in docstrings may need `napoleon_type_aliases` or
  `nitpick_ignore` entries in `docs/source/conf.py`).
- `docs/source/history.rst` is a first-class deliverable: each milestone cites a primary
  source, explains the original problem and key mechanism, links to a concrete API and a
  working gallery experiment, and distinguishes original protocols from teaching adaptations.
- `examples/plot_*.py` are the single source of truth for experiments. Never edit
  `notebooks/*.ipynb` or `docs/source/gallery/` directly — they are generated. Examples use
  `# %%` cells, fixed seeds, small bounded searches, assertions, a "What to look for" section,
  and an exercise. Follow `docs/source/course.rst` for learning order, not filename order.
