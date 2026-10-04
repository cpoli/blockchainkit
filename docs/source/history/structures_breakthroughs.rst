Breakthroughs in Authenticated Data Structures
==============================================

.. include:: /_generated/nav/structures.rst

A hash turns any record into a short fingerprint. Arranged in chains and trees,
fingerprints let anyone check that a history has not changed, or that one
record belongs to a large set, without trusting whoever stores it. This
chronology traces the ideas behind :mod:`blockchainkit.structures`.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

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

**Experiment:** :doc:`/api/gallery/structures/chain/plot_01_blockchain` creates linked records and
two conflicting continuations. A hash link alone cannot make one history
authoritative: somebody can recompute an entire alternative chain. Anchoring,
publication, or consensus supplies additional assumptions. The timestamps here
are caller-chosen simulation integers, not trusted real-world time certificates.
This is the hash-linking lesson, not a reproduction of the full timestamp service.

*References:* S. Haber and W. S. Stornetta, *How to Time-Stamp a Digital
Document*, Journal of Cryptology 3, 99–111 (1991). `DOI
<https://doi.org/10.1007/BF00196791>`__.

.. minigallery:: ../../examples/structures/chain/plot_01_blockchain.py
