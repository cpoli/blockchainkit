# blockchainkit

**Cryptography and blockchain breakthroughs, explained through working Python.**

An educational toolkit for students, educators, and reproducible simulations.
Follow an idea from its historical motivation and mathematics to a small,
inspectable implementation, a plotted experiment, and a notebook you can change.
Inspired by physicskit's consistent domain APIs and history-to-code approach.
Conventionally imported as `bk`.

**New here? Start with [the beginner guide](docs/source/start_here.rst), then follow
[the guided course](docs/source/course.rst) and [exercise solutions](docs/source/solutions.rst).**

Read [the history chapter](docs/source/history.rst) alongside the lessons. Cryptography is
central: public-key exchange, RSA, threshold sharing, blind signatures, elliptic
curves, zero-knowledge intuition, and Schnorr signatures lead into Merkle trees,
proof of work, peer propagation, fork selection, stake sampling, and a teaching VM.

## Install locally

Requires Python 3.10+. The only runtime dependencies are Matplotlib and NumPy,
used by each subpackage's `visualizers`; `import blockchainkit` itself loads
only the standard library.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

For the package alone use `pip install -e .`; choose `[test]` or `[docs]` for
smaller optional tool sets. This is a local project;
no published PyPI distribution or hosted documentation is assumed.

## Quick start

```python
import blockchainkit as bk

alice_key, bob_key = 7, 11  # Fixed teaching keys, not application secrets.
alice = bk.structures.address(bk.crypto.public_key(alice_key))
bob = bk.structures.address(bk.crypto.public_key(bob_key))

tx = bk.structures.Transaction(bk.crypto.public_key(alice_key), bob, 25, 0)
tx = tx.signed(alice_key, signing_nonce=17)  # Never reuse a signing nonce.

genesis = bk.consensus.mine(bk.structures.Block(difficulty=5)).block
chain = bk.structures.Blockchain(genesis, bk.structures.Ledger({alice: 100}))
block = bk.structures.Block(genesis.hash, (tx,), height=1, timestamp=1, difficulty=5)
chain.add(bk.consensus.mine(block).block)
assert chain.state.balances[bob] == 25
```

See [the complete fork experiment](examples/structures/chain/plot_01_blockchain.py) to propagate
blocks between peers and observe how a reorganization changes account state.

## Subpackages

| Module | Working capabilities |
| --- | --- |
| `bk.crypto` | SHA-256, commitments, textbook DH/RSA, RSA blinding, Shamir sharing, curve arithmetic, Schnorr signatures and proof transcripts |
| `bk.structures` | Count-bound Merkle proofs, signed account transfers, immutable blocks, ledger snapshots, cumulative-work fork selection |
| `bk.consensus` | Bounded PoW mining and verification, a catch-up model, reproducible integer-weight proposer sampling |
| `bk.network` | Discrete-event gossip, configurable latency, partitions, duplicate suppression, receive callbacks |
| `bk.vm` | Deterministic 256-bit stack execution, storage, branches, gas and stack limits, atomic failure |

## Learn through experiments

The [gallery scripts](examples/), one folder per subpackage, cover key exchange
and RSA; secret sharing; Merkle proofs; blind signatures; curves; Schnorr and
nonce reuse; hashing; mining; gossip; a signed payment and fork; stake
weighting; execution limits; and the complete payment lifecycle. Each includes
assertions, a figure, observations, and an exercise. The documentation offers
every script as a downloadable notebook.

New here? [The quickstart notebook](notebooks/quickstart.ipynb) takes one payment
from a signature to a mined block in about ten minutes.

## Sphinx documentation

```bash
cd docs
MPLBACKEND=Agg make html
MPLBACKEND=Agg make doctest
```

Open `docs/build/html/index.html`. The build executes gallery examples and
fails on warnings or example errors. The documentation includes:

- [History](docs/source/history/index.rst): one page per subpackage; each milestone gives the mathematics, implementation links, experiments, and primary references.
- [Quick start](docs/source/quickstart.rst): a tested signed-payment walkthrough.
- [Protocol conventions](docs/source/protocol.rst): exact encodings, validation rules, and model boundaries.
- [Simulation guide](docs/source/simulation.rst): reproducibility and research assumptions.
- [API](docs/source/api/index.rst): one page per subpackage, generated from implementation docstrings.

## Verification and development

```bash
pytest --cov=blockchainkit --cov-report=term-missing
pytest --doctest-modules blockchainkit --ignore-glob="*/tests/*"
ruff check .
ruff format --check .
mypy
python -m build
```

Prepared CI runs tests on Python 3.10–3.14 on Linux and Python 3.12 on macOS,
with separate documentation, notebook, type-checking, lint, and build checks.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## Model boundaries

This is teaching software, not hardened cryptography or a production blockchain.
Tiny RSA/DH parameters and variable-time Python curve arithmetic expose the
mathematics. Schnorr encoding is not BIP-340; blocks are not Bitcoin/Ethereum
wire formats. PoS is proposer sampling, not a complete voting/finality protocol.
The VM is independent of the account-transfer ledger. Initial allocations are
shared simulation inputs, not committed in genesis. These choices are specified
in the documentation so experiments can state their assumptions precisely.

MIT license — see [LICENSE](LICENSE).

New to blockchains? Start with `docs/source/start_here.rst`, follow the worked payment in `quickstart.rst`, and use `glossary.rst` for unfamiliar terms. The history chapter includes plain-language explanations before the mathematics.
