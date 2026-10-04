# Roadmap

What blockchainkit does not do yet, in priority order. `PLAN.md` has the
detailed, phase-by-phase version.

blockchainkit now uses the kit-family layout: one subpackage per domain with
`core/`, `systems/`, `utils/` and `tests/`. It is not yet at parity with
mathematicskit on documentation and educational depth.

## 1. Code-review fixes

Mining rebuilds the Merkle tree on every nonce attempt, signature
verification repeats subgroup checks that prime-order curves don't need, and
a few inputs fail with the wrong exception type. Each fix comes with a
regression test.

## 2. APIs the experiments need

Execution and Merkle-proof traces, block-tree accessors, and a `visualizers/`
package per subpackage, so gallery examples stop re-implementing internals.

## 3. Documentation in the family's structure

Per-subpackage hubs, API pages, history pages, tutorials, and JupyterLite.

## 4. History: at least 15 breakthroughs per subpackage

Each breakthrough cites a primary source and has its own gallery example.
Today there is one history page with 15 milestones across all five
subpackages.

## 5. Tutorials and exercises

Cross-domain tutorials ("Nonces everywhere", "Hashes everywhere", "Who do
you trust?") and per-subpackage exercise pages with answers executed in the
docs build.

## 6. First release

Tag-driven PyPI release, docs on GitHub Pages, and a Zenodo DOI.
