# blockchainkit

| | |
|:--|:-:|
| Package | [![PyPI version](https://badgen.net/pypi/v/blockchainkit)](https://pypi.org/project/blockchainkit/) [![Python versions](https://img.shields.io/pypi/pyversions/blockchainkit)](https://pypi.org/project/blockchainkit/) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23134958.svg)](https://doi.org/10.5281/zenodo.23134958) |
| Quality | [![License](https://badgen.net/github/license/cpoli/blockchainkit)](https://github.com/cpoli/blockchainkit/blob/main/LICENSE) [![CI](https://github.com/cpoli/blockchainkit/actions/workflows/ci.yml/badge.svg)](https://github.com/cpoli/blockchainkit/actions/workflows/ci.yml) [![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](#development) |
| Documentation | [![Docs](https://img.shields.io/badge/docs-cpoli.github.io%2Fblockchainkit-blue)](https://cpoli.github.io/blockchainkit/) |
| Code style | [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) |
| Downloads | [![Downloads](https://static.pepy.tech/badge/blockchainkit)](https://pepy.tech/project/blockchainkit) [![Downloads/Month](https://static.pepy.tech/badge/blockchainkit/month)](https://pepy.tech/project/blockchainkit) |
| Community | [![GitHub Stars](https://badgen.net/github/stars/cpoli/blockchainkit)](https://github.com/cpoli/blockchainkit) [![GitHub Forks](https://badgen.net/github/forks/cpoli/blockchainkit)](https://github.com/cpoli/blockchainkit) [![Contributors](https://badgen.net/github/contributors/cpoli/blockchainkit)](https://github.com/cpoli/blockchainkit/graphs/contributors) [![Last Commit](https://badgen.net/github/last-commit/cpoli/blockchainkit/main)](https://github.com/cpoli/blockchainkit/commits/main) |
| Try it online | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cpoli/blockchainkit/blob/main/notebooks/quickstart.ipynb) [![JupyterLite](https://jupyterlite.rtfd.io/en/latest/_static/badge.svg)](https://cpoli.github.io/blockchainkit/lite/lab/) |

**Cryptography and blockchains, understood through experiments.**
blockchainkit is a Python toolkit for learning and teaching how blockchains
work, from the one-time pad to Ethereum's gas. Each idea is followed from its
history and mathematics to a small, typed, inspectable implementation, a
figure, and an experiment you can change. Every subpackage's documentation
walks through the field's breakthroughs in historical order, 120 of them in
all, each linked to the code and the gallery example that reproduce it.

![A Merkle proof, Nakamoto's double-spend probabilities, and a Lamport space-time diagram, all drawn with blockchainkit](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_hero.png)

- **For students:** recover a private key from a reused signing nonce, find
  hash collisions at the birthday bound, watch a fork undo a payment, mine
  selfishly, eclipse a node, drain a DAO-style contract, take over a
  Parity wallet, and sandwich a swap, in a few lines each.
- **For instructors:** seven subpackages, one consistent API, 121 gallery
  examples (each downloadable as a notebook or runnable in the browser),
  exercise pages with worked solutions, and cross-cutting tutorials.
- **Honest about its limits:** tiny keys, variable-time arithmetic and
  simplified formats keep the mathematics visible. Every adaptation is marked
  on its history entry and specified in the
  [model boundaries](https://cpoli.github.io/blockchainkit/protocol.html).
  This is teaching software, not a wallet or a node.

`import blockchainkit` loads only the standard library. Matplotlib and NumPy
are used only by each subpackage's `visualizers`.

```bash
pip install blockchainkit   # Python 3.10+
```

Conventionally imported as `bk`:

```python
import blockchainkit as bk

alice_key = 7  # A fixed teaching key: never use such a key for real money.
alice = bk.structures.address(bk.crypto.public_key(alice_key))
bob = bk.structures.address(bk.crypto.public_key(11))

payment = bk.structures.Transaction(bk.crypto.public_key(alice_key), bob, 25, 0)
payment = payment.signed(alice_key, signing_nonce=17)  # Never reuse a signing nonce.

genesis = bk.consensus.mine(bk.structures.Block(difficulty=5)).block
chain = bk.structures.Blockchain(genesis, bk.structures.Ledger({alice: 100}))
block = bk.structures.Block(genesis.hash, (payment,), height=1, timestamp=1, difficulty=5)
chain.add(bk.consensus.mine(block).block)
assert chain.state.balances[bob] == 25
```

The [quickstart notebook](https://github.com/cpoli/blockchainkit/blob/main/notebooks/quickstart.ipynb)
takes one payment from a signature to a mined block in about ten minutes.
Open it in Colab using the badge above.

## Subpackages

- [`blockchainkit.crypto`](https://cpoli.github.io/blockchainkit/api/gallery/crypto/) -- the one-time pad,
  baby-step giant-step and Pohlig-Hellman, Merkle's puzzles, Diffie-Hellman and RSA, Shamir and Feldman
  secret sharing, Lamport signatures, birthday attacks, commitments (hash and Pedersen), blind signatures,
  elliptic curves, zero knowledge and Fiat-Shamir, Merkle-Damgård and length extension, HMAC, Schnorr
  signatures, RFC 6979 nonces, and MuSig. 22 breakthroughs.

  ![Scalar multiples on an elliptic curve, the SHA-256 avalanche, and the birthday bound](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_crypto.png)

- [`blockchainkit.structures`](https://cpoli.github.io/blockchainkit/api/gallery/structures/) -- double-entry
  ledgers, Bloom filters, Merkle trees and proofs, hash chains, linked and batched timestamps, the UTXO and
  account models, light clients, Bitcoin's duplicated-leaf bug, Certificate Transparency consistency proofs,
  transaction malleability, Merkle mountain ranges, replay protection, sparse Merkle trees, and blocks with
  cumulative-work fork choice. 15 breakthroughs.

  ![A Merkle proof, a fork in a block tree, and Bloom-filter false-positive rates](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_structures.png)

- [`blockchainkit.consensus`](https://cpoli.github.io/blockchainkit/api/gallery/consensus/) -- the gambler's
  ruin, Byzantine generals, Ben-Or and FLP, partial synchrony, PBFT, pricing functions and Hashcash, Nakamoto
  consensus and its double-spend calculation, difficulty retargeting, GHOST, selfish mining, proof of stake,
  nothing at stake, Casper FFG, and cryptographic sortition. 17 breakthroughs.

  ![Double-spend probabilities, selfish-mining revenue, and difficulty retargeting](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_consensus.png)

- [`blockchainkit.network`](https://cpoli.github.io/blockchainkit/api/gallery/network/) -- discrete-event
  gossip, random, small-world and scale-free graphs, Lamport and vector clocks, epidemic rumor spreading,
  Bracha's reliable broadcast, CAP, Kademlia, Sybil and eclipse attacks, inv/getdata relay, propagation and
  forks, compact blocks, and Dandelion. 17 breakthroughs.

  ![A small-world graph, push and pull gossip, and Kademlia lookup hops](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_network.png)

- [`blockchainkit.vm`](https://cpoli.github.io/blockchainkit/api/gallery/vm/) -- a deterministic 256-bit
  stack machine with gas and atomic failure, reverse Polish notation, Turing machines and the busy beaver,
  structured programming, Forth, state-machine replication, smart contracts, bytecode verification, Bitcoin
  Script with P2PKH and hash time-locked contracts, gas repricing, the DAO's reentrancy, and integer
  overflow. 16 breakthroughs.

  ![Stack height of two expressions, halting times of two-state Turing machines, and a reentrancy attack](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_vm.png)

- [`blockchainkit.contracts`](https://cpoli.github.io/blockchainkit/api/gallery/contracts/) -- a world-state
  model of contracts calling contracts, with Floyd-Hoare proofs, symbolic execution, design by contract,
  Ricardian contracts, capabilities and `tx.origin`, ERC-20 and its approval race, unchecked sends, gas
  denial of service, commit-reveal randomness, the two Parity wallet incidents, ERC-721, proxy storage
  collisions, CREATE2, Oyente and Echidna, and Beanstalk's flash-loan governance attack. 17 breakthroughs.

  ![The execution paths of a withdrawal, GovernMental's payout outgrowing the block, and push versus pull payments](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_contracts.png)

- [`blockchainkit.economics`](https://cpoli.github.io/blockchainkit/api/gallery/economics/) -- incentives,
  fees and markets: Schelling's focal points and SchellingCoin, Vickrey's and Myerson's auctions, Hanson's
  market scoring rule, block rewards and the halving, Bitcoin without the subsidy, mining games, EIP-1559,
  Dai and liquidation, Uniswap and impermanent loss, flash-loan oracle manipulation, priority gas auctions,
  sandwich attacks, and proposer-builder separation. 16 breakthroughs.

  ![EIP-1559's base fee during a demand surge, a miner's best response against honest miners, and sandwich profits against slippage tolerance](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_economics.png)

- [`blockchainkit.channels`](https://cpoli.github.io/blockchainkit/api/gallery/channels/) -- layer-2
  scaling and interoperability: Reed-Solomon codes, Spilman's and duplex channels, Lightning's revocation,
  Sprites and state channels, eltoo, watchtowers, balance probing, atomic swaps, BTC Relay, the Ronin and
  Wormhole exploits, Plasma, OmniLedger sharding, zk and optimistic rollups, and data-availability
  sampling. 16 breakthroughs.

  ![Light clients detecting withheld data, collateral locked by Lightning and Sprites routes, and a rollup's gas per transfer](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_channels.png)

- [`blockchainkit.proofs`](https://cpoli.github.io/blockchainkit/api/gallery/proofs/) -- zero-knowledge
  and succinct proofs: the Schwartz-Zippel lemma, sum-check, IP = PSPACE, the PCP theorem, Kilian's and
  Micali's arguments, KZG commitments, QAPs and Pinocchio, Zerocash, Groth16, trusted-setup ceremonies,
  Bulletproofs, FRI, STARKs, PLONK, and Halo. 16 breakthroughs.

  ![How often a random test is fooled by a polynomial's roots, STARK proof size against computation length, and range-proof sizes](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_proofs.png)

- [`blockchainkit.fraud`](https://cpoli.github.io/blockchainkit/api/gallery/fraud/) -- financial fraud on
  and around blockchains: Ponzi's scheme, Benford's law, Maxwell's proof of reserves, Mt. Gox and the
  malleability excuse, Provisions, deceptive verified sources, Ethereum's Ponzi contracts, ICO exit scams and
  the DAICO, the Willy bot, BitConnect, honeypots, pump-and-dumps, the Squid Game rug pull, NFT wash trading,
  ice phishing, FTX, and address poisoning. 17 breakthroughs.

  ![A Ponzi scheme's deposits and payouts until its collapse, invented amounts against Benford's law, and a pump-and-dump flagged by its spike](https://raw.githubusercontent.com/cpoli/blockchainkit/main/docs/source/_static/images/readme_fraud.png)

## Learn

- [Start here](https://cpoli.github.io/blockchainkit/start_here.html): the ideas, with one imaginary
  payment and no prerequisites.
- [Guided course](https://cpoli.github.io/blockchainkit/tutorials/course.html): seven lessons in
  prerequisite order.
- Tutorials across subpackages: [life of a payment](https://cpoli.github.io/blockchainkit/tutorials/life_of_a_payment.html),
  [nonces everywhere](https://cpoli.github.io/blockchainkit/tutorials/nonces_everywhere.html),
  [hashes everywhere](https://cpoli.github.io/blockchainkit/tutorials/hashes_everywhere.html), and
  [who do you trust?](https://cpoli.github.io/blockchainkit/tutorials/who_do_you_trust.html)
- [Exercises](https://cpoli.github.io/blockchainkit/exercises/index.html): worked solutions, checked by
  every documentation build.
- [History](https://cpoli.github.io/blockchainkit/history/index.html): the breakthroughs, each with
  plain-language explanation, mathematics, primary references, and its own experiment.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest --cov=blockchainkit --cov-branch          # 100% statement and branch coverage, enforced
pytest --doctest-modules blockchainkit --ignore-glob="*/tests/*"
ruff check . && ruff format --check .
mypy                                              # strict
cd docs && MPLBACKEND=Agg make html && MPLBACKEND=Agg make doctest
```

The documentation build runs every gallery example and every code line in
the tutorials and exercise solutions, and treats warnings as errors. The README
figures are regenerated with `python docs/make_readme_figure.py` and
`python docs/make_readme_subpackage_figures.py`. See
[CONTRIBUTING.md](CONTRIBUTING.md).

blockchainkit belongs to a family of teaching toolkits with the same
architecture: [mathematicskit](https://github.com/cpoli/mathematicskit),
[physicskit](https://github.com/cpoli/physicskit) and
[chemistrykit](https://github.com/cpoli/chemistrykit).

MIT license; see [LICENSE](LICENSE). To cite blockchainkit, see
[CITATION.cff](CITATION.cff).
