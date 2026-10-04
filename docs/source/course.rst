A guided course: from fingerprints to shared history
====================================================

Start with :doc:`start_here` and install using :doc:`quickstart`. You need
Python variables, lists, loops, functions, and ``assert``. You do not need
prior cryptography. Read the :doc:`glossary` as needed; leave equations for a
second pass. The times below are planning estimates, including exercises.

For each lesson: predict the result, run the notebook from its first cell,
change one input, and explain the result in your own words. Consult
:doc:`solutions` after trying the exercise. A passed assertion checks a
specific claim; it is not proof that a complete system is secure.

.. list-table:: Beginner route
   :header-rows: 1
   :widths: 12 30 38 20

   * - Lesson
     - Read and run
     - You should be able to explain
     - Prerequisite / time
   * - 1
     - :doc:`gallery/plot_07_hashing`
     - Why fingerprints detect changes but do not hide guessable messages
     - Start here / 30 min
   * - 2
     - :doc:`gallery/plot_03_merkle_proofs`
     - How ordered sibling hashes reconstruct a trusted root
     - Lesson 1 / 40 min
   * - 3
     - :doc:`gallery/plot_01_public_keys`, then :doc:`gallery/plot_05_elliptic_curves`
     - Public versus private values; why tiny examples can be broken
     - Python loops / 60 min
   * - 4
     - :doc:`gallery/plot_06_schnorr_proofs` and :doc:`quickstart`
     - What a signature checks and why signing nonces must not be reused
     - Lessons 1 and 3 / 60 min
   * - 5
     - :doc:`gallery/plot_08_proof_of_work` and :doc:`gallery/plot_09_gossip`
     - Why finding a block takes work and why peers temporarily disagree
     - Lesson 1 / 50 min
   * - 6
     - :doc:`gallery/plot_10_blockchain`, then :doc:`gallery/plot_13_payment_lifecycle`
     - Pending versus included payments; how a fork changes balances and queues
     - Lessons 2, 4, 5 / 60 min
   * - 7
     - :doc:`gallery/plot_12_execution`
     - Stack operations, execution budgets, and committing state only on success
     - Python lists / 40 min

Further investigations
----------------------

After lesson 3, explore :doc:`gallery/plot_02_secret_sharing` and
:doc:`gallery/plot_04_blind_signatures`: recovering a secret and authorizing
hidden information solve different problems. After lesson 6, explore
:doc:`gallery/plot_11_stake`: a fair proposer lottery still needs agreement
rules. Read :doc:`history` alongside these lessons for the origins and limits
of each breakthrough; its chronological order differs from this prerequisite
order deliberately.

Check your understanding
------------------------

Before moving on, answer these without code:

* If Alice signs two conflicting payments, can both signatures verify?
* Does an inclusion proof establish that a payment is funded or final?
* Can two honest peers have different pending queues or selected histories?
* Does reconnecting a link automatically send all old messages in this model?
* Why can a payment return to a queue after a reorganization?

Answers: yes; no; yes; no (explicit synchronization is needed); and because
its effect may have disappeared from the selected state, making its sequence
number and balance requirements valid again. Recheck eligibility rather than
assuming every displaced payment is still spendable.

A capstone experiment
---------------------

Run :doc:`gallery/plot_13_payment_lifecycle`. Draw its two branches on paper,
label Bob's balance at each block, and compare your predictions with the
balance and queue table. Then make the winning branch contain a conflicting
payment. Explain why a valid signature is insufficient to restore the original
payment to a pending queue. See :doc:`solutions` for a checked conflict example.

The lifecycle queue handles one candidate payment per peer. Extending it to
many dependent payments requires validating an ordered batch against a
provisional state, plus explicit policies for conflicts and replacement.
These policies are outside this lesson, not hidden behavior of the simulator.
