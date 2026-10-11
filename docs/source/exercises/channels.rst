Exercises: channels
===================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. Erasures and errors together
-------------------------------

From :doc:`/api/gallery/channels/coding/plot_01_reed_solomon`. With
``n = 11`` and ``k = 5``, erase two symbols and corrupt some others. How
many corruptions can Berlekamp-Welch still correct?

.. dropdown:: Solution

   Two erasures leave 9 symbols, 4 more than ``k``, so up to 2 errors can
   be corrected: :math:`2 \cdot 2 + 2 = 6 = n - k`. A third error breaks
   the bound.

   .. doctest::

      >>> received = list(bk.channels.rs_encode(list(b"HELLO"), 11))
      >>> received[0] = received[1] = None
      >>> received[2] += 1
      >>> received[3] += 1
      >>> bytes(bk.channels.rs_decode(received, 5))
      b'HELLO'
      >>> received[4] += 1
      >>> bk.channels.rs_decode(received, 5)
      Traceback (most recent call last):
      ...
      ValueError: too many errors to correct

2. A million resets within a day
--------------------------------

From :doc:`/api/gallery/channels/payment_channels/plot_02_duplex_channels`.
With :math:`\delta = 6` blocks, which invalidation trees support a million
resets and close within 144 blocks?

.. dropdown:: Solution

   The tree needs :math:`s^d \ge 10^6` and :math:`d (s - 1) \delta \le
   144`, that is :math:`d (s - 1) \le 24`. For a fixed product
   :math:`d (s - 1)`, binary trees reach the most states.

   .. doctest::

      >>> [(d, s) for d in range(1, 30) for s in range(2, 20)
      ...  if s**d >= 10**6 and d * (s - 1) * 6 <= 144]
      [(20, 2), (21, 2), (22, 2), (23, 2), (24, 2)]
      >>> sum(bk.channels.invalidation_locktimes(0, depth=20, steps=2, delta=6))
      120

   Lightning's number of updates is bounded only by the length of each
   party's hash chain of per-commitment secrets, and its delay is chosen
   for the watchers' safety, not for the number of updates.

3. The last chance to punish
----------------------------

From :doc:`/api/gallery/channels/payment_channels/plot_03_lightning_revocation`.
Alice publishes a revoked commitment at height 1,000 with a delay of 144.
Until when can Bob punish her?

.. dropdown:: Solution

   Alice's sweep becomes valid at height 1,144, so Bob's penalty must be
   confirmed by 1,143; after that, whoever is confirmed first wins.

   .. doctest::

      >>> def breached():
      ...     channel = bk.channels.LightningChannel(("alice", "bob"), (7, 5), (100, 100), delay=144)
      ...     channel.pay("alice", 10)
      ...     channel.publish("alice", state=0, height=1_000)
      ...     return channel
      >>> breached().penalize(height=1_143).kind
      'penalty'
      >>> breached().sweep(height=1_144).kind
      'unilateral'

   A shorter delay gives Bob, or his watchtower, less time to notice; a
   longer one makes honest unilateral closes slower.

4. How many shards?
-------------------

From :doc:`/api/gallery/channels/scaling/plot_02_omniledger_sharding`. With
1,800 validators and a 25% adversary, how many shards keep the chance that
any shard fails in an epoch below one in a million?

.. dropdown:: Solution

   A union bound over the shards suffices: ``s`` shards of ``1800 / s``
   fail with probability at most ``s`` times a single shard's.

   .. doctest::

      >>> def risk(shards):
      ...     return shards * bk.channels.shard_failure_probability(1_800, 450, 1_800 // shards)
      >>> [s for s in (1, 2, 3, 4, 5, 6) if risk(s) < 1e-6]
      [1, 2, 3]

   Only three shards: a quarter of the validators is a large adversary.
   As it nears a third, even the full set of 1,800 barely holds, and
   sharding gives no room at all.

5. A validium's gas
-------------------

From :doc:`/api/gallery/channels/scaling/plot_03_zk_rollups`. What does a
transfer cost in a batch of 1,000 if the data is posted elsewhere?

.. dropdown:: Solution

   .. doctest::

      >>> bk.channels.batch_gas(1_000, bytes_per_transaction=0, fixed_gas=300_000) / 1_000
      300.0

   Only the proof is paid for. But the chain no longer holds the data: if
   the operator withholds it, users cannot rebuild their balances, and the
   valid state root proves nothing they can withdraw with.

6. A window against censorship
------------------------------

From :doc:`/api/gallery/channels/scaling/plot_04_optimistic_rollups`. If a
fraction ``f`` of block producers censor the challenge, how many blocks
must the window last for the attack to succeed with probability below
:math:`10^{-9}`?

.. dropdown:: Solution

   The challenge is excluded from ``c`` consecutive blocks with probability
   :math:`f^c`, so :math:`c \ge \log 10^{-9} / \log f`.

   .. doctest::

      >>> from math import ceil, log
      >>> [ceil(log(1e-9) / log(f)) for f in (0.5, 0.9, 0.99)]
      [30, 197, 2062]

   Deployed rollups use a window of about a week, far longer, because the
   attacker might also delay the challenger off chain or congest the chain.
