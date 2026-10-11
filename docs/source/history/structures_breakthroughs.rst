Breakthroughs in Authenticated Data Structures
==============================================

.. include:: /_generated/nav/structures.rst

.. epigraph::

   "We define an electronic coin as a chain of digital signatures."
   -- Satoshi Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*, 2008

A hash turns any record into a short fingerprint. Arranged in chains and
trees, fingerprints let anyone check that a history has not changed, or that
one record belongs to a large set, without trusting whoever stores it. This
chronology traces the ideas behind :mod:`blockchainkit.structures`, from
double-entry bookkeeping to sparse Merkle trees. Encodings are this package's
own; :doc:`/protocol` lists exactly where they depart from Bitcoin and
Ethereum.

.. contents:: Timeline
   :local:
   :depth: 1

1494 -- Double-Entry Bookkeeping: Value Is Moved, Never Created
---------------------------------------------------------------

Luca Pacioli's *Summa de arithmetica* (Venice, 1494) contained the first
printed description of the double-entry method used by Venetian merchants:
every entry is recorded as a debit in one account and an equal credit in
another. Since each entry adds the same amount to both sides, total debits
always equal total credits, and a transfer leaves the sum of all balances
unchanged. A one-sided entry, whether a slip or a fraud, therefore shows up as
books that do not balance:

.. math::

   \sum_{\text{accounts}} \text{debits} = \sum_{\text{accounts}} \text{credits},
   \qquad \sum_a b_a \ \text{is invariant under transfers.}

A blockchain ledger enforces this rule in code rather than by an accountant's
review: a transfer is valid only if it debits and credits the same amount, and
a batch is applied atomically or not at all. New money appears only through an
explicit issuance rule, such as Bitcoin's block reward.

*Implementation:* :attr:`blockchainkit.structures.systems.ledger.Ledger.total_supply`
and :meth:`blockchainkit.structures.systems.ledger.Ledger.apply`, which returns
a new ledger or raises without changing the old one.

*References:* L. Pacioli, *Summa de arithmetica, geometria, proportioni et
proportionalità*, Venice (1494), section *Particularis de computis et
scripturis*.

.. minigallery:: ../../examples/structures/ledger/plot_01_double_entry.py

1970 -- Bloom Filters: Compact, Approximate Membership
------------------------------------------------------

Burton Bloom showed that a small bit array can answer "have I seen this?" in
far less space than a list, at the price of sometimes answering yes for an item
it has never seen; it never answers no for one it has. Each item sets :math:`k`
hash-chosen bits of an :math:`m`-bit array, and a query checks those bits.
After :math:`n` insertions,

.. math::

   \Pr[\text{false positive}] \approx \left(1 - e^{-kn/m}\right)^{k}, \qquad
   k_{\text{opt}} = \frac{m}{n}\ln 2.

Bitcoin's BIP 37 (2012) let a light wallet send a full node a Bloom filter of
its addresses, so the node could forward only matching transactions; the false
positives were meant to hide which ones were the wallet's. Later analyses showed
that they leaked most of that privacy, and compact block filters (BIP 157/158)
reversed the roles: the node publishes a filter of each block's contents and
the wallet tests it locally, so the wallet never reveals its addresses.

*Implementation:* :class:`blockchainkit.structures.systems.bloom.BloomFilter`,
with :meth:`~blockchainkit.structures.systems.bloom.BloomFilter.false_positive_rate`
and :meth:`~blockchainkit.structures.systems.bloom.BloomFilter.optimal_hash_count`.
Bit positions come from SHA-256; BIP 37 filters use MurmurHash3 with a
per-filter tweak, and Bitcoin Core has since disabled them by default.

*References:* B. H. Bloom, *Space/Time Trade-offs in Hash Coding with Allowable
Errors*, Communications of the ACM 13(7), 422–426 (1970). `DOI
<https://doi.org/10.1145/362686.362692>`__.

.. minigallery:: ../../examples/structures/bloom/plot_01_bloom_filter.py

1979-1987 -- Merkle Trees and Compact Authentication
----------------------------------------------------

Checking that one record belongs to a large set should not require
downloading the whole set. Ralph Merkle's work on hash-based authentication
supplied a tree in which the hashes of two children determine their parent's
hash. Anyone who trusts the root can authenticate a leaf from the sibling
digests along its path: hashing upward from the leaf must reproduce the root.
A tree of :math:`n` leaves has depth :math:`\lceil\log_2 n\rceil`, so the
proof holds :math:`O(\log n)` digests, and forging one would require a hash
collision:

.. math::

   L_i=H(0\,\|\,m_i),\qquad
   N=H(1\,\|\,N_{\mathrm{left}}\,\|\,N_{\mathrm{right}}).

The different prefixes for leaves (0) and internal nodes (1) stop an internal
node from being passed off as a leaf. The verifier must already trust the root
by some independent means; the proof only connects the leaf to it.

*Implementation:* :class:`blockchainkit.structures.systems.merkle.MerkleTree`
and :func:`blockchainkit.structures.systems.merkle.verify_proof`, which checks
the leaf's payload, its position, the proof's shape, and the leaf count. The prefix bytes above are this package's domain
separation, not Merkle's format; the root also binds the leaf count, and an
unmatched node is promoted rather than duplicated.

*References:* R. C. Merkle, *Secrecy, Authentication, and Public Key Systems*,
PhD thesis, Stanford University (1979). `Author's bibliography
<https://ralphmerkle.com/merkleDir/papers.html>`__. R. C. Merkle, *A Digital
Signature Based on a Conventional Encryption Function*, CRYPTO '87, LNCS 293,
369–378 (proceedings 1988). `DOI <https://doi.org/10.1007/3-540-48184-2_32>`__.

.. minigallery:: ../../examples/structures/merkle/plot_01_merkle_proofs.py

1981 -- Lamport's Hash Chains and One-Time Passwords
----------------------------------------------------

Leslie Lamport proposed a way to log in over an insecure network without ever
sending a reusable password. Hash a secret :math:`n` times and give the server
only the result, :math:`H^n(s)`, as its stored anchor. The :math:`i`-th login
reveals :math:`H^{n-i}(s)`, the value with one hash fewer than the anchor; the
server checks it with a single hash and then stores it as the new anchor:

.. math::

   H\bigl(H^{n-i}(s)\bigr) = H^{n-i+1}(s) = \text{stored anchor}.

Passwords are thus used in the reverse of the order they were computed. A
captured password is useless: the server will next expect its preimage, and
computing that would require inverting :math:`H`. The scheme became
S/KEY (RFC 1760, 1995). Hash chains recur throughout this subject: Lamport's
one-time signatures, commit-reveal randomness beacons, and the hash-linked
records of the next entries.

*Implementation:* :func:`blockchainkit.structures.systems.hash_chain.hash_chain`
and :func:`blockchainkit.structures.systems.hash_chain.verify_one_time_password`.

*References:* L. Lamport, *Password Authentication with Insecure
Communication*, Communications of the ACM 24(11), 770–772 (1981). `DOI
<https://doi.org/10.1145/358790.358797>`__.

.. minigallery:: ../../examples/structures/hash_chains/plot_01_lamport_hash_chain.py

1991 -- Haber and Stornetta: Hash-Linked Timestamps
---------------------------------------------------

Haber and Stornetta asked how to prove when a digital document existed without
trusting its easily edited metadata, or a single timestamping service. Their
answer links each record :math:`x_i` (a document's hash and its time) to the
one before it by including the previous record's hash:

.. math::

   h_i=H(h_{i-1} \,\|\, x_i).

Editing an earlier record changes its hash and breaks every later link unless
all later records are recomputed too. The chain therefore makes tampering
*evident*, not impossible: a forger can rebuild the whole tail, and only a
trusted copy of a recent hash exposes the rebuild. Surety, the company Haber
and Stornetta founded, supplied that copy by printing a hash in *The New York
Times* every week from 1995; Bitcoin's proof of work instead makes rebuilding
the tail too expensive.

*Implementation:* :class:`blockchainkit.structures.systems.block.Block` hashes a
canonical header containing the parent hash, transaction root, height,
timestamp, difficulty, and mining nonce, so changing any of those fields
changes the block digest.

*References:* S. Haber and W. S. Stornetta, *How to Time-Stamp a Digital
Document*, Journal of Cryptology 3, 99–111 (1991). `DOI
<https://doi.org/10.1007/BF00196791>`__.

.. minigallery:: ../../examples/structures/timestamps/plot_01_linked_timestamps.py

1993 -- Batching Timestamps with a Merkle Tree
----------------------------------------------

Bayer, Haber and Stornetta made timestamping cheaper: instead of linking every
document into the chain, collect a round of documents into one Merkle tree and
link only its root. Each document keeps a short proof that it was part of its
round:

.. math::

   \text{record}_t = H(\text{record}_{t-1} \,\|\, \text{root}_t), \qquad
   |\pi_{\text{doc}}| = O(\log n).

This is precisely the structure of a block: a header linked to its predecessor
and committing to its transactions through a Merkle root. Bitcoin's whitepaper
cites both Haber-Stornetta papers, and OpenTimestamps uses the same batching
today to anchor arbitrary documents in Bitcoin.

*Implementation:* :class:`blockchainkit.structures.systems.block.BlockHeader`
holds a ``merkle_root``; :class:`blockchainkit.structures.systems.block.Block`
computes it from its transactions.

*References:* D. Bayer, S. Haber, and W. S. Stornetta, *Improving the
Efficiency and Reliability of Digital Time-Stamping*, in Sequences II: Methods
in Communication, Security and Computer Science, Springer, 329–334 (1993).
`DOI <https://doi.org/10.1007/978-1-4613-9323-8_24>`__.

.. minigallery:: ../../examples/structures/timestamps/plot_02_merkle_batching.py

2008 -- Bitcoin's Unspent-Output Model: Coins, Not Accounts
-----------------------------------------------------------

Bitcoin keeps no balances. Nakamoto defined an electronic coin as a chain of
digital signatures, each owner signing the coin over to the next. Concretely,
value lives in the unspent outputs of earlier transactions. A payment consumes
whole coins as inputs and creates new ones as outputs, returning any excess to
the payer as a change coin, as with banknotes (whitepaper, section 9). Outputs
may not exceed inputs, and the difference goes to the miner as a fee:

.. math::

   \sum_{\text{inputs}} v_i \ \ge\ \sum_{\text{outputs}} v_j, \qquad
   \text{fee} = \sum v_i - \sum v_j.

A coin is spent at most once; preventing a second spend of the same output is
what the rest of the system (timestamps, proof of work, longest chain) exists
to do. Transactions touching different coins are independent, so they can be
validated in parallel, and a wallet's balance is not stored anywhere: it is
computed as the sum of its coins.

*Implementation:* :class:`blockchainkit.structures.systems.utxo.UTXOSet` and
:class:`blockchainkit.structures.systems.utxo.UTXOTransaction`, with
:class:`blockchainkit.structures.core.base.OutPoint` and
:class:`blockchainkit.structures.core.base.Coin`; the account-based
:class:`blockchainkit.structures.systems.ledger.Ledger` is the alternative
model. Transactions are signed with this package's Schnorr over a canonical
encoding; Bitcoin locks outputs with scripts, signs with ECDSA or BIP-340, and
uses its own serialization.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008), sections 2 and 9. `Paper <https://bitcoin.org/bitcoin.pdf>`__.

.. minigallery:: ../../examples/structures/utxo/plot_01_utxo.py

2008 -- Simplified Payment Verification: Light Clients
------------------------------------------------------

A phone cannot store every block. Section 8 of the Bitcoin whitepaper describes
simplified payment verification: keep only the short header of each block,
check that the headers link and carry their proof of work, and ask for the
Merkle branch that places a transaction in one of them:

.. math::

   \text{accept}(tx) \iff \text{headers link and meet their targets} \ \wedge\
   \text{verify}(tx, \pi, \text{root}_h).

The client cannot check the transactions themselves. It assumes that most
hashing power is honest, and honest miners do not extend an invalid block, so
the chain with the most work is taken to be valid.
That trust assumption is the price of downloading kilobytes instead of the
whole chain.

*Implementation:* :func:`blockchainkit.structures.systems.headers.verify_header_chain`
checks links and proof of work over
:class:`blockchainkit.structures.systems.block.BlockHeader` values;
:func:`blockchainkit.structures.systems.merkle.verify_proof` checks inclusion.
Headers use this package's encoding, and difficulty counts leading zero bits;
Bitcoin headers are 80 bytes with a compact-encoded target.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008), section 8. `Paper <https://bitcoin.org/bitcoin.pdf>`__.

.. minigallery:: ../../examples/structures/spv/plot_01_light_clients.py

2012 -- CVE-2012-2459: Two Lists, One Root
------------------------------------------

Bitcoin's Merkle tree fills an odd level by duplicating its last node, with no
domain separation and no leaf count. In 2012 Forrest Voight reported that the
transaction lists :math:`(t_1, \dots, t_n)` and :math:`(t_1, \dots, t_n, t_n)`
therefore share a root:

.. math::

   \text{root}(a, b, c) = H\bigl(H(ab) \,\|\, H(cc)\bigr) = \text{root}(a, b, c, c).

Since a block header commits only to the root, appending a copy of the last
transaction gives an invalid block (it spends the same coins twice) with the
same block hash as the valid one. A node that received the mutated block first
marked that hash as invalid and then refused the valid block too: a
denial-of-service and chain-split risk, fixed by rejecting blocks with
duplicated transactions rather than by changing the tree. A tree avoids the
whole class with three rules: promoting an odd node unchanged removes the
duplication; binding the leaf count into the root makes lists of different
lengths give different roots; and distinct leaf and node prefixes close the
related trick of presenting an internal node as a leaf.

*Implementation:* :func:`blockchainkit.structures.systems.merkle.bitcoin_merkle_root`
reproduces Bitcoin's rule exactly, for comparison with
:class:`blockchainkit.structures.systems.merkle.MerkleTree`, which does all
three.

*References:* National Vulnerability Database, *CVE-2012-2459* (2012). `Record
<https://nvd.nist.gov/vuln/detail/CVE-2012-2459>`__.

.. minigallery:: ../../examples/structures/merkle/plot_02_duplicate_leaf.py

2013 -- Certificate Transparency: Proving a Log Only Appends
------------------------------------------------------------

After certificate authorities were compromised in 2011, Laurie, Langley and
Kasper designed Certificate Transparency: every certificate is appended to
public Merkle-tree logs, and browsers require proof of logging. A log promises
never to change or delete an entry. Anyone holding an earlier root can demand a
short proof that today's log still begins with that earlier log, unchanged: a
log of size :math:`n` proves that its first :math:`m` leaves form the earlier
tree with :math:`O(\log n)` subtree digests, from which the verifier recomputes
both roots:

.. math::

   \text{verify}(m, \text{root}_m, n, \text{root}_n, \pi) \Rightarrow
   D[0{:}m] \ \text{is a prefix of}\ D[0{:}n].

Monitors that gossip signed tree heads then detect a log that shows different
histories to different people.

*Implementation:* :meth:`blockchainkit.structures.systems.merkle.MerkleTree.consistency_proof`
and :func:`blockchainkit.structures.systems.merkle.verify_consistency` follow
RFC 6962 and RFC 9162 on a tree of the same shape. Because this package's
roots also bind the leaf count, they differ from Certificate Transparency's,
and the verifier cannot read the old tree's top digest off its root. When
:math:`m` is a power of two, the case where RFC 6962 omits that digest from
the proof, this package's proof therefore includes it.

*References:* B. Laurie, A. Langley, and E. Kasper, *Certificate
Transparency*, RFC 6962 (2013). `DOI <https://doi.org/10.17487/RFC6962>`__.

.. minigallery:: ../../examples/structures/merkle/plot_03_consistency_proofs.py

2014 -- Ethereum's Account Model and Transaction Nonces
-------------------------------------------------------

Ethereum keeps a balance per account, like a bank, instead of separate coins.
Its design (Buterin's whitepaper, formalized in Wood's yellow paper) keeps a
world state mapping each address to a balance and a nonce: the number of
transactions it has sent. A transaction from :math:`a` is valid only if it
carries the next number,

.. math::

   \text{tx.nonce} = \sigma[a].\text{nonce}, \qquad
   \sigma'[a].\text{nonce} = \sigma[a].\text{nonce} + 1,

so the same signed payment cannot be replayed: once applied, it carries a
nonce the account has already used. Accounts make balances and
smart-contract state simple; the cost is a strict per-sender order, where coins
allowed independent spends.

*Implementation:* :class:`blockchainkit.structures.systems.ledger.Ledger`
stores balances and next nonces and rejects replayed or out-of-order
transfers. Transactions are signed canonical JSON with a string chain ID;
Ethereum uses RLP encoding, recoverable ECDSA signatures, and gas fees.

*References:* G. Wood, *Ethereum: A Secure Decentralised Generalised
Transaction Ledger* (yellow paper, 2014), section 4. `Paper
<https://ethereum.github.io/yellowpaper/paper.pdf>`__.

.. minigallery:: ../../examples/structures/ledger/plot_02_account_nonces.py

2014-2017 -- Transaction Malleability and Segregated Witness
------------------------------------------------------------

A Bitcoin transaction's id was the hash of everything in it, including the
signature. Anyone relaying a transaction could re-encode or negate its ECDSA
signature (:math:`s \mapsto n-s`) and it would stay valid, so the
transaction's id changed while its effect did not, confusing anyone tracking
payments by id. In 2014 the Mt. Gox exchange blamed this malleability for lost
withdrawals; Decker and Wattenhofer's measurements found it explained only a
small part of the losses. Segregated witness (BIP 141, activated in 2017)
moved signatures into a separate "witness" excluded from the txid:

.. math::

   \text{txid} = H(\text{tx without witness}), \qquad
   \text{wtxid} = H(\text{tx with witness}).

A transaction names the outputs it spends by their parent's txid, so if the
parent's id can change before confirmation, the child becomes invalid. A fixed
id lets a transaction safely spend an unconfirmed parent, which payment
channels such as Lightning depend on.

*Implementation:* :attr:`blockchainkit.structures.systems.transaction.Transaction.txid`
covers the signature, like Bitcoin's original id;
:attr:`blockchainkit.structures.systems.transaction.Transaction.unsigned_id`
covers only the payload, like SegWit's txid. Only that key idea is modeled, not
Bitcoin's witness serialization, weight units or script versions.

*References:* C. Decker and R. Wattenhofer, *Bitcoin Transaction Malleability
and MtGox*, ESORICS 2014, LNCS 8713, 313–326 (2014). `DOI
<https://doi.org/10.1007/978-3-319-11212-1_18>`__. E. Lombrozo, J. Lau, and
P. Wuille, *Segregated Witness (Consensus layer)*, BIP 141 (2015). `BIP
<https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki>`__.

.. minigallery:: ../../examples/structures/transactions/plot_01_malleability.py

2016 -- Merkle Mountain Ranges: An Append-Only Accumulator
----------------------------------------------------------

Peter Todd described Merkle mountain ranges for OpenTimestamps: a list of
perfect Merkle trees of decreasing size, like the peaks of a mountain range.
With :math:`n` leaves written in binary as :math:`n = \sum_i 2^{e_i}`, the
range holds one tree of :math:`2^{e_i}` leaves for each term. Appending a leaf
adds a tree of size one and merges equal-sized neighbors, like carrying when
adding one in binary:

.. math::

   \#\text{peaks}(n) = \text{popcount}(n), \qquad
   \text{root} = H\bigl(n \,\|\, \text{peak}_1 \,\|\, \cdots \,\|\, \text{peak}_k\bigr).

Appending never rewrites an old peak, so existing proofs remain valid with at
most a few digests added, and it costs two hashes on average (one for the leaf,
about one for merges, just as incrementing a binary counter carries about once
on average). Grin and
other Mimblewimble chains commit to their outputs and headers this way, and
FlyClient light clients use mountain ranges over headers.

*Implementation:* :class:`blockchainkit.structures.systems.mmr.MerkleMountainRange`
and :func:`blockchainkit.structures.systems.mmr.verify_mmr_proof`. Peak
bagging binds the size and differs from deployed ranges (Grin, Zcash's
FlyClient), so roots are not interoperable.

*References:* P. Todd, *Merkle Mountain Ranges*, OpenTimestamps documentation
(2016). `Document
<https://github.com/opentimestamps/opentimestamps-server/blob/master/doc/merkle-mountain-range.md>`__.

.. minigallery:: ../../examples/structures/merkle/plot_04_mountain_ranges.py

2016 -- EIP-155: Replay Protection across Chains
------------------------------------------------

When Ethereum and Ethereum Classic split in July 2016, the same keys controlled
coins on both chains, and a transaction signed for one was valid on the other.
Transactions were replayed, moving users' funds on the chain they had not meant
to touch. Buterin's EIP-155 included the chain identifier in the signed data,
so a signature is valid on one chain only:

.. math::

   \sigma = \text{Sign}_x\bigl(H(\text{nonce}, \dots, \text{chain\_id})\bigr).

The account nonce prevents replay *in time* on one chain; the chain id prevents
replay *across* chains.

*Implementation:* :class:`blockchainkit.structures.systems.transaction.Transaction`
signs its ``chain_id``, and :class:`blockchainkit.structures.systems.ledger.Ledger`
accepts only transactions for its own chain. The chain ID is a string inside
the signed message; EIP-155 folds a numeric chain ID into the signature's
recovery value ``v``.

*References:* V. Buterin, *EIP-155: Simple Replay Attack Protection* (2016).
`EIP <https://eips.ethereum.org/EIPS/eip-155>`__.

.. minigallery:: ../../examples/structures/transactions/plot_02_replay_protection.py

2016 -- Sparse Merkle Trees: Committing to a Whole State
--------------------------------------------------------

Picture a Merkle tree with a slot for every possible 256-bit key, almost all
empty. Each key always lands in the same slot, so the root does not depend on
insertion order, and absence is provable: show that the key's slot is empty.
Such a tree has :math:`2^{256}` leaves, far too many to hash, but every empty
subtree of a given height has the same digest.
Laurie and Kasper used such trees for certificate revocation (2012); Dahlberg,
Pulls and Peeters made them efficient with caching and gave secure membership
and non-membership proofs. Precomputing the default digest of an empty
subtree of each height,

.. math::

   d_0 = 0^{256}, \qquad d_{h+1} = H(d_h \,\|\, d_h),

means that only the paths to stored keys are ever hashed. Committing to an entire state
with one root is how blockchains let light clients check balances; Ethereum
uses a related structure, the Merkle Patricia trie.

*Implementation:* :class:`blockchainkit.structures.systems.sparse_merkle.SparseMerkleTree`
and :func:`blockchainkit.structures.systems.sparse_merkle.verify_sparse_proof`
use a full-depth binary tree (256 levels by default); production state trees
(Ethereum's Patricia trie, Diem's Jellyfish) compress empty paths.

*References:* R. Dahlberg, T. Pulls, and R. Peeters, *Efficient Sparse Merkle
Trees: Caching Strategies and Secure (Non-)Membership Proofs*, NordSec 2016,
LNCS 10014, 199–215 (2016). `DOI <https://doi.org/10.1007/978-3-319-47560-8_13>`__.

.. minigallery:: ../../examples/structures/state/plot_01_sparse_merkle.py
