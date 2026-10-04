Who do you trust?
=================

"Trustless" is a slogan, not a property. Every mechanism in blockchainkit is
safe only under an assumption about the world: that most of the hash power is
honest, that fewer than a third of the replicas lie, that messages eventually
arrive, that your neighbors are not all the same attacker. This page lines up
those assumptions and, for each, runs the experiment that shows the mechanism
failing once the assumption does.

.. list-table::
   :header-rows: 1
   :widths: 28 40 32

   * - Mechanism
     - Trusts that...
     - Fails when...
   * - PBFT, Bracha broadcast
     - fewer than a third of replicas are faulty
     - :math:`f \ge n/3`
   * - Nakamoto consensus
     - honest miners hold most of the hash power
     - an attacker reaches half (or a third, by mining selfishly)
   * - Casper FFG
     - fewer than a third of the stake is slashable-dishonest
     - a third is willing to be slashed
   * - Partial synchrony
     - messages eventually arrive within a bound
     - the network never stabilizes
   * - Light clients
     - the heaviest header chain has valid blocks
     - most hash power produces invalid blocks
   * - Peer-to-peer networking
     - at least one neighbor is honest
     - every connection is the attacker's (eclipse)
   * - Commitments, signatures
     - nobody knows a hidden trapdoor; hashes behave randomly
     - a setup secret leaks, or the hash breaks

All snippets use ``import blockchainkit as bk``.

Fewer than a third: quorums
---------------------------

PBFT waits for :math:`2f + 1` matching messages out of :math:`n = 3f + 1`. Any two
such quorums share an honest replica, so they cannot certify different
values, as long as at most :math:`f` replicas are faulty.

.. doctest::

   >>> bk.consensus.pbft_round(4, {0}, "A", equivocate=True).commits
   {1: 'A', 2: 'A', 3: None}
   >>> bk.consensus.pbft_round(4, {0, 3}, "A", equivocate=True).commits
   {1: 'A', 2: 'B'}

With one faulty leader, replica 3 commits nothing (it will catch up later), but
no one commits ``B``. With a second faulty replica, the honest replicas commit
different values. Bracha's broadcast has the same boundary:

.. doctest::

   >>> bk.network.reliable_broadcast(4, {0}, ["a", "a", "b", "b"]).agreement
   True
   >>> bk.network.reliable_broadcast(4, {0, 3}, ["a", "a", "b", "b"]).agreement
   False

See :doc:`/api/gallery/consensus/agreement/plot_05_pbft`.

Most of the hash power: Nakamoto consensus
------------------------------------------

Bitcoin does not count replicas, which would invite Sybils; it counts work.
Its safety is probabilistic: an attacker with a share :math:`q` of the hash
power catches up from :math:`z` blocks behind with a probability that falls
exponentially in :math:`z`, until :math:`q` reaches one half.

.. doctest::

   >>> [round(bk.consensus.attacker_success_probability(q, 6), 4) for q in (0.1, 0.3, 0.45, 0.5)]
   [0.0002, 0.1321, 0.7661, 1.0]

And honest majority is not quite enough. A pool that withholds blocks gains
more than its share once it controls a third of the hash power, or less if it
wins races to propagate:

.. doctest::

   >>> round(bk.consensus.selfish_mining_threshold(0.0), 4), bk.consensus.selfish_mining_threshold(0.5)
   (0.3333, 0.25)

See :doc:`/api/gallery/consensus/attacks/plot_02_double_spend` and
:doc:`/api/gallery/consensus/attacks/plot_03_selfish_mining`.

Two thirds of the stake: accountable safety
-------------------------------------------

Casper FFG finalizes a checkpoint with votes from two thirds of the stake. Two
conflicting finalized checkpoints would need two such sets, which overlap in a
third of the stake, and every validator in the overlap broke a slashing rule:

.. doctest::

   >>> from fractions import Fraction
   >>> 2 * Fraction(2, 3) - 1
   Fraction(1, 3)

So the assumption is economic: that no one will burn a third of the stake to
break safety. See :doc:`/api/gallery/consensus/pos/plot_04_casper_ffg`.

Messages arrive eventually: synchrony
-------------------------------------

FLP proved that no deterministic protocol can guarantee agreement if messages
may be delayed forever. Partially synchronous protocols assume that after an
unknown *global stabilization time* (GST), messages arrive within a bound
:math:`\Delta`. Leaders that time out are replaced, with longer timeouts each time,
until one succeeds after GST:

.. doctest::

   >>> run = bk.consensus.view_changes(gst=100, delta=8, base_timeout=1)
   >>> run.decided_view, run.decision_time >= 100
   (7, True)

Before GST the protocol stays safe but makes no progress; that is the price of
the assumption. See :doc:`/api/gallery/consensus/agreement/plot_04_partial_synchrony`.

At least one honest neighbor: the network
-----------------------------------------

Every node sees the chain only through its connections. If an attacker owns
all of them, the node is eclipsed: it sees whatever chain the attacker shows
it, and the honest majority elsewhere does not help.

.. doctest::

   >>> bk.network.eclipse_probability(0.9, 8) > bk.network.eclipse_probability(0.25, 8) * 1000
   True

Bucketing addresses by network group keeps the attacker's share of the table
low; more outbound connections then make an eclipse exponentially rarer. See
:doc:`/api/gallery/network/overlays/plot_03_eclipse_attack`.

No hidden trapdoor: setup
-------------------------

Pedersen commitments use two generators :math:`g` and :math:`h`. Anyone who knows
:math:`\log_g h` can open a commitment to any value. blockchainkit therefore
derives :math:`h` by hashing, so that no one, including the library author,
knows that logarithm. The trust moves into the hash.

.. doctest::

   >>> g, h = bk.crypto.pedersen_generators()
   >>> g != h
   True

See :doc:`/api/gallery/crypto/commitments/plot_02_pedersen`.

Check yourself
--------------

* PBFT can run on four servers, while Bitcoin needs thousands of miners. What
  does each count, and why can PBFT not simply be run among anonymous nodes?
* A light client follows the heaviest header chain. Which row of the table does
  it add to its trust, compared with a full node?
* Which of these assumptions would a two-week network partition break, and what
  would each system do during it? (Compare with
  :doc:`/api/gallery/network/replication/plot_01_cap_theorem`.)
