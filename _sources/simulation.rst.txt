Reproducible experiments and research scope
===========================================

This page is for readers ready to design their own experiments. A seed makes simulated
random choices repeatable; a peer graph describes who can talk to whom, and latency is
the delay before a message arrives. Begin with :doc:`/quickstart` if you have not yet run
a payment. A censored mining run below means a search stopped at its attempt limit
before finding an answer.

Record the model, not only the seed
-----------------------------------

Record the package and Python versions, peer graph, latency bounds, initial
balances, chain ID, mining difficulty, run length, and random seed. Seeded
sampling uses independent ``random.Random`` instances. Identical seeds and
inputs reproduce experiments within the same Python/runtime behavior; archived
research should record that environment rather than assume all future versions
produce identical streams.

Secret sharing and signing default to system randomness. Examples inject
fixed randomness only where necessary for reproducibility. Never infer a
cryptographic randomness guarantee from a reproducible simulation seed.

Three useful experiments
------------------------

**Propagation and topology.** Compare a line, ring, and complete graph under
the same latency distribution. Measure first-arrival times and event counts,
and repeat across seeds. ``deliveries`` includes local origin receipt; queued
events can include duplicates or messages later invalidated by a partition.
The simulator does not model bandwidth, packet sizes, queues inside links,
or network-level denial of service. Bandwidth is counted analytically by
``relay_cost`` and ``compact_block_relay``; peer discovery under attack is
modeled separately by ``AddressManager`` (eclipse attacks) and
``KademliaNetwork`` (Sybil identities). Both take global knowledge as given:
buckets and tables are filled at once, not learned from traffic.

**Mining variance.** Repeat searches using different headers at each difficulty.
Check the distribution, not just one sample. The expected geometric cost is
``2**difficulty``; a finite search budget can censor long searches. Record
timeouts as censored observations rather than dropping them from a reported
mean. The gallery uses small difficulties so all fixed fixtures complete.

**Stake concentration.** Compare empirical proposer frequencies to weight
fractions, with confidence intervals or repeated seeds. Integer sampling avoids
rounding weights into floating point. Sampling a proposer does not simulate
votes, long-range attacks, or randomness grinding; ``FinalityGadget`` models
Casper-style votes, slashing, and finality separately.

Forks and validation
--------------------

The chain accepts valid side branches and retains their state snapshots.
To simulate a reorganization, build forks from a shared parent, distribute
them to different peers, reconnect, and synchronize ancestors before descendants.
Validation is local and deterministic. The lexicographic tie-break is a teaching
choice; it should not be mistaken for a reproduction of a deployed chain.

The catch-up helper uses an infinite-horizon biased random walk from a known
deficit. It is not the finite-confirmation Poisson expression in the Bitcoin
paper, and it omits network delays and strategic mining. Label results with
these assumptions when using them in reports.

Extending the package
---------------------

A new model should specify inputs, state transition rules, observables, and
failure assumptions before optimization. Add one analytically checkable case,
invalid-input tests, and a seeded experiment. Prefer changes that expose one
new idea at a time. Full PoS consensus, BFT voting, zero-knowledge circuits,
rollups, threshold signing, and production clients are future work rather than
capabilities implied by the current interfaces.
