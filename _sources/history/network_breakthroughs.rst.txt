Breakthroughs in Peer-to-Peer Networking
========================================

.. include:: /_generated/nav/network.rst

Agreement needs communication. Peers learn about transactions and blocks by
gossip, find each other through overlays, and see the world only through the
connections they happen to have. This chronology traces the ideas behind
:mod:`blockchainkit.network`, from random graphs to Dandelion. Each entry has
its own experiment in the :doc:`gallery </api/gallery/network/index>`.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

1959 — Random graphs and the connectivity threshold
---------------------------------------------------

**In plain language.** If every pair of peers is linked by chance, the network
suddenly snaps from fragmented to connected once peers have about as many random
links as the logarithm of the network's size.

**Reading the experiment.** :math:`G(n, p)` links each of the :math:`n(n-1)/2`
pairs of :math:`n` peers independently with probability :math:`p`. The x-axis
rescales :math:`p` by :math:`\ln n / n`, so the threshold sits at 1.

Erdős and Rényi founded the theory of random graphs by asking which properties
appear, and how suddenly, as links are added at random. Connectivity has a sharp
threshold:

.. math::

   P\bigl(G(n, p) \text{ connected}\bigr) \to
   \begin{cases} 0 & p < (1 - \varepsilon) \ln n / n, \\
                 1 & p > (1 + \varepsilon) \ln n / n. \end{cases}

Just below the threshold, what keeps the graph apart is almost always a few
isolated peers. Unstructured peer-to-peer networks such as Bitcoin's rely on this
result: a handful of random outbound links per node is enough to connect
thousands of nodes.

**Implementation:** :func:`blockchainkit.network.systems.topology.erdos_renyi`
and :class:`blockchainkit.network.systems.topology.Graph`.

**Experiment:** the gallery example sweeps :math:`p` around :math:`\ln n / n` for
two network sizes, compares the result with the limit law
:math:`\exp(-n^{1-c})` at :math:`p = c \ln n / n`, and shows that the obstacle
to connectivity is usually one isolated peer.

*References:* P. Erdős and A. Rényi, *On random graphs I*, Publicationes
Mathematicae Debrecen 6, 290–297 (1959).

.. minigallery:: ../../examples/network/graphs/plot_01_random_graphs.py


1961–1965 — Discrete-event simulation
-------------------------------------

**In plain language.** Instead of waiting for real time to pass, a simulator
keeps a list of things that will happen and jumps straight from one to the next.
With a fixed random seed, every run is identical.

**Reading the experiment.** Times are integer ticks. A peer that is cut off
misses a message, and reconnecting it does not resend old messages: the example
sends the announcement again.

Geoffrey Gordon's GPSS (1961) and Dahl and Nygaard's Simula (1965) made
*discrete-event simulation* a standard tool: the state changes only at events,
held in a queue ordered by time. The simulator pops the earliest event, sets the
clock to its time, and lets it schedule further events. Simula's objects and
classes, invented to model the simulated entities, went on to found
object-oriented programming.

**Implementation:** :class:`blockchainkit.network.systems.gossip.SimulatedNetwork`
schedules each message as a delivery event a seeded random number of ticks
after it is sent, suppresses duplicates, and drops in-flight messages when a
link is cut. It never sleeps or reads the wall clock.

**Experiment:** the gallery example partitions a peer, reconnects it, retransmits
the missing announcement, and replays the run to show it is exactly
reproducible.

*References:* G. Gordon, *A general purpose systems simulation program*, Proc.
Eastern Joint Computer Conference, 87–104 (1961); O.-J. Dahl and K. Nygaard,
*SIMULA — an ALGOL-based simulation language*, Communications of the ACM 9(9),
671–678 (1966). `DOI <https://doi.org/10.1145/365813.365819>`__.

.. minigallery:: ../../examples/network/events/plot_01_discrete_event_simulation.py


1978 — Lamport clocks: time from messages
-----------------------------------------

**In plain language.** Computers' clocks disagree, so we cannot always tell which
of two events was first. But if one event could have influenced another, by a
message or by happening earlier on the same computer, counters passed along
with the messages can always put the cause first.

**Reading the experiment.** Each horizontal line is a process, each dot an event
labeled with its Lamport time, and each arrow a message.

Lamport defined *happened before* (:math:`a \to b`) as the smallest relation in
which each process's events are ordered, each send precedes its receive, and
which is transitive. Each process keeps a counter :math:`C`, increments it at
every event, attaches it to messages, and on receiving a message with stamp
:math:`t` sets :math:`C \leftarrow \max(C, t) + 1`. This guarantees the *clock
condition*

.. math::

   a \to b \implies C(a) < C(b),

and ordering events by :math:`(C, \text{process})` gives a total order every
process computes alike. Lamport used it to replicate a state machine: if all
replicas apply the same commands in the same order, they stay identical, the
principle behind every blockchain. The converse of the clock condition fails:
:math:`C(a) < C(b)` does not mean :math:`a` caused :math:`b`.

**Implementation:** :func:`blockchainkit.network.systems.clocks.lamport_timestamps`;
the diagram is drawn by
:func:`blockchainkit.network.visualizers.plots.plot_space_time`.

**Experiment:** the gallery example stamps a three-process history, checks the
clock condition, builds the total order, and exhibits two concurrent events with
ordered timestamps.

*References:* L. Lamport, *Time, clocks, and the ordering of events in a
distributed system*, Communications of the ACM 21(7), 558–565 (1978). `DOI
<https://doi.org/10.1145/359545.359563>`__.

.. minigallery:: ../../examples/network/events/plot_02_lamport_clocks.py


1985–1987 — Rumor spreading in log₂ n + ln n rounds
---------------------------------------------------

**In plain language.** If everyone who knows a rumor tells one random person per
round, the number who know it doubles at first, then the last few take a while
to be reached. For a million people, about 34 rounds suffice.

**Reading the experiment.** Each round, every peer calls one random other peer,
and informed callers pass the rumor on (*push*). The left plot compares measured
rounds with :math:`\log_2 n + \ln n`.

Frieze and Grimmett showed that push gossip on the complete graph informs all
:math:`n` peers in :math:`\log_2 n + \ln n + o(\log n)` rounds, and Pittel
sharpened the error to :math:`O(1)`:

.. math::

   T_n = \log_2 n + \ln n + O(1).

The :math:`\log_2 n` term is the doubling phase; the :math:`\ln n` term is a
coupon-collector phase, in which each remaining uninformed peer is missed by all
callers with probability about :math:`1/e` per round. Logarithmic spreading time
is why gossip scales to networks of any size.

**Implementation:** :func:`blockchainkit.network.systems.epidemics.spread_rumor`
and :func:`blockchainkit.network.systems.epidemics.pittel_rounds`.

**Experiment:** the gallery example measures rounds from 16 to 16,384 peers and
shows the gap to :math:`\log_2 n + \ln n` staying bounded.

*References:* A. M. Frieze and G. R. Grimmett, *The shortest-path problem for
graphs with random arc-lengths*, Discrete Applied Mathematics 10, 57–77 (1985);
B. Pittel, *On spreading a rumor*, SIAM Journal on Applied Mathematics 47(1),
213–223 (1987). `DOI <https://doi.org/10.1137/0147013>`__.

.. minigallery:: ../../examples/network/gossip/plot_02_rumor_spreading.py


1987 — Epidemic algorithms for replicated databases
---------------------------------------------------

**In plain language.** Copies of a database can stay in sync with no central
server if each copy regularly chats with a random other copy, like a disease
passing from person to person. Asking "what's new?" finishes the job faster
than only telling.

**Reading the experiment.** The plot shows, on a log scale, the fraction of
replicas still unaware of an update after each round, for *push*, *pull* and
*push-pull* exchanges.

Demers and colleagues at Xerox PARC analyzed epidemic protocols for keeping the
replicas of Xerox's Clearinghouse name service consistent. If a fraction
:math:`s_i` of replicas is uninformed after round :math:`i`, then once most
replicas know the update,

.. math::

   \text{push: } s_{i+1} \approx s_i e^{-1}, \qquad
   \text{pull: } s_{i+1} \approx s_i^2,

because an uninformed puller stays uninformed only by calling another
uninformed replica. They also introduced *anti-entropy* (periodically
reconciling whole databases) and *rumor mongering* (spreading a new update
until it seems old news). Block and transaction relay in Bitcoin descends from
these ideas.

**Implementation:** :func:`blockchainkit.network.systems.epidemics.spread_rumor`
with ``mode`` set to ``"push"``, ``"pull"`` or ``"push-pull"``;
:func:`blockchainkit.network.visualizers.plots.plot_rumor_spread`.

**Experiment:** the gallery example spreads an update among 4096 replicas and
checks the constant-factor decay of push against the squaring of pull.

*References:* A. Demers et al., *Epidemic Algorithms for Replicated Database
Maintenance*, PODC '87, 1–12 (1987). `DOI
<https://doi.org/10.1145/41840.41841>`__.

.. minigallery:: ../../examples/network/gossip/plot_01_epidemic_algorithms.py


1987 — Bracha's reliable broadcast
----------------------------------

**In plain language.** A dishonest sender might tell half the group one thing and
half another. If everyone first repeats what they heard and waits for enough
others to agree, either all honest members end up with the same message or none
accepts any.

**Reading the experiment.** Process 0 is the sender; ``t`` is the number of faulty
processes tolerated. The bar chart counts outcomes over every split of the
proposals the faulty sender and an accomplice can try.

Bracha built Byzantine *reliable broadcast* from two all-to-all phases. On the
sender's value, each process sends ECHO; on
:math:`\lceil (n + t + 1)/2 \rceil` echoes, or :math:`t + 1` READY messages, for
a value it sends READY once; on :math:`2t + 1` READY messages it delivers. Two
echo quorums of that size overlap in more than :math:`t` processes, so in a
correct one, which echoes only one value. Hence no two correct processes become
ready for different values, and the :math:`t + 1` amplification rule makes
delivery all-or-nothing, provided

.. math::

   n > 3t.

Reliable broadcast is a building block of asynchronous Byzantine consensus and
of modern DAG-based blockchain protocols.

**Implementation:** :func:`blockchainkit.network.systems.broadcast.reliable_broadcast`
runs the protocol in synchronous rounds against faulty processes that collude
with the sender's split.

**Experiment:** the gallery example contrasts trusting the sender with Bracha's
protocol, checks every split exhaustively for :math:`n = 7`, and breaks
agreement with one faulty process too many.

*References:* G. Bracha, *Asynchronous Byzantine agreement protocols*,
Information and Computation 75(2), 130–143 (1987). `DOI
<https://doi.org/10.1016/0890-5401(87)90054-X>`__.

.. minigallery:: ../../examples/network/gossip/plot_03_reliable_broadcast.py


1988 — Vector clocks: detecting concurrency
-------------------------------------------

**In plain language.** A single counter can put causes before effects, but cannot
say when two events happened independently. Keeping one counter per computer
can.

**Reading the experiment.** The matrix compares every pair of events: red or
blue if one happened before the other, white if they are concurrent.

Fidge and Mattern independently replaced Lamport's scalar with a vector
:math:`V` of :math:`n` counters. Process :math:`p` increments :math:`V[p]` at each
event and, on receipt, first takes the entrywise maximum with the vector carried
by the message. Then :math:`V(a)[q]` counts the events at :math:`q` that happened
before or at :math:`a`, and causality is characterized exactly:

.. math::

   a \to b \iff V(a) \le V(b) \text{ entrywise and } V(a) \ne V(b).

Events with incomparable vectors are concurrent. Replicated data stores use
vector clocks, and their descendants, to detect conflicting updates that must
be reconciled.

**Implementation:** :func:`blockchainkit.network.systems.clocks.vector_timestamps`,
:func:`blockchainkit.network.systems.clocks.happened_before` and
:func:`blockchainkit.network.systems.clocks.concurrent`.

**Experiment:** the gallery example classifies every pair of events of the
Lamport example's history and confirms that Lamport order never contradicts
causal order but cannot see concurrency.

*References:* C. J. Fidge, *Timestamps in message-passing systems that preserve
the partial ordering*, Proc. 11th Australian Computer Science Conference, 56–66
(1988); F. Mattern, *Virtual time and global states of distributed systems*,
Parallel and Distributed Algorithms, 215–226 (North-Holland, 1989).

.. minigallery:: ../../examples/network/events/plot_03_vector_clocks.py


1998 — Small-world networks
---------------------------

**In plain language.** In a network where everyone knows only their neighbors,
messages crawl. Adding a few random long-distance links makes everyone close to
everyone, while neighbors still mostly know each other.

**Reading the experiment.** :math:`L` is the average number of hops between two
peers and :math:`C` the clustering: the fraction of a peer's neighbor pairs that
are linked. Both are divided by their values for the unrewired ring.

Watts and Strogatz started from a ring lattice, where each node links to its
:math:`k` nearest neighbors, and rewired each link to a random node with
probability :math:`p`. The lattice has high clustering,
:math:`C(0) = 3(k-2)/(4(k-1))`, but long paths, :math:`L(0) \approx n/2k`. Already
at :math:`p \approx 0.01`, :math:`L` drops close to the random-graph value
:math:`\ln n / \ln k`, while :math:`C` barely moves: each shortcut shortens
many paths but changes the clustering of only two nodes. They found such small
worlds in actors' collaborations, the power grid and a nervous system.

**Implementation:** :func:`blockchainkit.network.systems.topology.watts_strogatz`,
:func:`blockchainkit.network.systems.topology.ring_lattice`,
:meth:`blockchainkit.network.systems.topology.Graph.average_path_length` and
:meth:`blockchainkit.network.systems.topology.Graph.clustering`.

**Experiment:** the gallery example reproduces the paper's :math:`L(p)` and
:math:`C(p)` curves and compares gossip on the lattice and a 1%-rewired graph.

*References:* D. J. Watts and S. H. Strogatz, *Collective dynamics of
'small-world' networks*, Nature 393, 440–442 (1998). `DOI
<https://doi.org/10.1038/30918>`__.

.. minigallery:: ../../examples/network/graphs/plot_02_small_world.py


1999 — Scale-free networks
--------------------------

**In plain language.** When newcomers prefer to connect to popular nodes, the
popular ones become more popular still. The result is a network with a few huge
hubs and many small nodes, which shrugs off random failures but suffers when
its hubs are attacked.

**Reading the experiment.** :math:`P(k)` is the fraction of nodes with :math:`k`
links, on log-log axes, where a power law is a straight line.

Barabási and Albert observed that the Web's link counts follow a power law,
unlike the Poisson degrees of a random graph, and explained it by growth with
*preferential attachment*: each new node links to :math:`m` existing nodes with
probability proportional to their degree. Their continuum argument gives a
degree distribution that does not depend on time or network size:

.. math::

   P(k) \approx \frac{2m^2}{k^3}.

Hubs shorten paths and speed up gossip, but concentrate risk: Albert, Jeong and
Barabási (2000) showed such networks are robust to random failures yet fragile
under targeted attacks on their hubs.

**Implementation:** :func:`blockchainkit.network.systems.topology.barabasi_albert`.

**Experiment:** the gallery example fits the degree exponent, compares the
largest degree with an equally dense random graph, and removes 5% of nodes at
random or by degree.

*References:* A.-L. Barabási and R. Albert, *Emergence of scaling in random
networks*, Science 286(5439), 509–512 (1999). `DOI
<https://doi.org/10.1126/science.286.5439.509>`__.

.. minigallery:: ../../examples/network/graphs/plot_03_scale_free.py


2000–2002 — The CAP theorem
---------------------------

**In plain language.** When a network splits, a replicated service must choose:
refuse some requests, or answer them knowing the other side may disagree. It
cannot have both while the split lasts.

**Reading the experiment.** Five replicas are split 2 to 3. *Refused* counts
requests a replica declined; *stale* counts successful reads that missed an
earlier successful write.

Brewer conjectured in a 2000 keynote that a distributed system can provide at
most two of *consistency*, *availability* and *partition tolerance*. Gilbert and
Lynch proved it: in an asynchronous network that may lose messages, no
read/write register can guarantee that every request to a live replica succeeds
and that every operation is linearizable. Since partitions cannot be ruled out,
the real choice is between consistency and availability *during* a partition.
Quorum systems such as PBFT choose consistency: the minority side stalls.
Nakamoto consensus chooses availability: both sides keep extending a chain, and
one side's blocks are discarded when the network heals.

**Implementation:** :class:`blockchainkit.network.systems.replication.ReplicatedRegister`
with ``mode="consistent"`` (majority quorums) or ``mode="available"`` (answer
locally, last writer wins on healing).

**Experiment:** the gallery example runs one workload against both policies and
counts refused requests, stale reads and the write lost at healing.

*References:* E. A. Brewer, *Towards robust distributed systems*, keynote, PODC
2000; S. Gilbert and N. Lynch, *Brewer's conjecture and the feasibility of
consistent, available, partition-tolerant web services*, ACM SIGACT News 33(2),
51–59 (2002). `DOI <https://doi.org/10.1145/564585.564601>`__.

.. minigallery:: ../../examples/network/replication/plot_01_cap_theorem.py


2002 — Kademlia
---------------

**In plain language.** To find who stores a piece of data, each computer keeps a
few contacts that are "far", a few that are "medium" and a few that are "near",
and each step of the search at least halves the remaining distance.

**Reading the experiment.** Identifiers are 32-bit numbers; distance is their
bitwise XOR. ``k`` is how many contacts a node keeps per distance scale.

Maymounkov and Mazières defined the distance between identifiers as
:math:`d(x, y) = x \oplus y`, read as an integer. It is symmetric, and for any
point and distance there is exactly one point at that distance, so lookups from
different nodes toward the same key converge on the same path. Node :math:`x`
keeps *k-buckets*: bucket :math:`i` holds up to :math:`k` contacts with
:math:`2^i \le d(x, y) < 2^{i+1}`. Each hop fixes at least the highest differing
bit, so a lookup takes :math:`O(\log n)` hops. Kademlia runs BitTorrent's
distributed hash table, Ethereum's node discovery and IPFS.

**Implementation:** :class:`blockchainkit.network.systems.kademlia.KademliaNetwork`
fills every bucket from global knowledge and routes greedily;
:func:`blockchainkit.network.systems.kademlia.xor_distance`.

.. admonition:: Teaching vs production
   :class: note

   Buckets here are filled from global knowledge and lookups are greedy and
   single-path. Real Kademlia learns contacts from traffic, prefers long-lived
   ones, and queries three contacts in parallel. See :doc:`/protocol` for this
   package's exact conventions.

**Experiment:** the gallery example measures lookup hops from 64 to 4096 nodes
for two bucket sizes and prints one route bit by bit.

*References:* P. Maymounkov and D. Mazières, *Kademlia: A peer-to-peer
information system based on the XOR metric*, IPTPS 2002, LNCS 2429, 53–65
(2002). `DOI <https://doi.org/10.1007/3-540-45748-8_5>`__.

.. minigallery:: ../../examples/network/overlays/plot_01_kademlia.py


2002 — The Sybil attack
-----------------------

**In plain language.** On an open network, one person can pretend to be many
people. Any rule that counts heads, such as a vote or a choice of who stores
some data, can be taken over by whoever creates the most fake identities.

**Reading the experiment.** Honest nodes have random identifiers; the attacker's
*Sybils* are placed next to one key. In the second part, identifiers must be
the hash of a public key, so the attacker has to try many keys.

Douceur proved that without a logically central, trusted authority that
certifies identities, a peer-to-peer system cannot prevent one entity from
presenting many identities, limited only by its resources. Systems can raise
the cost of an identity (hashing a public key, solving a puzzle) but not tie
identities to people. Bitcoin sidesteps the problem by never counting
identities: its consensus weighs computation, and its network layer assumes
some neighbors may be hostile.

**Implementation:** :func:`blockchainkit.network.systems.kademlia.node_id` and
:meth:`blockchainkit.network.systems.kademlia.KademliaNetwork.closest`.

**Experiment:** the gallery example lets eight chosen-identifier Sybils capture
every honest lookup for a key, then measures the cost of grinding hashed
identifiers that share :math:`d` bits with the key, which grows like
:math:`2^d`.

*References:* J. R. Douceur, *The Sybil attack*, IPTPS 2002, LNCS 2429, 251–260
(2002). `DOI <https://doi.org/10.1007/3-540-45748-8_24>`__.

.. minigallery:: ../../examples/network/overlays/plot_02_sybil_attack.py


2009 — Announce, then fetch: inv and getdata
--------------------------------------------

**In plain language.** Instead of sending a big block to every neighbor, a node
first says "I have block X". Only neighbors that don't have it ask for it, so
each node downloads each block once.

**Reading the experiment.** Traffic is the total over all links for one 1 MB
block. Time is counted in one-way link latencies.

The first Bitcoin client relayed blocks and transactions by announcement: an
``inv`` message carries hashes, a peer requests unknown items with ``getdata``,
and only then is the item sent. For a connected graph with :math:`E` links and
:math:`n` peers, flooding sends :math:`2E - (n - 1)` full copies, while
announcing sends that many small ``inv`` messages and only :math:`n - 1` copies.
The price is a round trip at every hop: three messages instead of one, which
later motivated compact blocks.

**Implementation:** :func:`blockchainkit.network.systems.relay.relay_cost`, checked
against the message count of
:class:`blockchainkit.network.systems.gossip.SimulatedNetwork`.

.. admonition:: Teaching vs production
   :class: note

   Costs here are counted analytically, one item per message. Bitcoin batches many
   hashes per ``inv`` and now relays headers first. See :doc:`/protocol` for this
   package's exact conventions.

**Experiment:** the gallery example compares the traffic and delay of flooding and
announcing as the number of links per peer grows.

*References:* S. Nakamoto, Bitcoin v0.1 source code, ``main.cpp`` (2009);
`Bitcoin protocol documentation <https://developer.bitcoin.org/reference/p2p_networking.html>`__.

.. minigallery:: ../../examples/network/relay/plot_01_inv_getdata.py


2013 — Information propagation and forks
----------------------------------------

**In plain language.** A new block takes several seconds to reach everyone.
During those seconds other miners still work on the old chain, and if one of
them finds a block too, the chain forks. Slower relay means more forks.

**Reading the experiment.** :math:`T` is the mean time between blocks. The curve
is the formula, the dots a simulation of Poisson block discoveries.

Decker and Wattenhofer connected to thousands of Bitcoin peers and timed how
long blocks took to reach them: a median of 6.5 s and a mean of 12.6 s. Because
block discovery is a Poisson process, the probability that a competing block is
found while a block of delay :math:`\tau` propagates is

.. math::

   P_\text{fork} = 1 - e^{-\tau / T},

which at :math:`\tau = 12.6\text{ s}` and :math:`T = 600\text{ s}` predicts about
2%, close to the 1.69% fork rate they observed. They showed that propagation
delay is the main cause of forks, and that relaying a block before fully
verifying it, or minimizing round trips, reduces them.

**Implementation:** :func:`blockchainkit.network.systems.propagation.fork_rate` and
:func:`blockchainkit.network.systems.propagation.simulate_fork_rate`.

.. admonition:: Teaching vs production
   :class: note

   The model uses one fixed propagation delay. Measured delays vary across peers
   and grow with block size, and relay networks have shortened them since 2013.
   See :doc:`/protocol` for this package's exact conventions.

**Experiment:** the gallery example compares the formula with simulation for block
intervals from 15 s to 20 minutes and computes the delay budget for 1% forks.

*References:* C. Decker and R. Wattenhofer, *Information propagation in the
Bitcoin network*, IEEE P2P 2013, 1–10 (2013). `DOI
<https://doi.org/10.1109/P2P.2013.6688704>`__.

.. minigallery:: ../../examples/network/relay/plot_02_propagation_and_forks.py


2015 — Eclipse attacks
----------------------

**In plain language.** If an attacker fills a node's address book with its own
addresses, every connection the node opens leads to the attacker, who then
decides what the node sees. Sorting addresses into groups the attacker cannot
fill stops the flood.

**Reading the experiment.** The table holds 64 buckets of 16 addresses. The
attacker sends 5000 addresses from 4 network groups; honest addresses come from
1000 groups. A node is *eclipsed* when all 8 outbound connections are the
attacker's.

Heilman, Kendler, Zohar and Goldberg showed that an attacker with a few thousand
IP addresses could monopolize a Bitcoin node's connections by repeatedly
advertising its addresses and waiting for a restart. An eclipsed node can be
used to double-spend against it, to waste its mining power, or to split the
network. Bitcoin's address manager already placed each address in a bucket
chosen by a secret hash of its network group, so an attacker with addresses in
few groups reaches few buckets; that is why the attack needed addresses spread
over many groups. The paper's countermeasures, adopted by Bitcoin Core,
strengthened this design with deterministic eviction, test-before-evict, feeler
and anchor connections, and more buckets. If a fraction :math:`f` of entries
were the attacker's and connections were independent draws,

.. math::

   P_\text{eclipse} = f^{\,\text{outbound}}.

**Implementation:** :class:`blockchainkit.network.systems.addresses.AddressManager`
and :func:`blockchainkit.network.systems.addresses.eclipse_probability`.

.. admonition:: Teaching vs production
   :class: note

   ``AddressManager`` models group bucketing and random eviction only. Bitcoin
   Core's address manager has separate new and tried tables, test-before-evict,
   feeler and anchor connections. See :doc:`/protocol` for this package's exact
   conventions.

**Experiment:** the gallery example floods tables with and without group
bucketing and measures how often eight selections are all the attacker's.

*References:* E. Heilman, A. Kendler, A. Zohar and S. Goldberg, *Eclipse attacks
on Bitcoin's peer-to-peer network*, 24th USENIX Security Symposium, 129–144
(2015).

.. minigallery:: ../../examples/network/overlays/plot_03_eclipse_attack.py


2016 — Compact blocks
---------------------

**In plain language.** Peers usually already have most of a new block's
transactions, so the sender lists short fingerprints instead of the
transactions, and the receiver rebuilds the block from what it already has.

**Reading the experiment.** The block has 2000 transactions of 250 bytes. Mempool
coverage is the fraction of them the receiver already holds.

BIP 152, by Matt Corallo, sends a block as its 80-byte header, a nonce and one
6-byte *short ID* per transaction, computed with SipHash keyed by the header and
nonce. The receiver matches short IDs against its mempool and requests the rest
in one extra round trip. Keying per block means an attacker cannot precompute
transactions whose IDs collide in every block. Compact blocks cut the bandwidth
and, with high-bandwidth mode, the latency of block relay, attacking both causes
of the forks Decker and Wattenhofer measured.

**Implementation:** :func:`blockchainkit.network.systems.relay.compact_block_relay`
and :func:`blockchainkit.network.systems.relay.short_id` (SHA-256 in place of
SipHash).

.. admonition:: Teaching vs production
   :class: note

   Short IDs here use SHA-256 instead of SipHash, and there is no high-bandwidth
   mode or prefilled coinbase. See :doc:`/protocol` for this package's exact
   conventions.

**Experiment:** the gallery example compares compact and full sizes as mempool
coverage falls, and shows short IDs of one or two bytes collapsing into
ambiguity.

*References:* M. Corallo, *BIP 152: Compact block relay* (2016).
`Specification <https://github.com/bitcoin/bips/blob/master/bip-0152.mediawiki>`__.

.. minigallery:: ../../examples/network/relay/plot_03_compact_blocks.py


2017 — Dandelion: transaction-origin privacy
--------------------------------------------

**In plain language.** The first node to shout news is usually the one who
started it. If a transaction first passes quietly along a random chain of
nodes before anyone shouts it, eavesdroppers learn only where the chain ended.

**Reading the experiment.** 10% of the peers are spies. *Precision* is how often
the spies' best guess, the peer that first sent the transaction to any spy,
is the true origin.

Bojja Venkatakrishnan, Fanti and Viswanath showed that Bitcoin's diffusion lets
well-connected spies link transactions to IP addresses, and proposed Dandelion:
a *stem* phase that forwards the transaction to one peer at a time, continuing
with probability :math:`q` at each hop, followed by a *fluff* phase of ordinary
diffusion. They proved that routing stems over a line-shaped anonymity graph
gives nearly optimal privacy against the first-spy estimator. Dandelion++
(2018) hardened the design, and variants are deployed in several
cryptocurrencies.

**Implementation:** :func:`blockchainkit.network.systems.privacy.first_spy_precision`
runs both modes; stems are random walks on the peer graph itself.

.. admonition:: Teaching vs production
   :class: note

   Stems here are random walks on the peer graph. Dandelion routes them over a
   separate line-shaped anonymity graph, and Dandelion++ adds further defenses.
   See :doc:`/protocol` for this package's exact conventions.

**Experiment:** the gallery example measures the first-spy precision of diffusion
and Dandelion and varies the stem probability.

*References:* S. Bojja Venkatakrishnan, G. Fanti and P. Viswanath, *Dandelion:
Redesigning the Bitcoin network for anonymity*, Proceedings of the ACM on
Measurement and Analysis of Computing Systems 1(1), 1–34 (2017). `DOI
<https://doi.org/10.1145/3084459>`__.

.. minigallery:: ../../examples/network/relay/plot_04_dandelion.py
