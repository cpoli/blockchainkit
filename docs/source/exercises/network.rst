Exercises: networking
=====================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. Gossip: redundant routes and broken links
--------------------------------------------

From :doc:`/api/gallery/network/events/plot_01_discrete_event_simulation`.
Connect a triangle, disconnect a link while a message is in flight, and
check that duplicate paths do not duplicate receipts.

.. dropdown:: Solution

   .. doctest::

      >>> net = bk.network.SimulatedNetwork(["a", "b", "c"], seed=7)
      >>> for left, right in [("a", "b"), ("b", "c"), ("c", "a")]:
      ...     net.connect(left, right, latency=(2, 4))
      >>> net.broadcast("a", b"news")
      >>> net.disconnect("a", "b")
      >>> _ = net.run()
      >>> sorted(d.recipient for d in net.deliveries)
      ['a', 'b', 'c']

   The direct message to ``b`` is dropped with its link, but the route through
   ``c`` remains, and each peer accepts the payload once. The same seed
   reproduces every time; a different seed can change delays without
   changing who is reached.

2. Lamport clocks: making two events causal
-------------------------------------------

From :doc:`/api/gallery/network/events/plot_02_lamport_clocks`. Add a message
from P0 to P2 sent right after ``a`` and received before ``b``.

.. dropdown:: Solution

   .. doctest::

      >>> history = [
      ...     [("send", "m1"), ("local", "a"), ("send", "m4"), ("receive", "m3")],
      ...     [("receive", "m1"), ("send", "m2")],
      ...     [("receive", "m4"), ("local", "b"), ("receive", "m2"), ("send", "m3")],
      ... ]
      >>> bk.network.lamport_timestamps(history)
      ((1, 2, 3, 8), (2, 3), (4, 5, 6, 7))
      >>> vectors = bk.network.vector_timestamps(history)
      >>> bk.network.happened_before(vectors[0][1], vectors[2][1])
      True

   ``b`` jumps from time 1 to 5, and the later events at P2 follow. Now a
   chain of events leads from ``a`` to ``b``, so they are no longer
   concurrent. The receipt of ``m3`` at P0 moves from 6 to 8, past the time
   at which P2 sent it.

3. Vector clocks: why no single number captures concurrency
-----------------------------------------------------------

From :doc:`/api/gallery/network/events/plot_03_vector_clocks`. Find events
:math:`x, y, z` with :math:`x` concurrent to :math:`y`, :math:`y` concurrent
to :math:`z`, but :math:`x` before :math:`z`.

.. dropdown:: Solution

   .. doctest::

      >>> history = [
      ...     [("send", "m1"), ("local", "a"), ("receive", "m3")],
      ...     [("receive", "m1"), ("send", "m2")],
      ...     [("local", "b"), ("receive", "m2"), ("send", "m3")],
      ... ]
      >>> v = bk.network.vector_timestamps(history)
      >>> send_m1, a, b = v[0][0], v[0][1], v[2][0]
      >>> bk.network.concurrent(send_m1, b), bk.network.concurrent(b, a)
      (True, True)
      >>> bk.network.happened_before(send_m1, a)
      True

   If "concurrent" meant "equal timestamps", it would be transitive like
   equality, so sending ``m1`` would be concurrent with ``a``. It is not.
   And any other scalar encoding orders all events linearly, which loses the
   distinction. Exact concurrency needs as many counters as processes.

4. Rumor spreading: the ring
----------------------------

From :doc:`/api/gallery/network/gossip/plot_02_rumor_spreading`. Run push on a
ring instead of the complete graph. How do the rounds grow with :math:`n`?

.. dropdown:: Solution

   .. doctest::

      >>> rounds = {
      ...     n: sum(bk.network.spread_rumor(bk.network.ring_lattice(n, 2), seed=s).rounds
      ...            for s in range(5)) / 5
      ...     for n in (32, 64, 128)
      ... }
      >>> 1.6 < rounds[64] / rounds[32] < 2.4 and 1.6 < rounds[128] / rounds[64] < 2.4
      True

   Doubling :math:`n` roughly doubles the rounds: growth is linear, not
   logarithmic. On a ring the rumor can only advance one hop per round on
   each side, and an informed peer calls the uninformed neighbor only half
   the time, so it takes about :math:`n` rounds. Fast gossip needs a graph
   with short paths, which random links provide.

5. Bracha broadcast: the echo quorum
------------------------------------

From :doc:`/api/gallery/network/gossip/plot_03_reliable_broadcast`. Show that
two echo quorums of size :math:`\lceil (n + t + 1)/2 \rceil` share at least
:math:`t + 1` processes. What goes wrong with a simple majority?

.. dropdown:: Solution

   .. doctest::

      >>> def overlap(quorum, n):
      ...     return 2 * quorum - n
      >>> all(overlap(-(-(n + t + 1) // 2), n) >= t + 1
      ...     for n in range(4, 60) for t in range((n - 1) // 3 + 1))
      True
      >>> [(n, overlap(n // 2 + 1, n)) for n in (4, 7, 10)]
      [(4, 2), (7, 1), (10, 2)]

   Since :math:`2\lceil (n + t + 1)/2 \rceil \ge n + t + 1`, the overlap is at
   least :math:`t + 1`, so it contains a correct process, which echoes one
   value only. A majority quorum overlaps in one or two processes, which can
   all be faulty when :math:`t \ge 2`, so two values could both gather a
   quorum.

6. Random graphs: where the threshold comes from
------------------------------------------------

From :doc:`/api/gallery/network/graphs/plot_01_random_graphs`. Evaluate the
expected number of isolated peers at :math:`p = c \ln n / n`, and derive the
limit law.

.. dropdown:: Solution

   The expected number of isolated peers is :math:`n(1-p)^{n-1} \approx n
   e^{-pn} = n^{1-c}`: it tends to infinity for :math:`c < 1` and to 0 for
   :math:`c > 1`. If their number is roughly Poisson with that mean, the
   chance of none is :math:`\exp(-n^{1-c})`, and isolated peers are the last
   obstacle to connectivity.

   .. doctest::

      >>> from math import exp, log
      >>> n, c = 400, 1.2
      >>> p = c * log(n) / n
      >>> round(n * (1 - p) ** (n - 1), 3), round(n ** (1 - c), 3)
      (0.288, 0.302)
      >>> isolated = [
      ...     sum(d == 0 for d in bk.network.erdos_renyi(n, p, seed=s).degrees()) for s in range(60)
      ... ]
      >>> abs(sum(isolated) / 60 - 0.3) < 0.15
      True
      >>> round(exp(-(n ** (1 - c))), 2)
      0.74

7. Eclipse attacks: picking a bucket first
------------------------------------------

From :doc:`/api/gallery/network/overlays/plot_03_eclipse_attack`. If the
attacker owns 16 of 64 buckets outright, what is the probability that all
eight picks land in its buckets?

.. dropdown:: Solution

   .. doctest::

      >>> f"{(16 / 64) ** 8:.1e}"
      '1.5e-05'

   Each pick first chooses a random bucket, so the attacker's chance per
   pick is the fraction of buckets it holds, :math:`1/4`, however many
   addresses it crammed into them. Eight independent picks all succeed with
   probability :math:`4^{-8}`, one in 65,536. The simulation, with 2000
   trials, saw none.

8. Compact blocks: short-ID collisions
--------------------------------------

From :doc:`/api/gallery/network/relay/plot_03_compact_blocks`. With 6-byte
short IDs, 2000 block transactions and a 300,000-transaction mempool,
estimate the expected number of colliding pairs.

.. dropdown:: Solution

   .. doctest::

      >>> pairs = 2000 * 300_000
      >>> f"{pairs / 2**48:.1e}"
      '2.1e-06'

   Each block transaction is compared with each mempool entry, and a pair
   collides with probability :math:`2^{-48}`. About one block in 470,000 has a
   collision, and it costs only an extra round trip. Eight bytes would make
   collisions rarer still but add a third more to the short IDs of every
   block; BIP 152 accepts the rare fallback.
