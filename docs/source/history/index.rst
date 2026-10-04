History
=======

A blockchain combines several answers to different questions. **Who can
authorize a message? Has a record changed? Can one item be checked without
downloading everything? Which of two valid histories should peers follow?**
Confusing these questions is a common source of confusion about blockchains.
A signature does not prevent double spending; a hash does not make a history
immutable; gossip does not create agreement.

This chapter follows the ideas in historical order. Each milestone gives the
problem, the mathematical mechanism, a link into the actual implementation,
and an experiment. The examples deliberately use smaller models than real
protocols. Their assumptions are part of the lesson, not details to hide.
Publication years below distinguish conference presentations from later
proceedings where useful. This is a selected, executable history, not a claim
that one inventor or one paper supplied every ingredient.

**First reading:** start with the “In plain language” and “Reading the
experiment” paragraphs in each milestone. The equations provide a second,
more detailed route; you can skip them initially. See :doc:`/start_here` for
the overall picture and :doc:`/glossary` for unfamiliar terms.

.. include:: /_generated/grid_history.rst

From breakthroughs to a working system
--------------------------------------

.. list-table:: A compact historical map
   :header-rows: 1
   :widths: 18 40 42

   * - Period
     - New capability
     - Question still requiring another ingredient
   * - 1976–1978
     - Public-key exchange and RSA
     - Who is really at the other end of the exchange?
   * - 1979–1983
     - Threshold sharing, Merkle authentication, blind signatures
     - Are shares honest, roots trusted, and tokens spent only once?
   * - 1985–1991
     - Curve groups, proof protocols, signatures, gossip, linked records
     - Which of two conflicting histories should participants accept?
   * - 1997–2009
     - Computational work, standardized hashing, Bitcoin's combination
     - Under which assumptions can a confirmation be reversed?
   * - 2012–2014
     - Stake-based participation and programmable state
     - What voting and execution rules make the whole system agree?

The detailed entries below distinguish original ideas from this package's
teaching adaptations. The :doc:`/tutorials/course` follows prerequisites rather than dates:

.. code-block:: text

   hashes ----> Merkle proofs ----------------------+
      |                                            |
      +-------> proof of work ----+                  v
   keys ------> signatures ------+------> payment lifecycle
   peer links -> gossip ---------+                  |
                                                    v
                                      forks, queues, and reorganization

   Python lists -> stack execution (a separate component)

Run :doc:`/api/gallery/structures/chain/plot_02_payment_lifecycle` to see how these ideas interact.
Use :doc:`/exercises/index` to check your reasoning after each experiment.

What the sequence teaches
-------------------------

Each ingredient changes what can be verified, under particular assumptions.
The most useful next experiment is often to remove one assumption: reuse a
nonce, reveal a commitment salt, forge a share, partition a link, replay a
transfer, or exhaust an execution budget. The tests and gallery show which
properties survive, which fail, and which the simplified model never promised.

See :doc:`/protocol` for exact encodings and :doc:`/simulation` for the scope of
research experiments. Each breakthrough page cites its primary sources.

.. toctree::
   :maxdepth: 1
   :hidden:

   crypto_breakthroughs
   structures_breakthroughs
   consensus_breakthroughs
   network_breakthroughs
   vm_breakthroughs
