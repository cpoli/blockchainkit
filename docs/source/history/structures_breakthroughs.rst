Breakthroughs in Authenticated Data Structures
==============================================

.. include:: /_generated/nav/structures.rst

A hash turns any record into a short fingerprint. Arranged in chains and trees,
fingerprints let anyone check that a history has not changed, or that one
record belongs to a large set, without trusting whoever stores it. This
chronology traces the ideas behind :mod:`blockchainkit.structures`, from
double-entry bookkeeping to Merkle mountain ranges. Each entry has its own
experiment in the :doc:`gallery </api/gallery/structures/index>`.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

1494 — Double-entry bookkeeping: value is moved, never created
--------------------------------------------------------------

**In plain language.** Every payment is written down twice: taken from one
account and added to another. Adding up all accounts therefore always gives
the same total, so a mistake or a fraud shows up as books that do not balance.

**Reading the experiment.** The total supply is the sum of all balances. The
experiment applies hundreds of random transfers and checks that the sum never
moves, then submits a batch that overdraws an account.

Luca Pacioli's *Summa de arithmetica* (Venice, 1494) contained the first printed
description of the double-entry method used by Venetian merchants: each entry is
recorded as a debit in one account and an equal credit in another, so that

.. math::

   \sum_{\text{accounts}} \text{debits} = \sum_{\text{accounts}} \text{credits},
   \qquad \sum_a b_a \ \text{is invariant under transfers.}

A blockchain ledger enforces this rule in code rather than by an accountant's
review: a transfer is valid only if it debits and credits the same amount, and a
batch is applied atomically or not at all. New money appears only through an
explicit issuance rule, such as Bitcoin's block reward.

**Implementation:** :attr:`blockchainkit.structures.systems.ledger.Ledger.total_supply`
and :meth:`blockchainkit.structures.systems.ledger.Ledger.apply`, which returns a
new ledger or raises without changing the old one.

**Experiment:** the gallery example runs 300 random transfers with constant
supply and shows a failed batch leaving every balance untouched.

*References:* L. Pacioli, *Summa de arithmetica, geometria, proportioni et
proportionalità*, Venice (1494), section *Particularis de computis et scripturis*.

.. minigallery:: ../../examples/structures/ledger/plot_01_double_entry.py


1970 — Bloom filters: compact, approximate membership
-----------------------------------------------------

**In plain language.** A small array of bits can answer "have I seen this?"
using far less space than a list, at the price of sometimes answering yes for
something it has never seen. It never answers no for something it has.

**Reading the experiment.** m is the number of bits, k the number of positions
set per item, and n the number of items. The false-positive rate is measured
and compared with the formula.

Burton Bloom proposed setting :math:`k` hash-chosen bits of an :math:`m`-bit array
for each item and testing membership by checking those bits. After :math:`n`
insertions,

.. math::

   \Pr[\text{false positive}] \approx \left(1 - e^{-kn/m}\right)^{k}, \qquad
   k_{\text{opt}} = \frac{m}{n}\ln 2.

Bitcoin's BIP 37 (2012) let a light wallet send a full node a Bloom filter of its
addresses, so the node could forward only matching transactions; the false
positives were meant to hide which ones were the wallet's. Later analyses showed
that they leaked most of that privacy, and compact block filters (BIP 157/158)
reversed the roles: the node publishes a filter and the wallet tests it.

**Implementation:** :class:`blockchainkit.structures.systems.bloom.BloomFilter`,
with :meth:`~blockchainkit.structures.systems.bloom.BloomFilter.false_positive_rate`
and :meth:`~blockchainkit.structures.systems.bloom.BloomFilter.optimal_hash_count`.

**Experiment:** the gallery example filters a wallet's addresses and compares
measured false positives with Bloom's formula.

*References:* B. H. Bloom, *Space/Time Trade-offs in Hash Coding with Allowable
Errors*, Communications of the ACM 13(7), 422–426 (1970). `DOI
<https://doi.org/10.1145/362686.362692>`__.

.. minigallery:: ../../examples/structures/bloom/plot_01_bloom_filter.py


1979–1987 — Merkle trees and compact authentication
---------------------------------------------------

**In plain language.** You can check whether one payment belongs to a large batch
without downloading every payment. Keep the batch’s trusted fingerprint, then combine
the payment with a short trail of supporting fingerprints.

**Reading the experiment.** H means a hash function and the vertical double bar means
joining bytes. A leaf is a bottom-level item; parents combine child fingerprints.
Prefixes 0 and 1 distinguish hashing a record from hashing a pair of tree nodes.
“Canonical” below means the history currently selected by the chain rules.

Authenticating a large collection need not require sending the whole collection.
Merkle's work on public-key systems and hash-based authentication supplied a
tree construction in which hashes of children determine their parent's hash. A trusted root can authenticate a leaf using the
sibling digests on its path.

.. math::

   L_i=H(0\,\|\,m_i),\qquad
   N=H(1\,\|\,N_{\mathrm{left}}\,\|\,N_{\mathrm{right}}).

The prefix bytes above are blockchainkit's domain-separation convention,
not a claim about Merkle's original wire format. Our root additionally binds
the leaf count; an unmatched node is promoted rather than duplicated.

**Implementation:** :class:`blockchainkit.structures.systems.merkle.MerkleTree` and
:func:`blockchainkit.structures.systems.merkle.verify_proof` check index, shape,
payload, and count.

**Experiment:** :doc:`/api/gallery/structures/merkle/plot_01_merkle_proofs` measures logarithmic proof
size and rejects modified payloads. It also distinguishes two trust claims:
membership in a list is not proof that the list is valid or canonical.

*References:* R. C. Merkle, *Secrecy, Authentication, and Public Key Systems*,
PhD thesis, Stanford University (1979). `Author's bibliography
<https://ralphmerkle.com/merkleDir/papers.html>`__. R. C. Merkle, *A Digital
Signature Based on a Conventional Encryption Function*, CRYPTO '87, LNCS 293,
369–378 (proceedings 1988). `DOI <https://doi.org/10.1007/3-540-48184-2_32>`__.

.. minigallery:: ../../examples/structures/merkle/plot_01_merkle_proofs.py


1981 — Hash chains and one-time passwords
-----------------------------------------

**In plain language.** Hash a secret over and over and give the server only the
final result. Each time you log in, reveal the value one step earlier in the
chain. The server checks it by hashing once; a stolen password is useless,
because the next one is the value *before* it.

**Reading the experiment.** :math:`H^i(s)` means the seed hashed :math:`i` times.
The anchor is the last value the server accepted.

Leslie Lamport proposed this scheme for authenticating over an insecure network.
The server stores :math:`H^n(s)`; the :math:`i`-th login sends
:math:`H^{n-i}(s)`, accepted when

.. math::

   H\bigl(H^{n-i}(s)\bigr) = H^{n-i+1}(s) = \text{stored anchor}.

Producing the next password from a captured one would require inverting
:math:`H`. The scheme became S/KEY (RFC 1760, 1995). Hash chains recur throughout
this package's subject: Lamport's own one-time signatures, commit-reveal
randomness beacons, and the hash-linked records of the next entries.

**Implementation:** :func:`blockchainkit.structures.systems.hash_chain.hash_chain`
and :func:`blockchainkit.structures.systems.hash_chain.verify_one_time_password`.

**Experiment:** the gallery example logs in five times and shows a captured
password failing on replay.

*References:* L. Lamport, *Password Authentication with Insecure Communication*,
Communications of the ACM 24(11), 770–772 (1981). `DOI
<https://doi.org/10.1145/358790.358797>`__.

.. minigallery:: ../../examples/structures/hash_chains/plot_01_lamport_hash_chain.py


1991 — Hash-linked timestamps and tamper evidence
-------------------------------------------------

**In plain language.** Include the previous record’s fingerprint in each new record.
Editing an earlier record then breaks later links unless those records are recalculated
too. Detecting such changes still requires something trustworthy to compare against.

**Reading the experiment.** The subscript i means the current block, and i−1 the
preceding block. H hashes an encoded bundle containing the previous hash, the current
payment-batch root, and descriptive fields such as height and timestamp.

Haber and Stornetta investigated how to establish when a digital document
existed without trusting easily edited metadata. Linking commitments
to earlier records makes an alteration affect subsequent commitments.

.. math::

   h_i=H(\mathrm{encode}(h_{i-1},\mathrm{root}_i,\mathrm{metadata}_i)).

**Implementation:** :class:`blockchainkit.structures.systems.block.Block` hashes a
canonical header containing the parent hash, transaction root, height,
timestamp, difficulty, and mining nonce. Changing any of those fields changes
the block digest.

**Experiment:** :doc:`/api/gallery/structures/timestamps/plot_01_linked_timestamps`
links ten records, edits one, and shows every later link breaking. A hash link
alone cannot make one history authoritative: somebody can recompute an entire
alternative chain, which is why the latest hash must be widely witnessed. The
timestamps here are caller-chosen simulation integers, not trusted real-world
time certificates.

*References:* S. Haber and W. S. Stornetta, *How to Time-Stamp a Digital
Document*, Journal of Cryptology 3, 99–111 (1991). `DOI
<https://doi.org/10.1007/BF00196791>`__.

.. minigallery:: ../../examples/structures/timestamps/plot_01_linked_timestamps.py


1993 — Batching timestamps with a Merkle tree
---------------------------------------------

**In plain language.** Instead of linking every document into the chain one by
one, collect a round of documents, combine them into one Merkle root, and
timestamp only the root. Each document keeps a short proof that it was part of
that round.

**Reading the experiment.** One header timestamps a thousand documents through
its Merkle root; each document's proof has about :math:`\log_2 1000 \approx 10`
hashes.

Bayer, Haber and Stornetta improved their timestamping scheme by grouping the
documents of each round into a Merkle tree:

.. math::

   \text{record}_t = H(\text{record}_{t-1} \,\|\, \text{root}_t), \qquad
   |\pi_{\text{doc}}| = O(\log n).

This is precisely the structure of a block: a header linked to its predecessor
and committing to its transactions through a Merkle root. Bitcoin's whitepaper
cites both Haber–Stornetta papers. OpenTimestamps uses the same batching today to
anchor arbitrary documents in Bitcoin.

**Implementation:** :class:`blockchainkit.structures.systems.block.BlockHeader`
holds a ``merkle_root``; :class:`blockchainkit.structures.systems.block.Block`
computes it from its transactions.

**Experiment:** the gallery example timestamps 1000 documents with one root and
compares batched and linked record counts.

*References:* D. Bayer, S. Haber, and W. S. Stornetta, *Improving the Efficiency
and Reliability of Digital Time-Stamping*, in Sequences II: Methods in
Communication, Security and Computer Science, Springer, 329–334 (1993). `DOI
<https://doi.org/10.1007/978-1-4613-9323-8_24>`__.

.. minigallery:: ../../examples/structures/timestamps/plot_02_merkle_batching.py


2008 — Coins, not accounts: the unspent-output model
----------------------------------------------------

**In plain language.** Bitcoin keeps no balances. Money exists as separate coins,
each owned by someone. To pay, you hand over whole coins and get change back as a
new coin, just as with banknotes.

**Reading the experiment.** An outpoint names a coin: the transaction that
created it and the output's position. A transaction lists coins to consume and
new coins to create; the difference is the miner's fee.

Nakamoto defined an electronic coin as a chain of digital signatures, each owner
signing the coin over to the next. Transactions combine and split value with
multiple inputs and outputs (whitepaper, section 9):

.. math::

   \sum_{\text{inputs}} v_i \ \ge\ \sum_{\text{outputs}} v_j, \qquad
   \text{fee} = \sum v_i - \sum v_j.

A coin is spent at most once; preventing a second spend of the same output is
what the rest of the system (timestamps, proof of work, longest chain) exists to
do. Because transactions touching different coins are independent, they can be
validated in parallel, and a wallet's balance is just the sum of its coins.

**Implementation:** :class:`blockchainkit.structures.systems.utxo.UTXOSet` and
:class:`blockchainkit.structures.systems.utxo.UTXOTransaction`, with
:class:`blockchainkit.structures.core.base.OutPoint` and
:class:`blockchainkit.structures.core.base.Coin`. The account-based
:class:`blockchainkit.structures.systems.ledger.Ledger` is the alternative model.

**Experiment:** the gallery example pays with change, rejects a double spend, and
merges coins.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008), sections 2 and 9. `Paper <https://bitcoin.org/bitcoin.pdf>`__.

.. minigallery:: ../../examples/structures/utxo/plot_01_utxo.py


2008 — Simplified payment verification: light clients
-----------------------------------------------------

**In plain language.** A phone cannot store every block. It can store just the
short header of each one, check that the headers link and that miners did the
work, and ask for a proof that a payment sits inside one of them.

**Reading the experiment.** A header carries the previous block's hash, the
Merkle root of the transactions, and the proof-of-work nonce. The light client
downloads headers plus one Merkle proof.

Section 8 of the Bitcoin whitepaper describes simplified payment verification: a
user keeps the headers of the longest proof-of-work chain and obtains the Merkle
branch linking a transaction to a block,

.. math::

   \text{accept}(tx) \iff \text{headers link and meet their targets} \ \wedge\
   \text{verify}(tx, \pi, \text{root}_h).

The client cannot check the transactions themselves; it trusts that the heaviest
chain is valid because honest miners would not extend an invalid one. That trust
assumption is the price of downloading kilobytes instead of the whole chain.

**Implementation:** :func:`blockchainkit.structures.systems.headers.verify_header_chain`
checks links and proof of work over
:class:`blockchainkit.structures.systems.block.BlockHeader` values;
:func:`blockchainkit.structures.systems.merkle.verify_proof` checks inclusion.

**Experiment:** the gallery example verifies a payment from 20 headers and one
proof and compares the download with a full node's.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008), section 8. `Paper <https://bitcoin.org/bitcoin.pdf>`__.

.. minigallery:: ../../examples/structures/spv/plot_01_light_clients.py


2012 — Two lists, one root: the duplicated-leaf ambiguity
---------------------------------------------------------

**In plain language.** Bitcoin's Merkle tree fills an odd row by copying its last
node. So a list and the same list with its last item repeated get the same root,
and an attacker can present a block in a form the network wrongly rejects.

**Reading the experiment.** Each list size is tested: is ``[..., x]``
confusable with ``[..., x, x]``?

Bitcoin's tree duplicates the last node of any odd level before pairing, with no
domain separation and no leaf count. In 2012 Forrest Voight reported that the
transaction lists :math:`(t_1, \dots, t_n)` and :math:`(t_1, \dots, t_n, t_n)`
then share a root. A node receiving the mutated, invalid block marked its hash as
invalid, and later refused the valid block with the same hash: a
denial-of-service and chain-split risk, tracked as CVE-2012-2459 and fixed by
rejecting duplicated transactions.

.. math::

   \text{root}(a, b, c) = H\bigl(H(ab) \,\|\, H(cc)\bigr) = \text{root}(a, b, c, c).

blockchainkit's tree avoids the whole class: odd nodes are promoted unchanged,
leaves and nodes have different prefixes, and the root binds the leaf count.

**Implementation:** :func:`blockchainkit.structures.systems.merkle.bitcoin_merkle_root`
reproduces Bitcoin's convention for comparison with
:class:`blockchainkit.structures.systems.merkle.MerkleTree`.

**Experiment:** the gallery example finds the collision and maps which list sizes
are ambiguous.

*References:* National Vulnerability Database, *CVE-2012-2459* (2012). `Record
<https://nvd.nist.gov/vuln/detail/CVE-2012-2459>`__.

.. minigallery:: ../../examples/structures/merkle/plot_02_duplicate_leaf.py


2013 — Certificate Transparency: proving a log only appends
-----------------------------------------------------------

**In plain language.** A public log promises never to delete or change an entry.
Anyone holding yesterday's fingerprint of the log can demand a short proof that
today's log still contains yesterday's, unchanged, at its start.

**Reading the experiment.** The old and new roots summarize the log at two sizes.
The consistency proof lists the subtree hashes needed to rebuild both.

After certificate authorities were compromised in 2011, Laurie, Langley and
Kasper designed Certificate Transparency: every certificate is appended to public
Merkle-tree logs, and browsers require proof of logging. A log of size :math:`n`
proves that its first :math:`m` leaves are an earlier version with
:math:`O(\log n)` subtree digests, from which a verifier recomputes both roots:

.. math::

   \text{verify}(m, \text{root}_m, n, \text{root}_n, \pi) \Rightarrow
   D[0{:}m] \ \text{is a prefix of}\ D[0{:}n].

Monitors that gossip signed tree heads then detect a log showing different
histories to different people.

**Implementation:** :meth:`blockchainkit.structures.systems.merkle.MerkleTree.consistency_proof`
and :func:`blockchainkit.structures.systems.merkle.verify_consistency` follow
RFC 6962 and RFC 9162 (blockchainkit's tree has the same shape; because its roots
also bind the leaf count, a power-of-two old tree's digest is carried in the
proof).

**Experiment:** the gallery example proves a 600-entry log is a prefix of a
1000-entry one, rejects a rewritten history, and plots proof size.

*References:* B. Laurie, A. Langley, and E. Kasper, *Certificate Transparency*,
RFC 6962 (2013). `DOI <https://doi.org/10.17487/RFC6962>`__.

.. minigallery:: ../../examples/structures/merkle/plot_03_consistency_proofs.py


2014 — The account model and transaction nonces
-----------------------------------------------

**In plain language.** Ethereum keeps a balance per account, like a bank, instead
of separate coins. To stop the same signed payment from being replayed, every
account counts the transactions it has sent, and each transaction must carry
the next number.

**Reading the experiment.** The account nonce is the number of transactions the
sender has sent so far. A replay reuses an old nonce; a later transaction waits
for the gap before it.

Ethereum's design (Buterin's whitepaper, formalized in Wood's yellow paper) keeps
a world state mapping each address to a balance and a nonce. A transaction from
:math:`a` is valid only if

.. math::

   \text{tx.nonce} = \sigma[a].\text{nonce}, \qquad
   \sigma'[a].\text{nonce} = \sigma[a].\text{nonce} + 1.

Accounts make balances and smart-contract state simple; the cost is a strict
per-sender order, where coins allowed independent spends.

**Implementation:** :class:`blockchainkit.structures.systems.ledger.Ledger`
stores balances and next nonces and rejects replayed or out-of-order transfers.

**Experiment:** the gallery example rejects a replay, holds an out-of-order
transfer until its gap is filled, and plots nonce against balance.

*References:* G. Wood, *Ethereum: A Secure Decentralised Generalised Transaction
Ledger* (yellow paper, 2014), section 4. `Paper
<https://ethereum.github.io/yellowpaper/paper.pdf>`__.

.. minigallery:: ../../examples/structures/ledger/plot_02_account_nonces.py


2014–2017 — Transaction malleability and segregated witness
-----------------------------------------------------------

**In plain language.** A transaction's id was a fingerprint of everything in it,
including the signature. Someone relaying it could change the signature's form
without making it invalid, and so change its id, confusing anyone tracking
payments by id.

**Reading the experiment.** ``txid`` hashes the signed transaction;
``unsigned_id`` hashes only what was signed. The same payment is signed twice.

Bitcoin's ECDSA signatures could be re-encoded or negated (:math:`s \mapsto n-s`)
by third parties without invalidating them. In 2014 the Mt. Gox exchange blamed
this malleability for lost withdrawals; Decker and Wattenhofer's measurements
found it explained only a small part of the losses. Segregated witness (BIP 141,
activated in 2017) moved signatures into a separate "witness" excluded from the
txid:

.. math::

   \text{txid} = H(\text{tx without witness}), \qquad
   \text{wtxid} = H(\text{tx with witness}).

A fixed id let a transaction safely spend an unconfirmed parent, which payment
channels such as Lightning depend on.

**Implementation:** :attr:`blockchainkit.structures.systems.transaction.Transaction.txid`
covers the signature, like Bitcoin's original id;
:attr:`blockchainkit.structures.systems.transaction.Transaction.unsigned_id`
covers only the payload, like SegWit's txid.

**Experiment:** the gallery example re-signs one payment, shows the txid changing
and the unsigned id staying fixed.

*References:* C. Decker and R. Wattenhofer, *Bitcoin Transaction Malleability and
MtGox*, ESORICS 2014, LNCS 8713, 313–326 (2014). `DOI
<https://doi.org/10.1007/978-3-319-11212-1_18>`__. E. Lombrozo, J. Lau, and
P. Wuille, *Segregated Witness (Consensus layer)*, BIP 141 (2015). `BIP
<https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki>`__.

.. minigallery:: ../../examples/structures/transactions/plot_01_malleability.py


2016 — Merkle mountain ranges: an append-only accumulator
---------------------------------------------------------

**In plain language.** Keep a list of complete Merkle trees of shrinking sizes,
like mountains in a range. Adding an item adds a tiny tree and merges any two
trees of equal size, the way carrying works when you add one in binary.

**Reading the experiment.** The peaks are the roots of the perfect trees; there is
one for each 1-bit of the number of leaves. A merge combines two equal peaks.

Peter Todd described Merkle mountain ranges for OpenTimestamps. With :math:`n`
leaves written in binary as :math:`n = \sum_i 2^{e_i}`, the range holds one
perfect tree of :math:`2^{e_i}` leaves for each term:

.. math::

   \#\text{peaks}(n) = \text{popcount}(n), \qquad
   \text{root} = H\bigl(n \,\|\, \text{peak}_1 \,\|\, \cdots \,\|\, \text{peak}_k\bigr).

Appending never rewrites an old peak and costs two hashes on average. Grin and
Mimblewimble chains commit to their outputs and headers this way, and FlyClient
light clients use mountain ranges over headers.

**Implementation:** :class:`blockchainkit.structures.systems.mmr.MerkleMountainRange`
and :func:`blockchainkit.structures.systems.mmr.verify_mmr_proof`.

**Experiment:** the gallery example grows a range to 64 leaves, counts peaks and
merges, and proves an old leaf.

*References:* P. Todd, *Merkle Mountain Ranges*, OpenTimestamps documentation
(2016). `Document
<https://github.com/opentimestamps/opentimestamps-server/blob/master/doc/merkle-mountain-range.md>`__.

.. minigallery:: ../../examples/structures/merkle/plot_04_mountain_ranges.py


2016 — Replay protection across chains
--------------------------------------

**In plain language.** When one blockchain splits into two, the same keys control
coins on both. A payment signed for one chain could be copied onto the other.
Signing the chain's name into every transaction makes a signature valid on one
chain only.

**Reading the experiment.** ``chain_id`` is part of the signed payload; each
ledger accepts only its own.

When Ethereum and Ethereum Classic split in July 2016, transactions were valid on
both chains and were replayed, moving users' funds on the chain they had not
meant to touch. Buterin's EIP-155 included the chain identifier in the signed
data:

.. math::

   \sigma = \text{Sign}_x\bigl(H(\text{nonce}, \dots, \text{chain\_id})\bigr).

The account nonce prevents replay *in time* on one chain; the chain id prevents
replay *across* chains.

**Implementation:** :class:`blockchainkit.structures.systems.transaction.Transaction`
signs its ``chain_id``; :class:`blockchainkit.structures.systems.ledger.Ledger`
accepts only transactions for its own chain id.

**Experiment:** the gallery example signs a payment on one chain and shows it
rejected on the other and on replay.

*References:* V. Buterin, *EIP-155: Simple Replay Attack Protection* (2016).
`EIP <https://eips.ethereum.org/EIPS/eip-155>`__.

.. minigallery:: ../../examples/structures/transactions/plot_02_replay_protection.py


2016 — Sparse Merkle trees: committing to a whole state
-------------------------------------------------------

**In plain language.** Imagine a Merkle tree with a slot for every possible
account, almost all empty. Each account always lands in the same slot, so the
tree's root is the same however the accounts were added, and you can prove that
an account does *not* exist by showing its slot is empty.

**Reading the experiment.** Keys are hashed to a 256-bit position. Siblings that
are empty subtrees have fixed default digests, so a proof's interesting part is
about :math:`\log_2(\text{keys})` hashes.

Laurie and Kasper used sparse Merkle trees for certificate revocation (2012);
Dahlberg, Pulls and Peeters made them efficient with caching and gave secure
membership and non-membership proofs. With a precomputed default digest for an
empty subtree of each height,

.. math::

   d_0 = 0^{256}, \qquad d_{h+1} = H(d_h \,\|\, d_h),

only the paths to stored keys are ever computed. Committing to an entire state
with one root is how blockchains let light clients check balances; Ethereum uses
a related structure, the Merkle Patricia trie.

**Implementation:** :class:`blockchainkit.structures.systems.sparse_merkle.SparseMerkleTree`
and :func:`blockchainkit.structures.systems.sparse_merkle.verify_sparse_proof`.

**Experiment:** the gallery example commits to balances in two orders, proves a
balance and an absence, and counts the non-default siblings.

*References:* R. Dahlberg, T. Pulls, and R. Peeters, *Efficient Sparse Merkle
Trees: Caching Strategies and Secure (Non-)Membership Proofs*, NordSec 2016,
LNCS 10014, 199–215 (2016). `DOI <https://doi.org/10.1007/978-3-319-47560-8_13>`__.

.. minigallery:: ../../examples/structures/state/plot_01_sparse_merkle.py
