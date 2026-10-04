Start here: a blockchain without the jargon
===========================================

You do not need a background in cryptography or finance to read this course.
Basic Python helps when running the experiments, but you can first read the
explanations and figures without running anything.

A shared payment notebook
-------------------------

Imagine Alice, Bob, and Carol keeping copies of a payment notebook. Alice
starts with 100 imaginary units and pays Bob 25. Everyone should eventually
record Alice's balance as 75 and Bob's as 25. There is no real money involved.
The interesting part is deciding which updates to accept:

* **Did Alice authorize this exact payment?** A digital signature lets other
  people check authorization using Alice's public key.
* **Has a record changed?** A hash is a short fingerprint of its contents.
* **Is a payment in this batch?** A Merkle proof checks membership against a
  fingerprint of the whole batch, called its root.
* **How does Carol hear about it?** Peers (participating computers) pass
  announcements to their neighbors.
* **What if two valid batches conflict?** Consensus rules determine which
  updates are valid and how participants choose between competing histories.

A **block** is a batch of records plus information about that batch. It includes
the previous block's fingerprint: these links form a **blockchain**. The
**ledger** is the accounting state, including balances, obtained by applying
the accepted payments.

Try a fingerprint
-----------------

.. doctest::

   >>> import blockchainkit as bk
   >>> original = bk.crypto.sha256(b"Alice pays Bob 25")
   >>> changed = bk.crypto.sha256(b"Alice pays Bob 250")
   >>> original == changed
   False
   >>> len(original)
   32

The ``b`` prefix tells Python to treat the text as bytes, the format accepted
by this hash function. ``False`` means the fingerprints differ. Both have the
same length: SHA-256 produces 32 bytes (256 bits), regardless of input length.
A hash does not hide the message or identify its author. If somebody replaces
both a message and its fingerprint, you need a trusted earlier fingerprint
to detect the substitution.

Keys, signatures, and competing histories
-----------------------------------------

A **private key** is a secret value used to sign. Its related **public key**
lets others check signatures without knowing the secret. A valid signature
does not prove a person's real-world identity or that their account has enough
money. Those are separate questions. **Encryption** hides a message's contents;
signing authorizes a message without necessarily hiding it.

Two peers may temporarily extend different blocks because messages arrive
at different times. The resulting split is a **fork**; it need not indicate
fraud. In this package's proof-of-work model, **mining** means searching for
a block fingerprint that meets a numerical target. Peers validate blocks and
choose the history with the greatest cumulative work. Changing to a competing
history is a **reorganization**, which can change balances even though an
earlier payment's signature still verifies.

For a structured sequence with objectives and checked answers, follow
:doc:`/tutorials/course` and :doc:`/tutorials/solutions`.

A suggested learning route
--------------------------

1. Read :doc:`/api/gallery/crypto/hashing/plot_04_sha256_avalanche` for fingerprints.
2. Read :doc:`/api/gallery/structures/merkle/plot_01_merkle_proofs` for checking a batch efficiently.
3. Follow :doc:`/quickstart` to make one payment.
4. Explore :doc:`/api/gallery/network/events/plot_01_discrete_event_simulation` and :doc:`/api/gallery/consensus/nakamoto/plot_01_longest_chain`
   to see delayed messages and competing histories.
5. Read :doc:`/history/index` to connect these tools to their original breakthroughs.

Use the :doc:`/glossary` whenever a term is unfamiliar. The equations in the
history chapter are optional on a first reading. The API and protocol pages
are references for later, rather than prerequisites.

In code examples, ``>>>`` marks Python input; the line below is the expected
output. Do not copy the ``>>>`` into a script. An ``assert`` checks a claim:
silence means the check passed; an error means it failed.

These experiments use simulated peers and imaginary balances. They do not
connect to a live blockchain. See :doc:`/protocol` for the model's boundaries.
