Exercises: ledgers and data structures
======================================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. Merkle proofs: position and size matter
------------------------------------------

From :doc:`/api/gallery/structures/merkle/plot_01_merkle_proofs`. Change the
leaf index or the leaf count in a proof and check verification.

.. dropdown:: Solution

   .. doctest::

      >>> from dataclasses import replace
      >>> tree = bk.structures.MerkleTree([b"a", b"b", b"c"])
      >>> proof = tree.proof(1)
      >>> bk.structures.verify_proof(b"b", proof, tree.root)
      True
      >>> bk.structures.verify_proof(b"b", replace(proof, index=0), tree.root)
      False
      >>> bk.structures.verify_proof(b"b", replace(proof, leaf_count=4), tree.root)
      False

   The index decides whether each sibling goes on the left or the right, and
   the count is bound into the root. A valid proof shows only that a leaf is
   in a committed list: not that a payment was authorized, funded, or final.

2. Duplicated leaves: two lists, one Bitcoin root
-------------------------------------------------

From :doc:`/api/gallery/structures/merkle/plot_02_duplicate_leaf`. Find a
length-6 list whose Bitcoin-style root equals that of a length-8 list.

.. dropdown:: Solution

   Six leaves make three pairs at the next level; Bitcoin duplicates the odd
   third pair. Appending a copy of the last *pair* to the list gives the
   same tree.

   .. doctest::

      >>> six = [bytes([i]) for i in range(6)]
      >>> eight = six + six[4:6]
      >>> bk.structures.bitcoin_merkle_root(six) == bk.structures.bitcoin_merkle_root(eight)
      True
      >>> bk.structures.MerkleTree(six).root == bk.structures.MerkleTree(eight).root
      False

   Binding the leaf count into the root makes lists of different lengths
   commit to different roots, which rules out every such case at once.

3. Merkle mountain ranges: merges are carries
---------------------------------------------

From :doc:`/api/gallery/structures/merkle/plot_04_mountain_ranges`. When does
an append cause the most merges, and what is the average over :math:`2^k`
appends?

.. dropdown:: Solution

   Appending to a range of size :math:`m` performs one merge per trailing 1
   bit of :math:`m`, exactly like the carries of :math:`m + 1` in binary.

   .. doctest::

      >>> mmr, merges = bk.structures.MerkleMountainRange(), []
      >>> for m in range(64):
      ...     before = len(mmr.peaks)
      ...     mmr = mmr.append(str(m).encode())
      ...     merges.append(before + 1 - len(mmr.peaks))
      >>> all(merges[m] == len(bin(m)) - len(bin(m).rstrip("1")) for m in range(64))
      True
      >>> max(merges), merges.index(max(merges)), sum(merges) / 64
      (6, 63, 0.984375)

   The worst append comes at size :math:`2^k - 1`, which merges everything
   into one peak. Over :math:`2^k` appends the merges total :math:`2^k - 1`,
   an average just under one.

4. Bloom filters: what the filter gives away
--------------------------------------------

From :doc:`/api/gallery/structures/bloom/plot_01_bloom_filter`. A filter
matches 1% of unrelated transactions. A wallet has 40 addresses, each used
once a day, among 300,000 daily transactions. What fraction of the matches
belong to the wallet?

.. dropdown:: Solution

   .. doctest::

      >>> true_matches = 40
      >>> false_matches = 0.01 * (300_000 - 40)
      >>> round(true_matches / (true_matches + false_matches), 4)
      0.0132

   Only about 1.3% of the matches are the wallet's, which sounds private. But
   the same addresses match day after day while false positives change, so
   intersecting a few days of matches reveals the wallet. This weakness led
   to compact block filters (BIP 157/158), where the server sends the filter
   instead.

5. Hash chains: why passwords are revealed backwards
----------------------------------------------------

From :doc:`/api/gallery/structures/hash_chains/plot_01_lamport_hash_chain`.
Why must passwords be revealed in reverse order of computation?

.. dropdown:: Solution

   .. doctest::

      >>> chain = bk.structures.hash_chain(b"seed", 5)
      >>> anchor = chain[-1]
      >>> bk.structures.verify_one_time_password(chain[-2], anchor)
      True
      >>> bk.crypto.sha256(chain[-3]) == chain[-2]  # Anyone can hash forward...
      True
      >>> bk.structures.verify_one_time_password(bk.crypto.sha256(anchor), anchor)
      False

   Each accepted password becomes the new anchor. Hashing is easy forward and
   hard backward, so an eavesdropper who sees one password can compute the
   *later* links of the chain but not the earlier one needed next. A breached
   server holds only the anchor, from which no future password follows.

6. Timestamping: a million documents in one proof
-------------------------------------------------

From :doc:`/api/gallery/structures/timestamps/plot_02_merkle_batching`.
Estimate the proof length for a round of a million documents.

.. dropdown:: Solution

   .. doctest::

      >>> from math import ceil, log2
      >>> levels = ceil(log2(1_000_000))
      >>> levels, levels * 32
      (20, 640)
      >>> tree = bk.structures.MerkleTree([str(i).encode() for i in range(1000)])
      >>> len(tree.proof(0).siblings) == ceil(log2(1000))
      True

   Twenty sibling digests, 640 bytes, link any document to the one hash
   written into the Bitcoin transaction, however many documents share it.

7. The payment lifecycle: reinclusion and conflicts
---------------------------------------------------

From :doc:`/api/gallery/structures/chain/plot_02_payment_lifecycle` and
:doc:`/api/gallery/consensus/nakamoto/plot_01_longest_chain`. After a fork,
replay a displaced payment, then try it against a state where a conflicting
payment spent the same account nonce.

.. dropdown:: Solution

   .. doctest::

      >>> from dataclasses import replace
      >>> public = bk.crypto.public_key(7)
      >>> alice = bk.structures.address(public)
      >>> bob = bk.structures.address(bk.crypto.public_key(11))
      >>> initial = bk.structures.Ledger({alice: 100})
      >>> payment = bk.structures.Transaction(public, bob, 25, 0).signed(7, signing_nonce=17)
      >>> paid = initial.apply([payment])
      >>> paid.balances[bob]
      25
      >>> try:
      ...     paid.apply([payment])
      ... except ValueError as error:
      ...     print("nonce" in str(error))
      True
      >>> replace(payment, chain_id="another-network").is_valid()
      False
      >>> conflict = bk.structures.Transaction(public, bob, 100, 0).signed(7, signing_nonce=19)
      >>> try:
      ...     initial.apply([conflict]).apply([payment])
      ... except ValueError as error:
      ...     print("nonce" in str(error))
      True

   A displaced payment is valid again against a state that has not used its
   account nonce, and replaying it after inclusion fails. When a conflicting
   payment used the same nonce on the winning branch, the original must not
   return to the queue even though its signature still verifies. Changing
   the chain ID changes the signed message, so the old signature fails.
