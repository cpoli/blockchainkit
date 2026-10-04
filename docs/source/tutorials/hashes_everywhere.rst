Hashes everywhere
=================

One function, SHA-256, does most of the work in blockchainkit. It is used for
at least six different jobs, and each job relies on a *different* property of
the hash. Knowing which property a design leans on tells you what breaks if
the hash is weakened.

.. list-table::
   :header-rows: 1
   :widths: 26 32 42

   * - Job
     - Property it needs
     - Where in blockchainkit
   * - Commit to a choice
     - hiding and binding
     - :func:`~blockchainkit.crypto.systems.commitments.commit`
   * - Summarize a list
     - collision resistance
     - :class:`~blockchainkit.structures.systems.merkle.MerkleTree`
   * - Name an account or a coin
     - collision resistance
     - :func:`~blockchainkit.structures.systems.transaction.address`, ``txid``
   * - Price a block
     - output unpredictable until computed
     - :func:`~blockchainkit.consensus.systems.pow.mine`
   * - Replace a verifier's random challenge
     - behaves like a random function
     - :func:`~blockchainkit.crypto.systems.signatures.challenge`
   * - Draw a fair lottery
     - uniform, unpredictable output
     - :func:`~blockchainkit.consensus.systems.sortition.sortition`

All snippets use ``import blockchainkit as bk``.

The one property underneath: avalanche
--------------------------------------

Change one bit of the input and about half of the 256 output bits flip, with
no visible pattern. Every job below builds on this.

.. doctest::

   >>> a = bk.crypto.sha256(b"pay Bob 25")
   >>> b = bk.crypto.sha256(b"pay Bob 26")
   >>> 100 < bk.crypto.hamming_distance(a, b) < 156
   True

Commitments: hiding and binding
-------------------------------

A commitment seals a choice now and reveals it later. It must *hide* the
choice until then (so a random salt goes in) and *bind* the committer to it (so
they cannot find a second opening, which needs collision resistance).

.. doctest::

   >>> salt = bytes(range(16))
   >>> sealed = bk.crypto.commit(b"heads", salt)
   >>> bk.crypto.verify_commitment(sealed, b"heads", salt)
   True
   >>> bk.crypto.verify_commitment(sealed, b"tails", salt)
   False

The same pattern appears inside signatures: the signer commits to
:math:`R = kG` before learning the challenge. See
:doc:`/api/gallery/crypto/commitments/plot_01_coin_flipping`.

Merkle roots: one hash for a whole list
---------------------------------------

A block header carries one 32-byte root for all its transactions, and a short
proof shows that any one transaction is included. Faking a proof would mean
finding a collision somewhere on the path.

.. doctest::

   >>> leaves = [f"tx {i}".encode() for i in range(1000)]
   >>> tree = bk.structures.MerkleTree(leaves)
   >>> proof = tree.proof(417)
   >>> len(proof.siblings), bk.structures.verify_proof(b"tx 417", proof, tree.root)
   (10, True)
   >>> bk.structures.verify_proof(b"tx 999 999", proof, tree.root)
   False

See :doc:`/api/gallery/structures/merkle/plot_01_merkle_proofs`.

Names: addresses and transaction IDs
------------------------------------

An address is the hash of a public key, and a transaction ID is the hash of
the transaction. Hashes make good names because two different things almost
never get the same one, and the name commits to the content.

.. doctest::

   >>> alice = bk.structures.address(bk.crypto.public_key(7))
   >>> len(alice), alice == bk.crypto.sha256(bk.crypto.encode_point(bk.crypto.public_key(7))).hex()
   (64, True)

Bitcoin's pay-to-public-key-hash locks coins to such a hash; the key itself is
revealed only when spending (:doc:`/api/gallery/vm/script/plot_01_p2pkh`). When
the name depends on something malleable, trouble follows:
:doc:`/api/gallery/structures/transactions/plot_01_malleability`.

Proof of work: a price nobody can shortcut
------------------------------------------

Since the output is unpredictable, the only way to find a header whose hash is
below a target is to try nonce after nonce. Checking the result takes one hash.

.. doctest::

   >>> block = bk.consensus.mine(bk.structures.Block(difficulty=10)).block
   >>> int.from_bytes(block.hash, "big") <= bk.consensus.target(10)
   True
   >>> block.hash.hex()[:2]  # 10 leading zero bits: the first byte is zero.
   '00'

See :doc:`/api/gallery/consensus/pow/plot_02_hashcash`.

Fiat-Shamir: a hash as the verifier
-----------------------------------

An interactive proof needs a verifier to pick a random challenge after the
prover commits. Hashing the commitment, the public key and the message produces
a challenge the prover cannot steer, turning the proof into a signature.

.. doctest::

   >>> public = bk.crypto.public_key(7)
   >>> signature = bk.crypto.sign(b"hello", 7, nonce=11)
   >>> c = bk.crypto.challenge(b"hello", signature.commitment, public)
   >>> c == bk.crypto.challenge(b"hello", signature.commitment, public)  # Anyone recomputes it.
   True
   >>> c != bk.crypto.challenge(b"hullo", signature.commitment, public)  # Bound to the message.
   True

See :doc:`/api/gallery/crypto/signatures/plot_02_fiat_shamir`.

Lotteries: sortition and node identifiers
-----------------------------------------

Reading a hash as a uniform number turns it into a fair, unpredictable die.
Algorand draws committees this way, and Kademlia places nodes in its
identifier space.

.. doctest::

   >>> seats = [bk.consensus.sortition(b"key", 100, 1000, 20, round_seed=bytes([r])) for r in range(200)]
   >>> 1.0 < sum(seats) / 200 < 3.0  # Expected 100 * 20 / 1000 = 2 seats per round.
   True
   >>> bk.network.node_id(b"my public key", 32) < 2**32
   True

When identities are cheap, an attacker can grind hashes to choose where its
Sybils land: :doc:`/api/gallery/network/overlays/plot_02_sybil_attack`.

What if the hash were broken?
-----------------------------

* A **collision** attack would break Merkle proofs, addresses and commitment
  binding: two different things would share a name.
* A **preimage** attack would let anyone open hash locks (HTLCs) and reverse
  hash chains.
* **Faster-than-brute-force** search would break proof of work's pricing, even
  without collisions.

Each failure hits different parts of a blockchain, which is why designs name
the property they depend on.
