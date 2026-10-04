# Local validation — 24 September 2026

Version: **0.1.0**. This package is built and checked locally; the prepared
GitHub Actions workflow has not been run on GitHub.

| Check | Result |
| --- | --- |
| Unit and property tests, Python 3.12.10 | 112 passed |
| Unit and property tests, Python 3.14.7 | 112 passed |
| Statement and branch coverage (Python 3.12 and 3.14) | 100% each |
| Module doctests | 14 passed |
| Sphinx doctest examples | 118 passed |
| Sphinx HTML build with warnings treated as errors | Passed |
| Executable Sphinx-Gallery experiments | 13 passed |
| Jupyter notebook execution in fresh kernels | 13 passed, all with inline figures |
| Ruff lint and formatting | Passed |
| Strict mypy checking | Passed for all 20 package source files |
| Wheel and source distribution | Built successfully |
| Wheel installation in a clean environment outside the checkout | Passed |

Tests cover SHA-256 vectors, finite-field and elliptic-curve identities, textbook
RSA, signature tampering and nonce reuse, Shamir reconstruction, Merkle proof
shape validation, replay rejection, atomic ledger updates, fork state restoration,
PoW bounds, stake sampling, local gossip behavior, partitions, and VM failure modes.

The history chapter was inspected in the browser, including rendered equations
and links. Gallery figures were also visually inspected. The two network
notebooks were re-executed after the final gossip correction.

The macOS sandbox emitted ipykernel shutdown diagnostics because it restricts
process enumeration. All notebook cells finished successfully and their saved
outputs contained no execution errors. These diagnostics did not affect results.

Python 3.10, 3.11, and 3.13 are included in the prepared CI matrix but were not
available for local execution. Educational algorithms and simplified simulations
have the boundaries documented in `docs/source/protocol.rst` and
`docs/source/simulation.rst`; these checks are not a cryptographic security audit.

## Beginner documentation review

Added a first-reading guide and glossary, expanded the payment walkthrough,
and added plain-language introductions to all 15 historical milestones and
observation guidance to all 12 experiments. The revised documentation passed
55 Sphinx doctests, all 12 gallery executions, and the HTML build with warnings
treated as errors. Notebook text was regenerated from the gallery scripts.
Example lint and formatting checks passed. Package algorithms were unchanged;
the unit, typing, coverage, and fresh-kernel results above are from the preceding
implementation validation. This was an editorial review, not a novice user study.

## Coverage completion

Added 46 boundary cases covering curve validation, subgroup membership,
Miller–Rabin witness handling, malformed proofs and accounts, unsigned payment
serialization, integer limits, and exact weighted-lottery boundaries.
On Python 3.12, all 765 measured statements and all 324 branches execute.
Python 3.14 also reports 100% (its executable-line accounting differs).
No coverage exclusions were added. The shared configuration now fails coverage
runs below 100%, including the prepared CI command. CI has not run remotely.

Two unreachable paths were simplified: the stake sampler now indexes cumulative
integer weights, and Merkle verification relies on its validated path length.
The full suite passes on both runtimes; module doctests, Ruff, and strict mypy
also pass. Documentation and gallery checks were rerun after these changes.

## Guided course extension

The new course, solutions, and lifecycle capstone pass 118 Sphinx doctests
and 13 gallery executions. HTML builds with warnings treated as errors.
The 112 package tests still pass with 100% statement and branch coverage.
Ruff lint and formatting pass. The three new trace figures were visually
inspected. No package runtime algorithms changed in this extension.
The pending queue is explicitly a one-payment teaching scenario; VM tracing
replays straight-line prefixes and is not a general debugger.

All 13 regenerated notebooks also executed successfully in fresh kernels.
Jupyter required local socket permission; sandbox process-enumeration warnings
at kernel shutdown did not prevent execution or produce cell errors.
