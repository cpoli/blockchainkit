# blockchainkit: plan to align with the kit family

Goal: bring blockchainkit to the same structure as mathematicskit (and physicskit/chemistrykit),
make it clearer and more educational, and fix what the code review found. Phases are in
dependency order: each one builds on the one before it.

Baseline (4 October 2026): 112 tests pass, 100% statement and branch coverage, 13 gallery
examples, one history page with 15 milestones. The directory is **not a git repository**, and
the package is not on PyPI (the name `blockchainkit` is free).

---

## Decisions needed before starting

| # | Decision | Recommendation |
| --- | --- | --- |
| D1 | The family template puts `visualizers/` (matplotlib) inside each subpackage, so matplotlib becomes a runtime dependency. blockchainkit currently has none. | Follow the template: depend on `matplotlib>=3.6` and `numpy>=1.24`, import matplotlib only in `visualizers/`, and keep the crypto and protocol code stdlib-only. Update the README claim. |
| D2 | Five subpackages, each needing at least 15 history breakthroughs. `network` and `vm` are thin today. | Keep the five subpackages; the breakthrough lists below fit all five. Revisit a sixth (`channels`: HTLCs, Lightning) after 1.0. |
| D3 | Committed `notebooks/*.ipynb` plus the `sync_notebooks.py`/`verify_notebooks.py` scripts, versus the template's JupyterLite plus one `notebooks/quickstart.ipynb`. | Follow the template. blockchainkit is pure Python, so it runs in Pyodide without changes, which is the template's best case. |
| D4 | blockchainkit is stricter than the template (strict mypy, 100% coverage gate, ruff line length 100). | Keep the stricter settings; they cost nothing to keep. Match the template everywhere else. |
| D5 | Moving modules changes import paths. Nothing has been released, so there are no users to break. | Move freely before the first release. Keep the `bk.<subpackage>.<name>` re-exports stable. |

---

## Phase 0: Safety net (done)

1. `git init`, set `user.name cpoli374` / `user.email cpoli374@gmail.com` locally, and commit the
   current tree as the baseline. Extend `.gitignore` with `build/`, `dist/`, `.hypothesis/`,
   `docs/source/gallery/`, `docs/source/_generated/`, `docs/source/api/gallery/`, and
   `sg_execution_times.rst`.
2. Create `cpoli/blockchainkit` on GitHub (private until Phase 7).

## Phase 1: Repository structure (done)

Status: done. 130 tests (112 original + 18 package-level), 100% coverage, docs
build and doctests pass, and hashes, signatures and Merkle roots are byte-identical to
the baseline. Deferred, deliberately: `visualizers/` and the matplotlib `conftest.py`
move to Phase 3 with D1. Empty `utils/` packages are created only when they get
content. The `notebooks` extra and sync scripts stay until the docs move to JupyterLite
in Phase 4.

Target layout, copied from mathematicskit:

```
blockchainkit/
  __init__.py  py.typed  constants.py
  crypto/      {core/base.py, systems/, utils/, visualizers/, tests/}
  structures/  {...same...}
  consensus/   {...}
  network/     {...}
  vm/          {...}
  tests/       (package-level tests: version, __all__, imports)
conftest.py
docs/{Makefile, make.bat, make_readme_figure.py, source/}
examples/<subpackage>/<topic>/{README.rst, plot_NN_<breakthrough>.py}
notebooks/quickstart.ipynb
.github/workflows/{ci.yml, docs.yml, release.yml}
CHANGELOG.md CITATION.cff CLAUDE.md CODE_OF_CONDUCT.md CONTRIBUTING.md
LICENSE MANIFEST.in README.md ROADMAP.md SECURITY.md pyproject.toml
```

1. Switch from the `src/` layout to the flat layout. Exclude `tests` from the wheel, as in
   mathematicskit's `pyproject.toml`.
2. Split each subpackage into `core/base.py` (result dataclasses and ABCs), `systems/` (one module
   per family), `utils/`, and `visualizers/`. Proposed mapping:
   - `crypto`: `systems/{hashing, commitments, asymmetric, sharing, curves, signatures}.py`;
     move `number_theory.integer()` to `blockchainkit/_validation.py`, since all subpackages
     share it. `is_prime` goes to `crypto/utils/primes.py`.
   - `structures`: `systems/{merkle, transaction, block, ledger, chain}.py`. Split `Ledger` out of
     `chain.py`.
   - `consensus`: `systems/{pow, pos, catch_up}.py`; `core/base.py` holds `MiningResult`.
   - `network`: `systems/gossip.py`; `core/base.py` holds `Delivery`.
   - `vm`: `systems/stack_machine.py`; `core/base.py` holds `ExecutionResult` and `VMError`.
3. Move `tests/test_*.py` into each `<subpackage>/tests/` and split `test_boundary_cases.py` by
   subpackage.
4. Create `constants.py` as the single home for consensus-relevant constants that are now spread
   across files: hash-domain tags (`b"\x00"`, `b"\x01"`, `b"\x02"`, `"blockchainkit:commit:v1"`,
   `"blockchainkit:schnorr:v1"`), `WORD_MODULUS`, the 64-bit bounds, and `DEFAULT_CHAIN_ID`.
5. Add the template's top-level files: `CITATION.cff` (citing the release's own Zenodo *version*
   DOI, never the concept DOI), `CODE_OF_CONDUCT.md`, `SECURITY.md` (explaining that this is
   teaching code and not a place to report vulnerabilities in real systems), `ROADMAP.md`, and
   `conftest.py`. Fold `VALIDATION.md` into CHANGELOG/CONTRIBUTING and delete it.
6. Bring `pyproject.toml` in line with the template: classifiers for Python 3.10–3.15, Topic
   classifiers, `[project.urls]`, ruff ignores `E741` (single-letter math names) and `SIM`, and
   docs extras (`sphinx-design`, `jupyterlite-sphinx`, `jupyterlite-pyodide-kernel`,
   `sphinx-autodoc-typehints`). Remove the `notebooks` extra (D3).
7. Rewrite `CLAUDE.md` in mathematicskit's form: commands, layout, conventions, and the
   history/gallery rules.

Done when: `pytest`, doctests, ruff, mypy and `python -m build` pass with 100% coverage, the
wheel contains no `/tests/`, and `bk.crypto.sign` and the other public names are unchanged.

## Phase 2: Code-review fixes (done)

Status: done. R1–R9 and the clarity items are fixed, each with a regression test (157 tests,
100% coverage). Protocol outputs are byte-identical to the baseline. Mining a 20-transaction
block went from 118 µs to 2 µs per attempt; `verify` from 17 ms to 8 ms. R4 uses Hasse's
bound (`Curve.cofactor_is_one`) instead of a new `cofactor` field, so callers supply nothing
new and the rule is a theorem the docs can teach.

Measured or reproduced on the current code:

| # | Where | Problem | Fix |
| --- | --- | --- | --- |
| R1 | `consensus.pow.mine` + `Block.hash` | Every nonce attempt calls `replace()`, which rebuilds the Merkle tree from every transaction (re-encoding public keys and JSON). Mining a 20-transaction block runs **~18× slower per attempt** (110 µs vs 6 µs). It also teaches the wrong model: real miners hash only the header. | Make `Block.merkle_root` a `functools.cached_property` (this works on frozen dataclasses), and have `mine` build the header once and vary only the nonce. `Blockchain.add` computes `block.hash` up to three times; compute it once. |
| R2 | `Transaction.__post_init__` | Accepts any `signature` object. `Transaction(..., signature="junk")` builds, but `Block(...).hash` then raises `AttributeError`. | Check `signature is None or isinstance(signature, SchnorrSignature)`. |
| R3 | `vm.execute` | An unhashable opcode (for example `(["PUSH"], 1)`) raises `TypeError` instead of `VMError`. | Check `isinstance(op, str)` first. |
| R4 | `crypto.signatures.verify_transcript` | Checks subgroup membership with two full scalar multiplications per verification (~16 ms per `verify`). On prime-order curves (cofactor 1, true of both built-in curves), being on the curve already implies subgroup membership. `Ledger.apply` verifies every transaction, so syncing a chain is slow. | Add `cofactor: int = 1` to `Curve`, validate it, and skip the check when it is 1. Keep the check, and an example, for a custom curve with a cofactor. |
| R5 | `crypto.curves.Curve.__post_init__` | Allowlists both secp256k1 constants for *either* role, so `p = N` skips the primality check. | Allowlist by role: `p == _SECP_P` and `order == _SECP_N`. |
| R6 | `network.SimulatedNetwork._receive` | If the `on_receive` callback raises, the payload is already marked seen, so a retry is silently suppressed. | Mark the payload seen only after the callback returns, or document the behavior and test it. |
| R7 | `structures.chain.Blockchain.__init__` | Uses `initial_state or Ledger()`. That works today only because `Ledger` has no `__len__`, so it is fragile. | `Ledger() if initial_state is None else initial_state`. |
| R8 | `crypto.number_theory.integer` | Raises `ValueError` for wrong *types* (bool, str). | Raise `TypeError` for the type check and `ValueError` for the range check, consistently across the package. Update tests. |
| R9 | `consensus.pow.eventual_catch_up`, `StakeSampler`, `SimulatedNetwork` | `attacker_fraction` accepts `True`; `seed` is not validated. | Validate them with the shared helpers. |

Clarity-only changes (no behavior change):

- `rsa_unblind` calls `rsa_blind(...)` only for its validation side effect. Use an explicit
  `_check_blinding(...)` helper.
- `number_theory.py`'s docstring says "finite-field helpers", but the module holds validation and
  primality code.
- In `split_secret`, the comment "Include zero among coefficients…" is unclear. Explain that a zero
  leading coefficient is allowed because uniform sampling over all polynomials is what gives
  perfect secrecy.
- `Ledger` and `Transaction` both copy the 64-hex account check. Share `_check_account()`.
- `encode_point` is annotated `tuple[int, int]` but handles `None`. Annotate it `Point`.
- Repeated `assert arg is not None` in the VM loop: split operand and simple opcodes into two
  dispatch tables.
- Add `__repr__` to `Ledger`, `Blockchain`, `MerkleTree` and `SimulatedNetwork`. Printing them now
  shows an object address, which is unhelpful in notebooks.
- Document that `Blockchain` keeps a full `Ledger` per block (memory grows as blocks × accounts),
  as a deliberate teaching trade-off.

Each fix gets a regression test (TDD). Add a CHANGELOG entry and update `protocol.rst` wherever
validation changes.

## Phase 3: API additions the history pages need (done)

Status: done. 193 tests, 100% coverage. Names differ slightly from the sketch below:
`trace_proof` is a function returning a `MerkleTrace` (so `verify_proof` stays a plain
bool); the block-tree accessors are `blocks`, `tips()`, `work_at()`, `state_at()`;
`plot_proof_trace` and `plot_hamming_distances` were added; `plot_stack_trace` is
`plot_execution_trace`. Gas prices must be at least 1, so a loop always runs out of
gas. Examples 03 and 12 now use the trace APIs instead of re-hashing or replaying
prefixes.

The gallery currently re-implements internals that the library should expose:
`plot_03_merkle_proofs.py` hard-codes the `\x00/\x01/\x02` prefixes to trace a proof, and
`plot_12_execution.py` replays program prefixes, which by its own admission breaks with jumps.

Cross-cutting additions:
- `vm.execute(..., trace=True)` returning an `ExecutionTrace` (pc, opcode, stack, gas per step),
  plus an optional per-opcode gas schedule.
- `structures.verify_proof(..., trace=True)` or `MerkleTree.levels`, so examples never re-hash by
  hand.
- `Blockchain.blocks`, `Blockchain.get(hash)`, `Blockchain.forks()` to visualize the block tree.
- `visualizers/` per subpackage: `plot_merkle_tree`, `plot_block_tree`, `plot_gossip_timeline`,
  `plot_stack_trace`, `plot_curve_points`, `plot_mining_trials`, `plot_stake_shares`.

New per-breakthrough APIs are marked **new** in Phase 5. Each comes with NumPy docstrings, a
doctest, a cited source, and closed-form or independent-vector tests.

## Phase 4: Docs scaffold (template structure) (done)

Status: done. HTML (warnings as errors, `nitpicky`) and doctest builds pass from a clean
tree; JupyterLite builds. API pages document the full module paths, not only the
re-exports, so every cross-reference resolves under `nitpicky`. Each subpackage page
registers its package module, so `:mod:` links resolve. The 15 original milestones are split across
the history pages (crypto 8, structures 2, consensus 3, network 1, vm 1), each with a
*References:* line and a `minigallery`. Three examples are still shared by two
breakthroughs each; Phase 5 splits them. The JupyterLite and Colab install cells run
`%pip install blockchainkit`, so they work from the first PyPI release (Phase 7). Course
and solutions live in `tutorials/`; `start_here`, `quickstart`, `glossary`, `protocol` and
`simulation` stay at the top level under "Getting started" and "Model boundaries".

1. Copy mathematicskit's `docs/source/conf.py` machinery: generated subpackage hubs
   (`_generated/{nav,subpackages,grid_*.rst,vars.rst}`), `api/<subpackage>.rst`, `examples/index.rst`,
   `history/index.rst` + `history/<subpackage>_breakthroughs.rst`, `subpackages/index.rst`,
   `tutorials/`, the `minigallery` backreferences setup, JupyterLite with its install cell,
   `sphinx-design`, and `docs/Makefile`.
2. Keep blockchainkit's strengths in the new structure. Nothing is deleted without a new home:
   - `start_here.rst`, `quickstart.rst`, `glossary.rst` → top-level "Getting started" section.
   - `protocol.rst`, `simulation.rst` → "Model boundaries" section (they are the precise
     teaching-vs-production contract and deserve a top-level link).
   - `course.rst` + `solutions.rst` → `tutorials/` and per-subpackage exercise pages with answers
     in collapsed `sphinx-design` dropdowns, executed in the build.
   - `references.rst` → split into per-breakthrough *References* lines, the template's form.
3. `index.rst` in mathematicskit's form: intro, "important" box on teaching scope, one bullet and
   hero figure per subpackage, family links (physicskit, mathematicskit, chemistrykit, tbkit),
   install, and a `bk` snippet.

## Phase 5: History and gallery (the bulk of the work)

Rules (from the family conventions):
- One page per subpackage, `docs/source/history/<subpackage>_breakthroughs.rst`, with
  **at least 15 breakthroughs** each.
- Every breakthrough has **its own** gallery example(s), linked with `.. minigallery::`, whose
  titles name that breakthrough. No example is shared between breakthroughs. Today `plot_01` is
  shared by DH and RSA, `plot_06` by ZK and Schnorr, and `plot_10` by timestamping and Bitcoin, so
  each must be split.
- Each entry: date and name, the original problem, the key mechanism (with math), an
  *Implementation:* line linking the API, *References:* to a primary source, and a clear line
  between the original protocol and the teaching adaptation (current history.rst already does
  this well; keep its "plain language first" voice).
- Examples keep the existing house style: `# %%` cells, fixed seeds, bounded searches, asserts,
  "What to look for", and an exercise.

Candidate breakthroughs (✓ = API exists, **new** = Phase 3/5 API). Verify each date against its
primary source while writing; the list below is a draft.

**crypto** (20)
1. 1917/1949 One-time pad and perfect secrecy (Vernam; Shannon), **new** `xor_bytes`
2. 1971 Baby-step giant-step discrete logs (Shanks): why group size matters, **new**
3. 1974–78 Merkle's puzzles, **new** small simulation
4. 1976 Diffie–Hellman ✓
5. 1978 RSA ✓
6. 1978 Pohlig–Hellman: smooth group orders are weak, **new**
7. 1979 Shamir secret sharing ✓
8. 1979 Lamport one-time signatures (hash-based, post-quantum link), **new**
9. 1979 Yuval's birthday attack on truncated hashes, **new**
10. 1982 Chaum blind signatures ✓
11. 1985 Elliptic-curve groups (Miller; Koblitz) ✓
12. 1985 Zero knowledge and simulated transcripts (Goldwasser–Micali–Rackoff) ✓
13. 1986 Fiat–Shamir heuristic ✓ (`challenge`)
14. 1987 Feldman verifiable secret sharing, **new**
15. 1989 Merkle–Damgård construction and length extension, **new**
16. 1989–91 Schnorr signatures ✓
17. 1991 Pedersen commitments (hiding, binding, homomorphic), **new**
18. 1996 HMAC, **new** (stdlib `hmac`)
19. 2010–13 Nonce reuse in practice (PS3 ECDSA) and RFC 6979 deterministic nonces ✓ + **new**
20. 2018 MuSig key aggregation and the rogue-key attack, **new**

**structures** (16)
1. 1494 Pacioli's double-entry bookkeeping: conservation of supply, **new** `Ledger.total_supply`
2. 1970 Bloom filters (SPV wallets), **new** `BloomFilter`
3. 1979 Merkle trees ✓
4. 1981 Lamport hash chains, **new** `hash_chain`
5. 1991 Haber–Stornetta linked timestamps ✓
6. 1993 Bayer–Haber–Stornetta: batching into a Merkle root ✓
7. 2005 Content addressing (Git's Merkle DAG) ✓ `txid`
8. 2008 Bitcoin's UTXO model, **new** `UTXOSet`
9. 2008 Simplified payment verification (headers + proofs) ✓ + **new** header-only validation
10. 2012 CVE-2012-2459: duplicated-leaf Merkle ambiguity, and why roots bind the leaf count ✓
11. 2013 Certificate Transparency consistency proofs, **new** `MerkleTree.consistency_proof`
12. 2014 Account model and nonces (Ethereum) ✓ `Ledger`
13. 2014 Transaction malleability (Mt. Gox) → 2017 SegWit txid/wtxid, **new** `Transaction.wtxid`
14. 2016 EIP-155 replay protection ✓ `chain_id`
15. 2016 Sparse Merkle trees and state roots, **new**
16. 2016 Merkle mountain ranges (append-only accumulators), **new**

**consensus** (18)
1. 1656 Gambler's ruin (Pascal, Fermat, Huygens) ✓ `eventual_catch_up`
2. 1982 Byzantine generals, n ≥ 3f+1, **new** oral-messages simulation
3. 1983 Ben-Or randomized consensus (the way around FLP), **new**
4. 1985 FLP impossibility (shown with an adversarial scheduler on #3) ✓ network + **new**
5. 1988 Partial synchrony (Dwork–Lynch–Stockmeyer): timeouts, **new**
6. 1992 Pricing via processing (Dwork–Naor) ✓
7. 1997 Hashcash ✓ `mine`
8. 1999 PBFT quorums and quorum intersection, **new**
9. 2008 Nakamoto consensus: cumulative work ✓ `Blockchain`
10. 2008 Nakamoto's double-spend probability (whitepaper §11, Poisson), **new**
    `attacker_success_probability(q, z)`, contrasted with #1
11. 2009 Difficulty retargeting, **new** `retarget`
12. 2012 Peercoin proof of stake ✓ `StakeSampler`
13. 2013 GHOST fork choice, **new**
14. 2014 Selfish mining (Eyal–Sirer), **new** revenue formula + simulation
15. 2014 Nothing-at-stake and long-range attacks, **new** simulation
16. 2017 Cryptographic sortition (Algorand), **new** hash-based sortition
17. 2017 Casper FFG: checkpoints, 2/3 finality, slashing, **new**
18. 2019 HotStuff/Tendermint-style rotating-leader BFT, **new**

**network** (16)
1. 1959 Erdős–Rényi random graphs: connectivity threshold, **new** topology builders
2. 1961–65 Discrete-event simulation (GPSS; Tocher) ✓ event queue
3. 1978 Lamport logical clocks, **new**
4. 1985–87 Rumor spreading in log₂n + ln n rounds (Frieze–Grimmett; Pittel), **new**
5. 1987 Epidemic algorithms: anti-entropy vs rumor mongering (Demers et al.) ✓ + **new**
6. 1987 Bracha reliable broadcast, **new**
7. 1998 Small-world networks (Watts–Strogatz), **new**
8. 1999 Scale-free networks (Barabási–Albert), **new**
9. 2000/2002 CAP theorem (Brewer; Gilbert–Lynch) ✓ partitions
10. 2002 Kademlia XOR routing, **new**
11. 2002 Sybil attack (Douceur), **new** simulation
12. 2009 Inventory announcements (inv/getdata), **new**
13. 2013 Propagation delay and forks (Decker–Wattenhofer) ✓ + `consensus`
14. 2015 Eclipse attacks (Heilman et al.), **new** simulation
15. 2016 Compact blocks (BIP 152): bandwidth accounting, **new**
16. 2017 Dandelion: hiding a transaction's origin, **new**

**vm** (16)
1. 1924/1957 Polish notation → reverse Polish (Łukasiewicz; Hamblin) ✓
2. 1936 Turing machines and the halting problem: why gas exists ✓
3. 1961 Burroughs B5000 hardware stack ✓ + `stack_limit`
4. 1962 Busy beaver (Radó): bounded work, **new** program enumeration
5. 1966 Böhm–Jacopini: sequence, selection, iteration ✓ `JMP/JZ`
6. 1970 Forth stack words ✓ `DUP/SWAP/DROP`
7. 1978/1990 State-machine replication (Lamport; Schneider) ✓ determinism
8. 1981 Gray's transaction concept: atomicity ✓
9. 1994 Szabo smart contracts (the vending machine), **new** program library
10. 1995 Bytecode verification: static checks before running ✓ + **new** stack-depth analysis
11. 2009 Bitcoin Script and P2PKH, **new** `HASH256`, `CHECKSIG`, `EQUALVERIFY`
12. 2013–16 Hash time-locked contracts and payment channels, **new** time-lock opcode
13. 2014 Ethereum's 256-bit word and gas ✓
14. 2016 Gas repricing after DoS attacks (EIP-150), **new** gas schedule
15. 2016 The DAO and reentrancy, **new** host-call simulation
16. 2018 Integer overflow (BEC token): modular wraparound ✓

Progress: **crypto done** (22 breakthroughs, 22 dedicated examples; the shared DH/RSA,
ZK/Schnorr and hashing/commitment examples were split). Changes from the draft list:
Blum's coin flipping (1981) added for hash commitments; ElGamal not used. A brute-force
check over 1.7 million cases found and fixed a Pohlig-Hellman bug when the stated order
is a proper multiple of the base's order.

Total: about 86 breakthroughs, so about 75 new examples. Work one subpackage at a time (crypto →
structures → consensus → network → vm, the course's learning order). For each one: API → tests →
examples → history page. The docs build must pass before starting the next subpackage.

## Phase 6: Educational layer

1. Cross-domain tutorials (`docs/source/tutorials/`), in the style of mathematicskit's
   `eigenvalues_everywhere.rst`:
   - *Life of a payment* (today's `plot_13` capstone, expanded).
   - *Nonces everywhere*: signing nonce vs account nonce vs PoW nonce. They are three
     different ideas that share one name, and learners often confuse them.
   - *Hashes everywhere*: commitments, Merkle roots, PoW, addresses, sortition.
   - *Who do you trust?*: the trust assumption behind each mechanism (honest majority of hash power,
     2/3 honest stake, synchrony).
2. An exercise page per subpackage, 5–10 problems each, built on gallery examples. Solutions are
   in collapsed dropdowns and executed in the build (migrated from `solutions.rst`).
3. A "teaching vs production" callout on every history entry that adapts a protocol, linking to
   `protocol.rst`.
4. Generate README hero figures with `docs/make_readme_figure.py`, one per subpackage, as
   mathematicskit does.
5. A `notebooks/quickstart.ipynb` with a Colab badge.

## Phase 7: Release pipeline

1. Copy the CI layout: `ci.yml` (lint; tests on 3.10–3.15 × Linux/macOS; doctests; mypy;
   package build with `twine check` and no `/tests/` in the wheel), `docs.yml`, and a tag-driven
   `release.yml` (PyPI trusted publisher, GitHub Release from the CHANGELOG, gh-pages, Zenodo).
2. First release: `0.2.0`, after Phases 1–4 and at least two subpackages of Phase 5. Then add the
   CITATION.cff version DOI.
3. Later, a conda-forge recipe: name written out directly, no `name` in `context`.

## Verification at every phase

```bash
ruff check . && ruff format --check .
mypy blockchainkit
MPLBACKEND=Agg pytest -q --cov=blockchainkit --cov-branch     # 100% gate
MPLBACKEND=Agg pytest --doctest-modules blockchainkit --ignore-glob="*/tests/*"
cd docs && MPLBACKEND=Agg make html                            # runs every example; -W
python -m build && twine check --strict dist/*
```
