Breakthroughs in Peer-to-Peer Networking
========================================

.. include:: /_generated/nav/network.rst

Agreement needs communication. Peers learn about transactions and blocks by
gossip: each one forwards what it hears to its neighbors. This chronology
traces the ideas behind :mod:`blockchainkit.network`.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

1987 — Epidemic dissemination and partial views
-----------------------------------------------

**In plain language.** A message spreads through neighboring peers, much as news passes
between people. Some hear it later than others. Passing the news around does not by
itself settle which of two conflicting stories to accept.

**Reading the experiment.** In the experiment, watch which peers receive the message
before and after a broken connection is restored. Reconnection alone does not send
earlier messages: the example explicitly sends the announcement again.

Demers and colleagues studied epidemic algorithms for propagating updates
among replicated databases. Local exchanges can spread information
without requiring one central sender to reach every replica at once. The
resulting delays make each participant's view temporarily different.

**Implementation:** :class:`blockchainkit.network.systems.gossip.SimulatedNetwork` is a
simplified flooding model with duplicate suppression, explicit links, and
seeded per-hop delays. It illustrates dissemination rather than reproducing
the paper's anti-entropy algorithms. The simulator orders simultaneous events
deterministically and uses integer time instead of sleeping.

**Experiment:** :doc:`/api/gallery/network/gossip/plot_01_gossip` partitions a peer, reconnects it,
and explicitly retransmits the missing announcement. A new connection alone
does not synchronize old state. Delivery does not imply agreement: peers can
receive the same two conflicting proposals and still need rules for choosing
between them. That distinction becomes visible in the blockchain experiment.

*References:* A. Demers et al., *Epidemic Algorithms for Replicated Database
Maintenance*, PODC '87, 1–12 (1987). `DOI
<https://doi.org/10.1145/41840.41841>`__.

.. minigallery:: ../../examples/network/gossip/plot_01_gossip.py
