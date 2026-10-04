# Contributing

Keep the teaching chain intact: historical motivation, mathematical mechanism,
typed public API, checked example, and explicit model assumptions.

blockchainkit is organized as one subpackage per domain
(`blockchainkit/<name>/`), each with its own `core/` (shared types and result
dataclasses), `systems/` (concrete constructions and protocols, one module per
family), `utils/` (supporting helpers that are not a model themselves), and
`tests/` directory. Code shared by every subpackage lives at the top level:
argument validation in `_validation.py` and every consensus-relevant constant
(hash domain tags, encoding bounds, the default chain ID) in `constants.py`.
New material belongs in the subpackage it fits best, re-exported from that
subpackage's `__init__.py`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pre-commit install
```

## Required checks

```bash
ruff check .
ruff format --check .
mypy
pytest --cov=blockchainkit --cov-branch --cov-report=term-missing
pytest --doctest-modules blockchainkit --ignore-glob="*/tests/*"
sphinx-build -W --keep-going -b html docs/source docs/build/html
sphinx-build -W --keep-going -b doctest docs/source docs/build/doctest
python scripts/sync_notebooks.py
python scripts/verify_notebooks.py
python -m build
```

Coverage runs must reach 100% for statements and branches across all package
modules. `pyproject.toml` enforces this threshold for the CI coverage command.
Add meaningful boundary and failure tests; do not exclude code to meet the target.

The tests check independent vectors (SHA-256 test vectors, hand-computed curve
points), algebraic identities (Diffie-Hellman agreement, RSA and blinding
round-trips, Shamir reconstruction from every threshold subset), and failure
behavior (signature tampering, nonce reuse, malformed Merkle proofs, replayed
or overdrawn transfers, fork state restoration, VM resource limits). Passing
them shows the teaching models behave as documented; it is not a
cryptographic security audit.

## History is part of the implementation

`docs/source/history.rst` is a first-class deliverable. A new historical entry
must cite a primary source, explain the original problem, give the key equation
or mechanism, link to a concrete public API, and link to a working gallery
experiment. Distinguish original protocols from teaching adaptations. Do not
describe a proposed future feature as an implemented breakthrough.

Every public algorithm should have a clear docstring and type annotations.
Use NumPy-style parameter/return sections where they clarify the interface.
Tests should compare independent vectors, algebraic properties, conservation
laws, or failure behavior rather than merely asserting the function returns.

## Examples and notebooks

Edit `examples/plot_*.py`, not the generated notebooks. Separate explanation and
code with `# %%` cells. Use fixed simulation seeds, small bounded searches,
assertions of the expected result, and an exercise. Build Sphinx, then run
`scripts/sync_notebooks.py` to regenerate the notebook deliverables.
`scripts/verify_notebooks.py` executes notebooks in isolated kernels and writes
executed copies to `build/executed-notebooks/`, keeping source notebooks clean.

## Protocol changes

Changing hash domains, serialization, validation, or tie-breaking can change
consensus behavior. Update `docs/source/protocol.rst`, the relevant tests,
examples, and changelog together. Reproducibility is scoped to recorded inputs
and runtime versions; it is not a substitute for cryptographic randomness.
