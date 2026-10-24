Exercises: privacy
==================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. A quiet hour at the mix
--------------------------

From :doc:`/api/gallery/privacy/networks/plot_01_chaum_mix_nets`. Only two
messages pass through the cascade. What is the chance of linking a sender,
and what did Chaum propose to keep batches large?

.. dropdown:: Solution

   An honest mix can only shuffle what it holds, so each sender hides among
   two: a guess is right half the time.

   .. doctest::

      >>> from random import Random
      >>> mixes = [bk.privacy.MixNode(f"m{i}", 10 + i) for i in range(3)]
      >>> rng = Random(0)
      >>> onions = [bk.privacy.wrap(b"hi", mixes, f"r{i}", rng) for i in range(2)]
      >>> run = bk.privacy.mix_cascade(onions, mixes)
      >>> len(run.candidates(0))
      2

   Chaum had every participant send a message, real or dummy, in every
   batch, so the batch size never depends on who is active.

2. Entry guards
---------------

From :doc:`/api/gallery/privacy/networks/plot_02_tor_onion_routing`. With
10% of relays malicious, how likely is a bad guard, and why is a long-lived
guard better than a fresh entry for every circuit?

.. dropdown:: Solution

   A guard kept for months is bad with probability 0.1, once. A fresh entry
   for each of a hundred circuits is almost certain to be bad at least
   once, and a single exposed circuit can be enough.

   .. doctest::

      >>> round(1 - 0.9**100, 5)
      0.99997

   Guards turn "eventually exposed" into "exposed with probability 0.1, or
   never".

3. Two rings, one leaker
------------------------

From :doc:`/api/gallery/privacy/signatures/plot_01_ring_signatures`. Why do
two leaks signed with rings that share only the leaker's key reveal it?

.. dropdown:: Solution

   If both leaks are known to come from one person, that person is in both
   rings, so in their intersection.

   .. doctest::

      >>> G = bk.crypto.TEACHING_GROUP
      >>> first = {G.public(x) for x in (11, 22, 33)}
      >>> second = {G.public(x) for x in (33, 44, 55)}
      >>> first & second == {G.public(33)}
      True

   A careful leaker signs every leak with the same ring, so that the
   intersection is the whole ring.

4. A key image of g
-------------------

From :doc:`/api/gallery/privacy/signatures/plot_02_linkable_ring_signatures`.
Why would :math:`I = g^x` be a disaster?

.. dropdown:: Solution

   :math:`g^x` is the signer's public key, which sits in the ring. The
   "image" would name the signer.

   .. doctest::

      >>> G = bk.crypto.TEACHING_GROUP
      >>> ring = [G.public(x) for x in (11, 22, 33)]
      >>> ring.index(pow(G.g, 22, G.p))
      1
      >>> bk.privacy.key_image(22) in ring
      False

   Hashing the key into the group gives a base whose discrete logarithm
   nobody knows, so :math:`H_p(P)^x` cannot be matched to :math:`P`.

5. Handing over the view key
----------------------------

From :doc:`/api/gallery/privacy/signatures/plot_03_cryptonote_stealth_addresses`.
What can an auditor holding Bob's view key do?

.. dropdown:: Solution

   It can find every output paid to Bob, but it cannot compute a one-time
   private key, which also needs the spend key. Nor can it see Bob's
   spending: recognising a spend needs its key image, which needs the
   one-time private key.

   .. doctest::

      >>> bob = bk.privacy.stealth_keys(31_337, 27_182)
      >>> output = bk.privacy.stealth_payment(bob.view_public, bob.spend_public, 99)
      >>> bk.privacy.owns_output(output, bob.view_secret, bob.spend_public)
      True
      >>> bk.privacy.one_time_secret(output, bob.view_secret, 1)
      Traceback (most recent call last):
      ...
      ValueError: the output does not pay this wallet

6. Five patients, one diagnosis
-------------------------------

From :doc:`/api/gallery/privacy/analysis/plot_01_k_anonymity_anonymity_sets`.
What does 5-anonymity protect when everyone in a class shares a
diagnosis?

.. dropdown:: Solution

   Nothing about the diagnosis: knowing the neighbour is in the class is
   knowing the neighbour's diagnosis. Machanavajjhala et al. (2006) asked for
   *l-diversity*: at least :math:`l` distinct sensitive values per class.

   .. doctest::

      >>> rows = [{"zip": "021*", "age": "30s", "diagnosis": "flu"}] * 5
      >>> bk.privacy.k_anonymity(rows, ["zip", "age"])
      5
      >>> len({row["diagnosis"] for row in rows})
      1

7. One coin per payment
-----------------------

From :doc:`/api/gallery/privacy/analysis/plot_02_fistful_of_bitcoins_clustering`.
Which heuristic still links a user who spends one coin at a time, and when
does it abstain?

.. dropdown:: Solution

   The common-input heuristic never fires, but the change heuristic does,
   whenever the payee's address has been seen before. It abstains when both
   outputs are fresh.

   .. doctest::

      >>> shop = bk.privacy.TransactionRecord((), (("shop", 1),))
      >>> pay = bk.privacy.TransactionRecord((("coin", 9),), (("shop", 4), ("change", 5)))
      >>> {"coin", "change"} in bk.privacy.cluster_addresses([shop, pay], change=True)
      True
      >>> fresh = bk.privacy.TransactionRecord((("coin", 9),), (("new", 4), ("change", 5)))
      >>> {"coin", "change"} in bk.privacy.cluster_addresses([fresh], change=True)
      False

8. Rings of eleven
------------------

From :doc:`/api/gallery/privacy/analysis/plot_03_monero_traceability`.
Monero made rings of size 11 mandatory in 2018. Using
:func:`~blockchainkit.privacy.systems.traceability.simulate_rings`, how much
of a ledger with 60% zero-mixin rings of size 2 does the chain reaction
trace, and how much once the other 40% have size 11?

.. dropdown:: Solution

   With rings of two, striking the zero-mixin outputs leaves many rings with
   one member: 663 of 900 inputs are traced, 118 more than the zero-mixin
   ones. A ring of eleven falls only once ten of its members are struck, and
   none does, so only the zero-mixin inputs are traced. Large rings stop the
   cascade; only forbidding rings without decoys protects those inputs too.

   .. doctest::

      >>> for size in (2, 11):
      ...     rings = bk.privacy.simulate_rings(2_000, 900, ring_size=size, zero_mixin=0.6, seed=5)
      ...     report = bk.privacy.trace_rings(rings)
      ...     print(size, len(rings), report.zero_mixin, report.deduced)
      2 900 545 663
      11 900 525 525

9. Equal inputs
---------------

From :doc:`/api/gallery/privacy/mixing/plot_01_coinjoin`. Inputs of 15, 15
and 25 join with denomination 10. Which change outputs link?

.. dropdown:: Solution

   The two changes of 5 could each come from either 15-coin input, so
   neither links; the change of 15 can only come from the 25-coin input.

   .. doctest::

      >>> people = [("ann", "a", 15), ("bob", "b", 15), ("cat", "c", 25)]
      >>> round_ = bk.privacy.coinjoin(people, 10)
      >>> links = bk.privacy.link_change(round_.transaction, 10)
      >>> [(round_.owners[change], source) for change, source in links.items()]
      [('cat', 'c')]

   Inputs of equal size, or of exactly the denomination, leave change that
   links nothing.

10. Same size, same window
--------------------------

From :doc:`/api/gallery/privacy/mixing/plot_02_tumblebit`. Why must
TumbleBit payments share one size and one time window?

.. dropdown:: Solution

   Blinding hides the puzzles, but not the payments on the chain around
   them. If amounts differed, the tumbler, or anyone, could match each
   payer's payment to the payee receiving the same amount; if times
   differed, it could match by order.

   .. doctest::

      >>> run = bk.privacy.run_tumbler([("p1", "q1"), ("p2", "q2")], seed=1)
      >>> bk.privacy.tumbler_links(run)
      ()
      >>> paid_in = {"p1": 3, "p2": 5}
      >>> paid_out = {"q1": 3, "q2": 5}
      >>> [(p, q) for p, a in paid_in.items() for q, b in paid_out.items() if a == b]
      [('p1', 'q1'), ('p2', 'q2')]

11. Waiting before withdrawing
------------------------------

From :doc:`/api/gallery/privacy/mixing/plot_03_tornado_cash`. Why wait
before withdrawing?

.. dropdown:: Solution

   A withdrawal hides among the deposits made before it. Waiting lets more
   deposits arrive; it costs time, during which the coins are locked.

   .. doctest::

      >>> deposits = [(f"user{i}", 10 * i) for i in range(10)]
      >>> bk.privacy.mixer_report(deposits, [("fresh", 5)]).anonymity_sets
      (1,)
      >>> bk.privacy.mixer_report(deposits, [("fresh", 95)]).anonymity_sets
      (10,)

12. A million coins
-------------------

From :doc:`/api/gallery/privacy/amounts/plot_01_zerocoin`. How large is a
spend from a million coins here, and why did Zerocoin need a trusted RSA
modulus to do better?

.. dropdown:: Solution

   The ring signature has one response per coin plus a challenge: about a
   million numbers.

   .. doctest::

      >>> pool = bk.privacy.ZerocoinPool()
      >>> for serial in range(1, 9):
      ...     _ = pool.mint(bk.privacy.mint_coin(serial, 100 + serial))
      >>> spend = bk.privacy.prove_zerocoin_spend(pool.coins, 3, 103, b"m")
      >>> len(spend.proof.responses) + 1
      9

   The accumulator makes the proof independent of the number of coins, but
   anyone who knows the factors of :math:`N` can take :math:`c`-th roots and
   forge a witness for a coin never minted. So the modulus had to be made
   by a party trusted to destroy its factors.

13. The payee's opening
-----------------------

From :doc:`/api/gallery/privacy/amounts/plot_02_confidential_transactions`.
Why must the payee learn its amount and blinding factor, and how does it
check them?

.. dropdown:: Solution

   To spend the output later, the payee must choose blinding factors that
   cancel, so it needs this one. It checks by recomputing the commitment.

   .. doctest::

      >>> output = bk.privacy.confidential_output(30, 600, seed=1)
      >>> output.commitment == bk.crypto.pedersen_commit(30, 600)
      True
      >>> output.commitment == bk.crypto.pedersen_commit(31, 600)
      False

   Real wallets send the amount and blinding factor encrypted to the
   payee, inside the transaction.

14. The second column
---------------------

From :doc:`/api/gallery/privacy/amounts/plot_03_ringct`. Show that outputs
worth more than the input fail verification.

.. dropdown:: Solution

   The second column's key for the real member is no longer a pure power of
   :math:`h`, so the signature, made for the honest outputs, no longer
   closes.

   .. doctest::

      >>> import dataclasses
      >>> G = bk.crypto.TEACHING_GROUP
      >>> ring = [(G.public(x), bk.crypto.pedersen_commit(50, 7 + x)) for x in (11, 22, 33)]
      >>> tx = bk.privacy.ringct_spend(ring, 1, 22, 50, 29, [(49, 3)], 1, bits=8)
      >>> bk.privacy.verify_ringct(tx)
      True
      >>> richer = bk.privacy.confidential_output(60, 3, 8)
      >>> bk.privacy.verify_ringct(dataclasses.replace(tx, outputs=(richer,)))
      False

15. Without the offset
----------------------

From :doc:`/api/gallery/privacy/amounts/plot_04_mimblewimble`. How could an
observer split a merged block if there were no offset?

.. dropdown:: Solution

   Each kernel's excess would equal its own transaction's outputs over
   inputs (times :math:`g^{\text{fee}}`), so trying subsets of the block's
   inputs and outputs against each kernel would find them. With the offset,
   no kernel matches its own transaction on its own.

   .. doctest::

      >>> G = bk.crypto.TEACHING_GROUP
      >>> pay = bk.privacy.mimblewimble_transaction([(50, 11)], [(30, 22), (19, 33)], fee=1)
      >>> product = pow(G.g, 1, G.p) * pay.outputs[0] * pay.outputs[1] % G.p
      >>> product * pow(pay.inputs[0], -1, G.p) % G.p == pay.kernels[0].excess
      False
      >>> pay.offset != 0
      True
