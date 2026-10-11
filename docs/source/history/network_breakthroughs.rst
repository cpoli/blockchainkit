Breakthroughs in Peer-to-Peer Networking
========================================

.. include:: /_generated/nav/network.rst

.. epigraph::

   "A distributed system is one in which the failure of a computer you didn't
   even know existed can render your own computer unusable."
   -- Leslie Lamport, email message, 1987

Agreement needs communication. Peers learn about transactions and blocks by
gossip, find each other through overlays, and see the world only through the
connections they happen to have. This chronology traces the ideas behind
:mod:`blockchainkit.network`, from random graphs to Dandelion, along four
questions: how peers are connected (random, small-world and scale-free graphs,
Kademlia), how news spreads (gossip, reliable broadcast, block relay), how
events are ordered without a shared clock (Lamport and vector clocks, CAP),
and what an adversary can do to the network (Sybil and eclipse attacks,
deanonymization). Every model runs
in simulated time from a fixed seed; :doc:`/simulation` describes what the
simulations do and do not capture.

.. contents:: Timeline
   :local:
   :depth: 1

1959 -- Random Graphs and the Connectivity Threshold
----------------------------------------------------

Erdős and Rényi founded the theory of random graphs by asking which properties
appear, and how suddenly, as links are added at random. Connectivity has a
sharp threshold: if every pair of :math:`n` peers is linked with probability
:math:`p`, the network snaps from fragmented to connected once each peer has
about :math:`\ln n` links:

.. math::

   P\bigl(G(n, p) \text{ connected}\bigr) \to
   \begin{cases} 0 & p < (1 - \varepsilon) \ln n / n, \\
                 1 & p > (1 + \varepsilon) \ln n / n. \end{cases}

Just below the threshold, what keeps the graph apart is almost always a few
isolated peers, so the practical rule is to make sure no peer is left with too
few links. Unstructured peer-to-peer networks such as Bitcoin's rely on this
result: :math:`\ln n` grows so slowly that ten thousand peers need only about
nine links each, and a Bitcoin node opens eight outbound connections and
accepts inbound ones, which puts it above the threshold.

*Implementation:* :func:`blockchainkit.network.systems.topology.erdos_renyi`
and :class:`blockchainkit.network.systems.topology.Graph`.

*References:* P. Erdős and A. Rényi, *On random graphs I*, Publicationes
Mathematicae Debrecen 6, 290–297 (1959).

.. minigallery:: ../../examples/network/graphs/plot_01_random_graphs.py

1961-1965 -- Discrete-Event Simulation
--------------------------------------

Geoffrey Gordon's GPSS (1961) and Dahl and Nygaard's Simula (1965) made
*discrete-event simulation* a standard tool. Instead of waiting for real time
to pass, the simulator keeps future events in a queue ordered by time, pops the
earliest, sets the clock to its time, and lets it schedule further events.
Nothing happens between events, and with a fixed random seed every run is
identical. Simula's objects and classes, invented to model the simulated
entities, went on to found object-oriented programming.

*Implementation:* :class:`blockchainkit.network.systems.gossip.SimulatedNetwork`
schedules each message as a delivery event a seeded random number of ticks
after it is sent, suppresses duplicates, and drops in-flight messages when a
link is cut. It never sleeps or reads the wall clock.

*References:* G. Gordon, *A general purpose systems simulation program*, Proc.
Eastern Joint Computer Conference, 87–104 (1961); O.-J. Dahl and K. Nygaard,
*SIMULA — an ALGOL-based simulation language*, Communications of the ACM 9(9),
671–678 (1966). `DOI <https://doi.org/10.1145/365813.365819>`__.

.. minigallery:: ../../examples/network/events/plot_01_discrete_event_simulation.py

1978 -- Lamport Clocks: Time from Messages
------------------------------------------

Computers' clocks disagree, so physical time cannot always say which of two
events came first. Lamport defined *happened before* (:math:`a \to b`) from the
messages themselves: the smallest transitive relation in which each process's
events are ordered and each send precedes its receive. Each process keeps a
counter :math:`C`, increments it at every event, attaches it to messages, and on
receiving a message with stamp :math:`t` sets :math:`C \leftarrow \max(C, t) + 1`.
This guarantees the *clock condition*

.. math::

   a \to b \implies C(a) < C(b),

and ordering events by :math:`(C, \text{process})` gives a total order that
every process computes alike. Lamport used it to replicate a state machine: if
all replicas apply the same commands in the same order, they stay identical,
the principle behind every blockchain. The converse fails: :math:`C(a) < C(b)`
does not mean that :math:`a` could have influenced :math:`b`.

*Implementation:* :func:`blockchainkit.network.systems.clocks.lamport_timestamps`;
:func:`blockchainkit.network.visualizers.plots.plot_space_time` draws the
diagram.

*References:* L. Lamport, *Time, clocks, and the ordering of events in a
distributed system*, Communications of the ACM 21(7), 558–565 (1978). `DOI
<https://doi.org/10.1145/359545.359563>`__.

.. minigallery:: ../../examples/network/events/plot_02_lamport_clocks.py

1985-1987 -- Rumor Spreading in log₂ n + ln n Rounds
----------------------------------------------------

If everyone who knows a rumor tells one random person per round, how long until
everyone knows? Frieze and Grimmett showed that this *push* gossip on the
complete graph informs all :math:`n` peers in
:math:`\log_2 n + \ln n + o(\log n)` rounds, and Pittel sharpened the error to
:math:`O(1)`:

.. math::

   T_n = \log_2 n + \ln n + O(1).

The :math:`\log_2 n` term is the doubling phase: while few peers know the
rumor, almost every call reaches someone new, so the informed set doubles each
round. The :math:`\ln n` term is a coupon-collector phase: once nearly all
:math:`n` peers are calling, a given uninformed peer is missed by every caller
with probability :math:`(1 - 1/n)^n \approx 1/e`, so the uninformed shrink by a
factor :math:`e` per round and need about :math:`\ln n` rounds to vanish. A
million peers need about :math:`20 + 14 = 34` rounds. Logarithmic
spreading time is why gossip scales to networks of any size.

*Implementation:* :func:`blockchainkit.network.systems.epidemics.spread_rumor`
and :func:`blockchainkit.network.systems.epidemics.pittel_rounds`.

*References:* A. M. Frieze and G. R. Grimmett, *The shortest-path problem for
graphs with random arc-lengths*, Discrete Applied Mathematics 10, 57–77 (1985);
B. Pittel, *On spreading a rumor*, SIAM Journal on Applied Mathematics 47(1),
213–223 (1987). `DOI <https://doi.org/10.1137/0147013>`__.

.. minigallery:: ../../examples/network/gossip/plot_02_rumor_spreading.py

1987 -- Epidemic Algorithms for Replicated Databases
----------------------------------------------------

Demers and colleagues at Xerox PARC kept the replicas of the Clearinghouse name
service consistent without a central server: each replica regularly contacts a
random other one, like a disease passing from person to person. In *push* the
caller tells, in *pull* it asks "what's new?". If a fraction :math:`s_i` of
replicas is uninformed after round :math:`i`, then once most replicas know the
update,

.. math::

   \text{push: } s_{i+1} \approx s_i e^{-1}, \qquad
   \text{pull: } s_{i+1} \approx s_i^2,

because an uninformed replica stays uninformed under push only if no informed
caller picks it, with probability about :math:`1/e` as above, and under pull
only if it calls another uninformed replica, with probability :math:`s_i`.
Push therefore cuts the stragglers by a constant factor per round, while pull
squares their fraction and finishes in a few rounds; combining the two gives
push's fast start and pull's fast finish. They also introduced *anti-entropy* (periodically
reconciling whole databases) and *rumor mongering* (spreading a new update
until it seems old news). Block and transaction relay in Bitcoin descends from
these ideas.

*Implementation:* :func:`blockchainkit.network.systems.epidemics.spread_rumor`
with ``mode`` set to ``"push"``, ``"pull"`` or ``"push-pull"``;
:func:`blockchainkit.network.visualizers.plots.plot_rumor_spread`.

*References:* A. Demers et al., *Epidemic Algorithms for Replicated Database
Maintenance*, PODC '87, 1–12 (1987). `DOI
<https://doi.org/10.1145/41840.41841>`__.

.. minigallery:: ../../examples/network/gossip/plot_01_epidemic_algorithms.py

1987 -- Bracha's Reliable Broadcast
-----------------------------------

A dishonest sender might tell half the group one thing and half another.
Bracha built Byzantine *reliable broadcast*, which makes either every correct
process deliver the same value or none deliver anything, from two all-to-all
phases, tolerating :math:`t` faulty processes out of :math:`n`. On receiving
the sender's value, each process sends ECHO for it. On
:math:`\lceil (n + t + 1)/2 \rceil` echoes, or :math:`t + 1` READY messages,
for one value, it sends READY once. On :math:`2t + 1` READY messages it
delivers. All of this needs

.. math::

   n > 3t,

so that the :math:`n - t` correct processes can reach both thresholds on their
own: :math:`n - t \ge \lceil (n + t + 1)/2 \rceil` and :math:`n - t \ge 2t + 1`
both reduce to :math:`n \ge 3t + 1`.

Agreement comes from quorum overlap: two echo quorums together hold more than
:math:`n + t` messages, so they share at least :math:`t + 1` processes, at
least one of them correct. A correct process echoes only one value, so no two
correct processes become ready for different values.

Delivery is all-or-nothing: if one correct process delivers, it saw
:math:`2t + 1` READY messages, at least :math:`t + 1` of them from correct
processes, and those reach everyone. Every correct process therefore gets
:math:`t + 1` READY messages, sends READY itself, and so all
:math:`n - t \ge 2t + 1` correct processes deliver. Reliable broadcast is a
building block of asynchronous Byzantine consensus and of modern DAG-based
blockchain protocols.

*Implementation:* :func:`blockchainkit.network.systems.broadcast.reliable_broadcast`
runs the protocol in synchronous rounds against faulty processes that collude
with the sender's split.

*References:* G. Bracha, *Asynchronous Byzantine agreement protocols*,
Information and Computation 75(2), 130–143 (1987). `DOI
<https://doi.org/10.1016/0890-5401(87)90054-X>`__.

.. minigallery:: ../../examples/network/gossip/plot_03_reliable_broadcast.py

1988 -- Vector Clocks: Detecting Concurrency
--------------------------------------------

A Lamport clock puts causes before effects but cannot say when two events
happened independently. Fidge and Mattern independently replaced the scalar
with a vector :math:`V` of :math:`n` counters, one per process. Process
:math:`p` increments :math:`V[p]` at each event and, on receipt, first takes the
entrywise maximum with the vector carried by the message. Then :math:`V(a)[q]`
counts the events at :math:`q` that happened before or at :math:`a`, and
causality is characterized exactly:

.. math::

   a \to b \iff V(a) \le V(b) \text{ entrywise and } V(a) \ne V(b).

Events with incomparable vectors are concurrent. Replicated data stores use
vector clocks and their descendants to detect conflicting updates that must be
reconciled.

*Implementation:* :func:`blockchainkit.network.systems.clocks.vector_timestamps`,
:func:`blockchainkit.network.systems.clocks.happened_before` and
:func:`blockchainkit.network.systems.clocks.concurrent`.

*References:* C. J. Fidge, *Timestamps in message-passing systems that preserve
the partial ordering*, Proc. 11th Australian Computer Science Conference, 56–66
(1988); F. Mattern, *Virtual time and global states of distributed systems*,
Parallel and Distributed Algorithms, 215–226 (North-Holland, 1989).

.. minigallery:: ../../examples/network/events/plot_03_vector_clocks.py

1998 -- Small-World Networks
----------------------------

In a network where everyone knows only their neighbors, messages crawl. Watts
and Strogatz started from a ring lattice, in which each node links to its
:math:`k` nearest neighbors, and rewired each link to a random node with
probability :math:`p`. The lattice has high clustering but long paths:

.. math::

   C(0) = \frac{3(k-2)}{4(k-1)}, \qquad L(0) \approx \frac{n}{2k}.

Already at :math:`p \approx 0.01`, the average path length :math:`L` drops close
to the random-graph value :math:`\ln n / \ln k`, while the clustering :math:`C`
barely moves: each shortcut shortens many paths but changes the clustering of
only two nodes. They found such small worlds in actors' collaborations, the
power grid and a nervous system. For a peer-to-peer network the lesson is that
a few random links are enough to make every peer close to every other, even if
most links are local.

*Implementation:* :func:`blockchainkit.network.systems.topology.watts_strogatz`,
:func:`blockchainkit.network.systems.topology.ring_lattice`,
:meth:`blockchainkit.network.systems.topology.Graph.average_path_length` and
:meth:`blockchainkit.network.systems.topology.Graph.clustering`.

*References:* D. J. Watts and S. H. Strogatz, *Collective dynamics of
'small-world' networks*, Nature 393, 440–442 (1998). `DOI
<https://doi.org/10.1038/30918>`__.

.. minigallery:: ../../examples/network/graphs/plot_02_small_world.py

1999 -- Scale-Free Networks
---------------------------

Barabási and Albert observed that the Web's link counts follow a power law,
unlike the Poisson degrees of a random graph, and explained it by growth with
*preferential attachment*: each new node links to :math:`m` existing nodes
with probability proportional to their degree, so the popular become more
popular still. Their continuum argument gives a degree distribution that does
not depend on time or network size:

.. math::

   P(k) \approx \frac{2m^2}{k^3}.

The result is a few huge hubs and many small nodes. Hubs shorten paths and
speed up gossip, but concentrate risk: Albert, Jeong and Barabási (2000) showed
that such networks are robust to random failures yet fragile under targeted
attacks on their hubs. A random failure almost always hits one of the many
small nodes, which carry few paths; an attacker who removes the few hubs
removes the shortcuts that hold the network together.

*Implementation:* :func:`blockchainkit.network.systems.topology.barabasi_albert`.

*References:* A.-L. Barabási and R. Albert, *Emergence of scaling in random
networks*, Science 286(5439), 509–512 (1999). `DOI
<https://doi.org/10.1126/science.286.5439.509>`__.

.. minigallery:: ../../examples/network/graphs/plot_03_scale_free.py

2000-2002 -- The CAP Theorem
----------------------------

Brewer conjectured in a 2000 keynote that a distributed system can provide at
most two of *consistency*, *availability* and *partition tolerance*. Gilbert
and Lynch proved it: in an asynchronous network that may lose messages, no
read/write register can guarantee both that every request to a live replica
succeeds and that every operation is linearizable. The argument is short: cut
the replicas into two sides that cannot exchange messages, write a new value on
one side, then read on the other. Availability forces the reader's replica to
answer without hearing from the writer's side, so it returns the old value,
which linearizability forbids. Since partitions cannot be
ruled out, the real choice is what to give up *during* a partition: refuse some
requests, or answer them knowing the other side may disagree.

Quorum systems such as PBFT choose consistency: the minority side stalls.
Nakamoto consensus chooses availability: both sides keep extending a chain, and
one side's blocks are discarded when the network heals.

*Implementation:* :class:`blockchainkit.network.systems.replication.ReplicatedRegister`
with ``mode="consistent"`` (majority quorums) or ``mode="available"`` (answer
locally, last writer wins on healing).

*References:* E. A. Brewer, *Towards robust distributed systems*, keynote, PODC
2000; S. Gilbert and N. Lynch, *Brewer's conjecture and the feasibility of
consistent, available, partition-tolerant web services*, ACM SIGACT News 33(2),
51–59 (2002). `DOI <https://doi.org/10.1145/564585.564601>`__.

.. minigallery:: ../../examples/network/replication/plot_01_cap_theorem.py

2002 -- Kademlia: Routing by XOR Distance
-----------------------------------------

To find who stores a piece of data, Maymounkov and Mazières defined the distance
between identifiers as :math:`d(x, y) = x \oplus y`, read as an integer. It is
symmetric, and for any point and distance there is exactly one point at that
distance, so lookups from different nodes toward the same key converge on the
same path. Node :math:`x` keeps *k-buckets*: a few contacts at every scale of
distance,

.. math::

   \text{bucket}_i(x) \subseteq \{\, y : 2^i \le d(x, y) < 2^{i+1} \,\},
   \qquad |\text{bucket}_i| \le k.

If the highest bit in which :math:`x` and the key differ is bit :math:`i`, any
contact in :math:`\text{bucket}_i(x)` agrees with the key on that bit and so is
less than :math:`2^i` from it: each hop at least halves the distance. Because
:math:`n` random identifiers are spread evenly, about :math:`\log_2 n` halvings
reach the node closest to the key, so a lookup takes :math:`O(\log n)` hops. Kademlia runs BitTorrent's distributed hash table,
Ethereum's node discovery and IPFS.

*Implementation:* :class:`blockchainkit.network.systems.kademlia.KademliaNetwork`
and :func:`blockchainkit.network.systems.kademlia.xor_distance`. Buckets are
filled from global knowledge and lookups are greedy and single-path; real
Kademlia learns contacts from traffic, prefers long-lived ones, and queries
several contacts in parallel.

*References:* P. Maymounkov and D. Mazières, *Kademlia: A peer-to-peer
information system based on the XOR metric*, IPTPS 2002, LNCS 2429, 53–65
(2002). `DOI <https://doi.org/10.1007/3-540-45748-8_5>`__.

.. minigallery:: ../../examples/network/overlays/plot_01_kademlia.py

2002 -- The Sybil Attack
------------------------

On an open network, one person can pretend to be many, and any rule that counts
heads, such as a vote or a choice of who stores some data, can be taken over by
whoever creates the most identities. Douceur proved that without a logically
central, trusted authority that certifies identities, a peer-to-peer system
cannot prevent one entity from presenting many identities, limited only by its
resources. In Kademlia, for example, an attacker who chooses its own
identifiers can place a few right next to a key, become the nodes closest to
it, and answer every lookup for it. Systems can raise the cost of an identity
(requiring the identifier to be the hash of a public key, so the attacker must
grind keys; solving a puzzle) but cannot tie identities to people. Bitcoin
sidesteps the
problem by never counting identities: its consensus weighs computation, and its
network layer assumes that some neighbors may be hostile.

*Implementation:* :func:`blockchainkit.network.systems.kademlia.node_id` and
:meth:`blockchainkit.network.systems.kademlia.KademliaNetwork.closest`.

*References:* J. R. Douceur, *The Sybil attack*, IPTPS 2002, LNCS 2429,
251–260 (2002). `DOI <https://doi.org/10.1007/3-540-45748-8_24>`__.

.. minigallery:: ../../examples/network/overlays/plot_02_sybil_attack.py

2009 -- Announce, Then Fetch: inv and getdata
---------------------------------------------

The first Bitcoin client relayed blocks and transactions by announcement rather
than by sending them to every neighbor: an ``inv`` message carries hashes, a
peer requests unknown items with ``getdata``, and only then is the item sent, so
each node downloads each block once. In a connected graph with :math:`E` links
and :math:`n` peers, the origin sends to all its neighbors and every other peer
to all but the one it heard from, so :math:`2E - (n - 1)` messages cross the
links either way; what changes is how many of them carry the whole block:

.. math::

   \text{flooding: } 2E - (n - 1) \text{ full copies}, \qquad
   \text{announcing: } 2E - (n - 1) \text{ inv messages} + (n - 1) \text{ copies}.

Every peer still hears about the block from each neighbor, but the redundant
copies shrink from whole blocks to hashes of a few dozen bytes. The price is a
round trip at every hop (``inv``, ``getdata``, block: three messages instead
of one), which later motivated compact blocks.

*Implementation:* :func:`blockchainkit.network.systems.relay.relay_cost`,
checked against the message count of
:class:`blockchainkit.network.systems.gossip.SimulatedNetwork`. Costs are
counted analytically, one item per message; Bitcoin batches many hashes per
``inv`` and now relays headers first.

*References:* S. Nakamoto, Bitcoin v0.1 source code, ``main.cpp`` (2009);
`Bitcoin protocol documentation
<https://developer.bitcoin.org/reference/p2p_networking.html>`__.

.. minigallery:: ../../examples/network/relay/plot_01_inv_getdata.py

2013 -- Information Propagation and Forks
-----------------------------------------

A new block takes seconds to reach everyone, and during those seconds other
miners still work on the old chain; if one of them finds a block too, the chain
forks. Decker and Wattenhofer connected to thousands of Bitcoin peers and timed
how long blocks took to reach them: a median of 6.5 s and a mean of 12.6 s.
Because block discovery is a Poisson process with mean interval :math:`T`, the
probability that a competing block appears while a block propagates for
:math:`\tau` is

.. math::

   P_\text{fork} = 1 - e^{-\tau / T},

which at :math:`\tau = 12.6\text{ s}` and :math:`T = 600\text{ s}` predicts
about 2%, close to the 1.69% fork rate they observed. They showed that
propagation delay is the main cause of forks, and that relaying a block before
fully verifying it, or minimizing round trips, reduces them.

*Implementation:* :func:`blockchainkit.network.systems.propagation.fork_rate`
and :func:`blockchainkit.network.systems.propagation.simulate_fork_rate` use one
fixed delay; measured delays vary across peers and grow with block size, and
relay networks have shortened them since 2013.

*References:* C. Decker and R. Wattenhofer, *Information propagation in the
Bitcoin network*, IEEE P2P 2013, 1–10 (2013). `DOI
<https://doi.org/10.1109/P2P.2013.6688704>`__.

.. minigallery:: ../../examples/network/relay/plot_02_propagation_and_forks.py

2015 -- Eclipse Attacks
-----------------------

Heilman, Kendler, Zohar and Goldberg showed that an attacker with a few
thousand IP addresses could monopolize a Bitcoin node's connections by
repeatedly advertising its addresses and waiting for a restart. The eclipsed
node then sees only what the attacker shows it, and can be used to
double-spend against it, to waste its mining power, or to split the network.
If a fraction :math:`f` of the address table were the attacker's and
connections were independent draws,

.. math::

   P_\text{eclipse} = f^{\,\text{outbound}}.

With eight outbound connections, even :math:`f = 0.9` gives only 43%, so the
attacker must fill nearly the whole table, and its task is to push honest
addresses out. Bitcoin's address manager already placed each address in a
bucket chosen by a
secret hash of its network group, so an attacker with addresses in few groups
reaches few buckets; that is why the attack needed addresses spread over many
groups. The paper's countermeasures, adopted by Bitcoin Core, strengthened this
design with deterministic eviction, test-before-evict, feeler and anchor
connections, and more buckets.

*Implementation:* :class:`blockchainkit.network.systems.addresses.AddressManager`
and :func:`blockchainkit.network.systems.addresses.eclipse_probability` model
group bucketing and random eviction only; Bitcoin Core's address manager also
has separate new and tried tables, test-before-evict, and feeler and anchor
connections.

*References:* E. Heilman, A. Kendler, A. Zohar and S. Goldberg, *Eclipse
attacks on Bitcoin's peer-to-peer network*, 24th USENIX Security Symposium,
129–144 (2015).

.. minigallery:: ../../examples/network/overlays/plot_03_eclipse_attack.py

2016 -- Compact Block Relay
---------------------------

Peers usually already hold most of a new block's transactions in their
mempools. BIP 152, by Matt Corallo, therefore sends a block as its 80-byte
header, a nonce, and one 6-byte *short ID* per transaction, computed with
SipHash keyed by the header and nonce. The receiver rebuilds the block from its
mempool and requests the rest in one extra round trip:

.. math::

   \text{bytes} \approx 80 + 8 + 6\,n_{\text{tx}}
   + \sum_{\text{missing}} |\text{tx}|.

Since a transaction is typically a few hundred bytes, the block shrinks by
well over an order of magnitude. Six bytes are short enough that two
transactions with equal short IDs can be found by brute force, and such a
collision makes the receiver rebuild the wrong block; keying per block means an
attacker cannot precompute transactions whose IDs collide in every block.
Compact blocks cut the bandwidth and, in
high-bandwidth mode, the latency of block relay, attacking both causes of the
forks Decker and Wattenhofer measured.

*Implementation:* :func:`blockchainkit.network.systems.relay.compact_block_relay`
and :func:`blockchainkit.network.systems.relay.short_id` use SHA-256 in place
of SipHash, with no high-bandwidth mode or prefilled coinbase.

*References:* M. Corallo, *BIP 152: Compact block relay* (2016).
`Specification <https://github.com/bitcoin/bips/blob/master/bip-0152.mediawiki>`__.

.. minigallery:: ../../examples/network/relay/plot_03_compact_blocks.py

2017 -- Dandelion: Transaction-Origin Privacy
---------------------------------------------

The first node to announce a transaction is usually the one that created it.
Bitcoin's diffusion spreads a transaction outward from its source at roughly
the same speed in every direction, so the spy that hears it first is usually
next to the source. Bojja Venkatakrishnan, Fanti and Viswanath showed that
well-connected spies can link transactions to IP addresses this way, and
proposed
Dandelion: a *stem* phase that passes the transaction to one peer at a time,
continuing with probability :math:`q` at each hop, followed by a *fluff* phase
of ordinary diffusion. The expected stem length is

.. math::

   \mathbb{E}[\text{hops}] = \frac{1}{1 - q},

and the diffusion that spies observe starts where the stem ended, a random
number of hops away from the source. Routing stems over a line-shaped
anonymity graph gives nearly optimal privacy against the first-spy estimator.
Dandelion++ (2018) hardened the design, and variants are deployed in several
cryptocurrencies.

*Implementation:* :func:`blockchainkit.network.systems.privacy.first_spy_precision`
runs both modes, with stems as random walks on the peer graph itself rather
than over a separate anonymity graph.

*References:* S. Bojja Venkatakrishnan, G. Fanti and P. Viswanath, *Dandelion:
Redesigning the Bitcoin network for anonymity*, Proceedings of the ACM on
Measurement and Analysis of Computing Systems 1(1), 1–34 (2017). `DOI
<https://doi.org/10.1145/3084459>`__.

.. minigallery:: ../../examples/network/relay/plot_04_dandelion.py
