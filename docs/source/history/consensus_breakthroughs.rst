Breakthroughs in Consensus
==========================

.. include:: /_generated/nav/consensus.rst

.. epigraph::

   "The longest chain not only serves as proof of the sequence of events
   witnessed, but proof that it came from the largest pool of CPU power."
   -- Satoshi Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*, 2008

Signatures say who authorized a payment; they cannot say which of two
conflicting payments came first. Consensus mechanisms answer that question,
either by voting among known participants or by making some resource scarce:
computation, or stake. This chronology traces the ideas behind
:mod:`blockchainkit.consensus` along three threads that meet in Bitcoin and
Ethereum. Voting among known participants runs from the Byzantine generals
to PBFT. Scarce computation runs from pricing via processing to Nakamoto
consensus, with the gambler's ruin supplying the security argument. Scarce
stake runs from Peercoin to Casper finality and Algorand's committees. The
models are deliberately idealized; :doc:`/protocol` lists where they depart
from deployed protocols.

.. contents:: Timeline
   :local:
   :depth: 1

1656 -- The Gambler's Ruin: Catching Up from Behind
---------------------------------------------------

In 1656 Pascal posed to Fermat the problem of two gamblers playing until one is
ruined, and Huygens published it the next year. For a walk that steps toward
the goal with probability :math:`q` and away with :math:`p = 1 - q`, the chance
of ever making up a deficit of :math:`z` is

.. math::

   P_z = \begin{cases} 1 & q \ge p, \\ (q/p)^{z} & q < p. \end{cases}

An attacker mining a secret chain is exactly this player. Each new block is
one step: it is the attacker's, closing the gap by one, with probability
:math:`q` equal to the attacker's share of the hashrate, and otherwise the
honest network's, widening it by one. Section 11 of the Bitcoin whitepaper
applies the result to an attacker racing the honest chain: below half the
hashrate, the chance of ever catching up falls exponentially with every block
of lead.

*Implementation:* :func:`blockchainkit.consensus.systems.catch_up.eventual_catch_up`.

*References:* C. Huygens, *De ratiociniis in ludo aleae* (1657), problem 5; the
problem was posed in the Pascal-Fermat correspondence of 1656.

.. minigallery:: ../../examples/consensus/attacks/plot_01_gamblers_ruin.py

1982 -- The Byzantine Generals Problem
--------------------------------------

Generals surrounding a city must all attack or all retreat, but some are
traitors who tell different generals different things. Lamport, Shostak and
Pease gave the problem its name and its answer: with oral (unsigned) messages,
the loyal generals can agree despite :math:`m` traitors if and only if

.. math::

   n \ge 3m + 1.

Their algorithm OM(:math:`m`) has each lieutenant relay the order it received,
recursively for :math:`m` rounds, and decide by majority. The bound is tight
already for three generals and one traitor. If the commander says "attack" to
one lieutenant and "retreat" to the other, the first lieutenant hears
"attack" from the commander and "retreat" relayed by its peer. A loyal
commander and a lying peer would produce exactly the same messages, so the
lieutenant cannot tell which one is the traitor, and no rule can be right in
both cases. With signed messages a forged relay would be detected, and the
bound disappears. Later papers write the number of faults as :math:`f`, and
the :math:`3f + 1` bound reappears in every Byzantine fault-tolerant
blockchain protocol.

*Implementation:* :func:`blockchainkit.consensus.systems.byzantine.oral_messages`
runs OM(:math:`m`) with a configurable traitor strategy.

*References:* L. Lamport, R. Shostak, and M. Pease, *The Byzantine Generals
Problem*, ACM Transactions on Programming Languages and Systems 4(3), 382–401
(1982). `DOI <https://doi.org/10.1145/357172.357176>`__.

.. minigallery:: ../../examples/consensus/agreement/plot_01_byzantine_generals.py

1983 -- Ben-Or's Randomized Consensus
-------------------------------------

The same year, Fischer, Lynch and Paterson presented the impossibility result
of the 1985 entry below: no deterministic protocol can guarantee agreement in
an asynchronous network where a process may crash. Michael Ben-Or escaped it
by letting processes flip coins, giving the first asynchronous consensus
protocol that tolerates :math:`f` crashes among :math:`n > 2f` processes.

Each round has two exchanges, and in each a process waits for only
:math:`n - f` messages, because the other :math:`f` may never arrive. First,
every process reports its current value. A process then proposes :math:`v` if
more than :math:`n/2` of the reports it received are :math:`v`, a strict
majority of all processes, and otherwise proposes nothing. Two values cannot both have a strict majority, so
all proposals in a round name the same value. A process decides :math:`v`
after receiving :math:`f + 1` proposals of :math:`v`, adopts :math:`v` after
receiving at least one, and otherwise flips a coin for its next value. Once
all correct processes hold the same value, every one of them proposes it and
decides. Fresh coins are flipped in every round, so that moment comes sooner
or later.

Against any message scheduler, termination therefore has probability one. With
:math:`n` independent coins the expected number of rounds can be exponential
in :math:`n`, which later common-coin protocols reduced to a constant.

*Implementation:* :func:`blockchainkit.consensus.systems.randomized.ben_or`,
with an adversarial or random message scheduler.

*References:* M. Ben-Or, *Another Advantage of Free Choice: Completely
Asynchronous Agreement Protocols*, PODC '83, 27–30 (1983). `DOI
<https://doi.org/10.1145/800221.806707>`__.

.. minigallery:: ../../examples/consensus/agreement/plot_02_ben_or.py

1985 -- FLP: No Deterministic Consensus in an Asynchronous Network
------------------------------------------------------------------

Fischer, Lynch and Paterson proved that if messages can be delayed arbitrarily
and even one process might crash, every deterministic protocol has a schedule
in which it never decides. The proof finds a *bivalent* configuration, from
which both decisions are still reachable, and shows that an adversary who only
chooses the order of delivery can always keep it bivalent.

The conference version appeared in 1983; this is the journal version. Every
practical consensus protocol escapes by weakening an assumption:
randomization (Ben-Or), partial synchrony (Dwork, Lynch and Stockmeyer), or
probabilistic finality (Nakamoto).

*Implementation:* :func:`blockchainkit.consensus.systems.randomized.ben_or`
with a deterministic ``coin`` shows one such stalling schedule: without its
coins, Ben-Or's protocol is deterministic again and falls under the theorem.

*References:* M. J. Fischer, N. A. Lynch, and M. S. Paterson, *Impossibility of
Distributed Consensus with One Faulty Process*, Journal of the ACM 32(2),
374–382 (1985). `DOI <https://doi.org/10.1145/3149.214121>`__.

.. minigallery:: ../../examples/consensus/agreement/plot_03_flp_impossibility.py

1988 -- Partial Synchrony: Progress after an Unknown Stabilization Time
-----------------------------------------------------------------------

Networks are usually fast and sometimes slow. Dwork, Lynch and Stockmeyer
introduced partially synchronous models, in which a delay bound :math:`\Delta`
exists but is unknown, or holds only after an unknown global stabilization time
(GST), and showed that consensus is then solvable for :math:`n \ge 3f + 1`
Byzantine faults. The design separates safety from progress. Safety rests on
overlapping quorums, never on timing, so the protocol stays safe even while
the network misbehaves. Progress needs a leader whose messages arrive before
the others give up on it. Each view's leader gets a timeout that doubles after
every failed view, :math:`T_v = T_0\,2^{v}`. Views keep starting and timeouts
grow without bound, so some view eventually starts after GST with a timeout
longer than the delay:

.. math::

   \exists\, v:\ t_v \ge \text{GST} \ \wedge\ T_v \ge \Delta.

Rotating the leader among the views that follow reaches an honest one within
:math:`f + 1` views. Progress is guaranteed without ever knowing
:math:`\Delta`. PBFT, Tendermint and HotStuff all assume this model.

*Implementation:* :func:`blockchainkit.consensus.systems.synchrony.view_changes`.

*References:* C. Dwork, N. Lynch, and L. Stockmeyer, *Consensus in the Presence
of Partial Synchrony*, Journal of the ACM 35(2), 288–323 (1988). `DOI
<https://doi.org/10.1145/42282.42283>`__.

.. minigallery:: ../../examples/consensus/agreement/plot_04_partial_synchrony.py

1992 -- Pricing via Processing
------------------------------

To fight junk mail, Dwork and Naor proposed that every message should cost its
sender a little computation: too little to bother an ordinary user, too much
for someone sending millions, and instantly checkable by the recipient. Their
*pricing functions* are moderately hard to compute, easy to verify, and cannot
be amortized across messages. One example is the modular square root, for
:math:`p \equiv 3 \pmod 4`:

.. math::

   r = x^{(p+1)/4} \bmod p \quad (\approx 1.5 \log_2 p \text{ multiplications}),
   \qquad r^2 \equiv x \pmod p \quad (1 \text{ multiplication}).

The gap between computing and checking is only a factor of about
:math:`\log_2 p`. Raising the price means enlarging :math:`p`, which also
makes the verifier's multiplication more expensive. Later designs therefore
moved to puzzles whose cost grows exponentially in a tunable parameter while
checking stays a single cheap step. The idea of attaching a verifiable
computational cost is the root of proof of work.

*Implementation:* :func:`blockchainkit.consensus.systems.pricing.modular_square_root`
counts its multiplications.

*References:* C. Dwork and M. Naor, *Pricing via Processing or Combatting Junk
Mail*, CRYPTO '92, LNCS 740, 139–147 (1993). `DOI
<https://doi.org/10.1007/3-540-48071-4_10>`__.

.. minigallery:: ../../examples/consensus/pow/plot_01_pricing_via_processing.py

1997-2002 -- Hashcash and Proofs of Computational Effort
--------------------------------------------------------

Adam Back's Hashcash (proposed in 1997, described in a 2002 paper) priced
requests with a hash puzzle: the sender varies a nonce until the hash meets a
target, and the recipient checks the answer with a single hash. With
:math:`d` required leading zero bits, each attempt succeeds with probability
:math:`2^{-d}`:

.. math::

   H(\mathrm{header})\leq 2^{256-d}-1,\qquad
   \Pr[\mathrm{success}]=2^{-d},\qquad \mathbb{E}[T]=2^d.

Here :math:`T` counts attempts. The cost is tunable and exponential in
:math:`d`. Each attempt is an independent trial, so :math:`T` is geometric and
any one search can finish much earlier or later than the average. Bitcoin's
proof of work is Hashcash applied to block headers. Because the trials are
memoryless, blocks across the whole network arrive as a Poisson process,
which the 2008 double-spend calculation relies on.

*Implementation:* :func:`blockchainkit.consensus.systems.pow.mine` searches a
bounded nonce interval; :func:`blockchainkit.consensus.systems.pow.valid_pow`
checks one hash. Difficulty counts leading zero bits of SHA-256 over this
package's header; Bitcoin compares the double SHA-256 of an 80-byte header with
a full 256-bit target.

*References:* A. Back, *Hashcash — A Denial of Service Counter-Measure* (2002),
describing the earlier 1997 proposal. `Author's paper
<http://www.hashcash.org/papers/hashcash.pdf>`__.

.. minigallery:: ../../examples/consensus/pow/plot_02_hashcash.py

1999 -- Practical Byzantine Fault Tolerance
-------------------------------------------

Castro and Liskov made Byzantine fault tolerance practical: a group of
:math:`3f + 1` replicas keeps one consistent log even if :math:`f` of them lie,
using a three-phase protocol (pre-prepare, prepare, commit) and view changes for
faulty leaders. A replica cannot wait for all :math:`3f + 1` votes, because
:math:`f` faulty replicas may stay silent, so it acts on a quorum of the
:math:`2f + 1` it can count on. Safety then rests on quorum intersection:

.. math::

   |Q_1 \cap Q_2| \ \ge\ 2(2f + 1) - (3f + 1) = f + 1.

Two quorums share at least :math:`f + 1` replicas, so at least one of them is
honest. That replica never votes for two values in one view, so two
conflicting values can never both gather a quorum. With more than :math:`f` faults that guarantee
disappears. Tendermint, HotStuff and many proof-of-stake chains descend from
PBFT.

*Implementation:* :func:`blockchainkit.consensus.systems.pbft.pbft_round` runs
one normal-case round with a fixed leader and synchronous delivery, with
:func:`blockchainkit.consensus.systems.pbft.quorum_size`. It has no view
changes, checkpoints, request batching or message authentication.

*References:* M. Castro and B. Liskov, *Practical Byzantine Fault Tolerance*,
3rd Symposium on Operating Systems Design and Implementation (OSDI), 173–186
(1999).

.. minigallery:: ../../examples/consensus/agreement/plot_05_pbft.py

2008-2009 -- Nakamoto Consensus: Bitcoin Combines the Ingredients
-----------------------------------------------------------------

Alice could sign two payments that each spend her entire balance: both
signatures are valid, but both payments cannot be accepted. Nakamoto's 2008
proposal solved this double-spending problem without a trusted party by
combining earlier ingredients: signatures, hash-linked blocks, proof of work,
and peer-to-peer gossip. Peers accept the valid chain with the most cumulative
work, and switch when a heavier one appears:

.. math::

   \text{tip} = \arg\max_{\text{valid chains } C} \sum_{b \in C} \text{work}(b).

Work cannot be faked, so to replace a block an attacker must redo it and then
outpace the rest of the network. With less than half the hashrate this is the
losing gambler of 1656. An earlier payment can still be undone by a reorganization, so no finite number
of confirmations gives unconditional finality; the 2008 entry below computes
how fast the risk falls.

*Implementation:* :class:`blockchainkit.structures.systems.chain.Blockchain`
validates account transfers and selects the greatest cumulative work. Each fork
keeps its own :class:`blockchainkit.structures.systems.ledger.Ledger`, so a
reorganization restores balances and account nonces, and equal-work ties go to
the smaller hash so that experiments are reproducible. Difficulty is fixed by
genesis, and there are no UTXOs, coinbase rewards, fees, scripts, or wire
protocol: fork choice by cumulative work is the part reproduced.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008). `Original announcement
<https://www.metzdowd.com/pipermail/cryptography/2008-October/014810.html>`__;
`paper <https://bitcoin.org/bitcoin.pdf>`__.

.. minigallery:: ../../examples/consensus/nakamoto/plot_01_longest_chain.py

2008 -- How Many Confirmations? Nakamoto's Double-Spend Calculation
-------------------------------------------------------------------

A merchant who waits for more blocks on top of a payment is safer, because an
attacker must secretly build a longer chain. Section 11 of the whitepaper
computes how much safer, for an attacker with hashrate share :math:`q` (and
:math:`p = 1 - q` for the honest network) and a merchant waiting for
:math:`z` confirmations. The attacker mines at :math:`q/p` times the honest
rate, so while the honest network finds :math:`z` blocks the attacker's
progress :math:`k` is Poisson with mean :math:`\lambda = zq/p`. An attacker
with :math:`k \le z` blocks still trails by :math:`z - k` and, by the
gambler's ruin, catches up with probability :math:`(q/p)^{z-k}`; one with
more blocks has already won. Subtracting the chance of failure from one:

.. math::

   P(q, z) = 1 - \sum_{k=0}^{z} \frac{\lambda^k e^{-\lambda}}{k!}
   \left(1 - (q/p)^{z-k}\right).

The whitepaper tabulates :math:`P` (for example 0.0009137 at :math:`q = 0.1`,
:math:`z = 5`) and the :math:`z` needed for :math:`P < 0.1\%`. Later work
refined the model (Rosenfeld 2014; Grunspan and Pérez-Marco 2017), but the
exponential decay remains.

*Implementation:* :func:`blockchainkit.consensus.systems.catch_up.attacker_success_probability`
reproduces the whitepaper's table.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008), section 11. `Paper <https://bitcoin.org/bitcoin.pdf>`__.

.. minigallery:: ../../examples/consensus/attacks/plot_02_double_spend.py

2009 -- Difficulty Retargeting
------------------------------

If more miners join, blocks come faster. The whitepaper says difficulty is set
by a moving average targeting an average number of blocks per hour, and
Bitcoin's first release (January 2009) recomputes the target :math:`T` every
2016 blocks, scaled by how long they actually took and clamped to a factor of
four:

.. math::

   T' = T \cdot \frac{\min\!\bigl(\max(t_{\text{actual}}, t_{\text{expected}}/4),\
   4\,t_{\text{expected}}\bigr)}{t_{\text{expected}}}.

A larger target is easier to hit, so blocks that came too slowly raise
:math:`T` and blocks that came too fast lower it. The clamp limits
manipulation and shocks. Retargeting turns proof of work into a clock that
returns to about ten minutes per block whatever the hashrate. It also matters
for selfish mining (2014 entry below). Orphaned blocks slow the chain, so
retargeting lowers the difficulty, and a pool that holds a larger share of
the chain then also earns more blocks per hour.

*Implementation:* :func:`blockchainkit.consensus.systems.difficulty.retarget`
and :func:`blockchainkit.consensus.systems.difficulty.simulate_difficulty` use
Bitcoin's clamp on an integer target, in a simulation with given hashrates;
they do not reproduce the off-by-one in Bitcoin's interval count.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008), section 4; Bitcoin v0.1 source code (2009), ``GetNextWorkRequired``.

.. minigallery:: ../../examples/consensus/pow/plot_03_difficulty_retargeting.py

2012 -- Peercoin: Stake as an Alternative to Work
-------------------------------------------------

King and Nadal's Peercoin explored proof of stake alongside proof of work: the
right to propose blocks could be weighted by coins held rather than by
computation performed. Coins are as scarce as computation, so an attacker
still needs a large share of a limited resource, but using them burns no
electricity. The basic building block is a weighted lottery, in which twice
the stake gives twice the chance of being selected:

.. math::

   \Pr[\text{proposer}=i]=\frac{w_i}{\sum_j w_j}.

A lottery alone is not consensus: a proof-of-stake protocol still needs an
unbiasable source of randomness, voting, and penalties, which the following
entries add.

*Implementation:* :class:`blockchainkit.consensus.systems.pos.StakeSampler`
samples integer weights exactly, from a private seeded generator. It does not
model Peercoin's coin age, voting, slashing or finality; deployed protocols
derive randomness with RANDAO or verifiable random functions and must resist
validators grinding it.

*References:* S. King and S. Nadal, *PPCoin: Peer-to-Peer Crypto-Currency with
Proof-of-Stake* (2012). `Project paper
<https://www.peercoin.net/assets/paper/peercoin-paper.pdf>`__.

.. minigallery:: ../../examples/consensus/pos/plot_01_stake.py

2013 -- GHOST: The Heaviest Observed Subtree
--------------------------------------------

When blocks are frequent, honest miners often build on the same parent at
once, and the longest-chain rule throws their extra blocks away. Sompolinsky and
Zohar showed that this degrades security at high block rates. An attacker's
private chain has no forks, so all its work counts, while honest work split
across sibling blocks only partly lengthens the main chain. An attacker can
therefore win with less than half the hashrate. GHOST (Greedy Heaviest
Observed SubTree) counts the work in sibling blocks too. It descends from
genesis, at each fork choosing

.. math::

   \text{child} = \arg\max_{c} \sum_{b \in \text{subtree}(c)} \text{work}(b).

Sibling blocks still add weight to their common branch. Without forks, GHOST
picks the same tip as the longest-chain rule. Ethereum's proof-of-work chain
adopted GHOST's uncle rewards but kept
heaviest-chain selection; a GHOST variant, LMD-GHOST, became its fork-choice
rule with proof of stake.

*Implementation:* :func:`blockchainkit.consensus.systems.fork_choice.ghost_tip`
and :func:`blockchainkit.consensus.systems.fork_choice.subtree_work` apply
GHOST to a static block tree.

*References:* Y. Sompolinsky and A. Zohar, *Secure High-Rate Transaction
Processing in Bitcoin*, Financial Cryptography 2015, LNCS 8975, 507–527 (2015);
preprint IACR ePrint 2013/881. `DOI
<https://doi.org/10.1007/978-3-662-47854-7_32>`__.

.. minigallery:: ../../examples/consensus/nakamoto/plot_02_ghost.py

2014 -- Nothing at Stake, and Slashing
--------------------------------------

A proof-of-work miner must spend electricity on one fork or another. In early
2014 critics pointed out that a proof-of-stake validator can sign every fork
for free and collect the reward whichever wins, so forks never settle.
Buterin's Slasher answered with penalties: evidence of two signatures at the
same height destroys the validator's deposit. Take reward :math:`R` for
voting on the winning fork, probability :math:`p_A` that fork :math:`A` wins,
and penalty :math:`S`, and assume that a double vote is always caught. Voting
only for :math:`A` pays when :math:`A` wins, and voting for both always pays
but is always punished:

.. math::

   E[\text{vote } A] = p_A R, \qquad E[\text{vote both}] = R - S,

so voting for one fork is the best response once :math:`S > (1 - p_A) R`.
Slashing is now part of every major proof-of-stake protocol. It works only
while the deposit is still locked. Keys whose deposits were already withdrawn
can sign an alternative history at no cost, which is the *long-range
attack*.

*Implementation:* :func:`blockchainkit.consensus.systems.stake_games.fork_voting_payoffs`
is a payoff table, not a protocol; real slashing needs on-chain evidence and
deposits that are still locked.

*References:* V. Buterin, *Slasher: A Punitive Proof-of-Stake Algorithm*,
Ethereum blog (January 2014). `Post
<https://blog.ethereum.org/2014/01/15/slasher-a-punitive-proof-of-stake-algorithm>`__.

.. minigallery:: ../../examples/consensus/pos/plot_02_nothing_at_stake.py

2014 -- Selfish Mining: Majority Is Not Enough
----------------------------------------------

Eyal and Sirer showed that a large pool can earn more than its fair share by
withholding the blocks it finds and releasing them just in time to orphan
honest blocks. The pool sometimes loses its own blocks too, but honest miners
lose more, so the pool's fraction of the final chain rises. They modelled the strategy as a Markov chain on the pool's
private lead and derived its share of the chain, for hashrate share
:math:`\alpha` and fraction :math:`\gamma` of honest miners that build on the
pool's block during a tie:

.. math::

   R(\alpha, \gamma) = \frac{\alpha(1-\alpha)^2\bigl(4\alpha + \gamma(1-2\alpha)\bigr)
   - \alpha^3}{1 - \alpha\bigl(1 + (2-\alpha)\alpha\bigr)}.

This exceeds :math:`\alpha` whenever :math:`\alpha > (1-\gamma)/(3-2\gamma)`: a
third of the hashrate when ties go to honest blocks, and any share when the
pool wins every tie. Honest miners then gain by joining the pool, so Bitcoin's
incentive argument needs more than an honest majority.

*Implementation:* :func:`blockchainkit.consensus.systems.selfish.selfish_mining_revenue`,
:func:`blockchainkit.consensus.systems.selfish.selfish_mining_threshold`, and
the state-machine simulation
:func:`blockchainkit.consensus.systems.selfish.simulate_selfish_mining`, in Eyal
and Sirer's idealized model: propagation is instant apart from the tie share
:math:`\gamma`, and difficulty does not adjust.

*References:* I. Eyal and E. G. Sirer, *Majority Is Not Enough: Bitcoin Mining
Is Vulnerable*, Financial Cryptography 2014, LNCS 8437, 436–454 (2014). `DOI
<https://doi.org/10.1007/978-3-662-45472-5_28>`__.

.. minigallery:: ../../examples/consensus/attacks/plot_03_selfish_mining.py

2017 -- Casper FFG: Finality from Two-Thirds Votes
--------------------------------------------------

Buterin and Griffith's Casper the Friendly Finality Gadget overlays finality on
any block-proposal mechanism. Validators vote for links
:math:`s \to t` from a source checkpoint to a later target. A checkpoint is
*justified* when two thirds of the stake vote for a link to it from a
justified checkpoint, and it is *final* when the link that justifies its
direct successor starts from it. Two slashing conditions forbid, for one
validator, two distinct votes for the same target height and a vote that
surrounds another:

.. math::

   h(t_1) = h(t_2) \ \text{for distinct votes}, \qquad
   h(s_1) < h(s_2) < h(t_2) < h(t_1).

They prove *accountable safety*: two conflicting finalized checkpoints imply
that validators holding at least a third of the stake violated a condition and
can be punished. The argument is PBFT's quorum intersection. Two sets that
each hold two thirds of the stake overlap in at least a third, and the
validators in the overlap cannot have voted for both checkpoints without
breaking one of the rules. Where PBFT assumes the overlap contains an honest
replica, Casper makes it identifiable and punishable. Ethereum's proof of stake combines Casper FFG with LMD-GHOST.

*Implementation:* :class:`blockchainkit.consensus.systems.finality.FinalityGadget`
tracks justification, finality and offenses for a fixed validator set. It has no
deposits, rewards, inactivity leak or fork choice.

*References:* V. Buterin and V. Griffith, *Casper the Friendly Finality Gadget*,
arXiv:1710.09437 (2017). `Preprint <https://arxiv.org/abs/1710.09437>`__.

.. minigallery:: ../../examples/consensus/pos/plot_04_casper_ffg.py

2017 -- Algorand's Cryptographic Sortition
------------------------------------------

Gilad, Hemo, Micali, Vlachos and Zeldovich built Algorand around a private
lottery: each round's committee is drawn so that every unit of stake is a
ticket, and each user checks their own tickets with a verifiable random
function on the round seed. A user with stake :math:`w`, out of total stake
:math:`W` and expected committee size :math:`\tau`, holds :math:`j` seats with

.. math::

   j \sim \text{Binomial}\!\left(w, \frac{\tau}{W}\right), \qquad
   E[j] = \tau\,\frac{w}{W}.

The function needs the user's secret key, so nobody else knows who is on the
committee until its members speak and attach their proofs. They therefore
cannot be attacked in advance, and Algorand replaces the committee after
every step, so attacking a member after it speaks is too late. Independent
binomials with the same probability add, so splitting stake across accounts
leaves the distribution of seats unchanged: there is no Sybil advantage.

*Implementation:* :func:`blockchainkit.consensus.systems.sortition.sortition`.
A hash of the user's secret replaces the verifiable random function, so others
cannot check a claimed draw.

*References:* Y. Gilad, R. Hemo, S. Micali, G. Vlachos, and N. Zeldovich,
*Algorand: Scaling Byzantine Agreements for Cryptocurrencies*, 26th Symposium
on Operating Systems Principles (SOSP), 51–68 (2017). `DOI
<https://doi.org/10.1145/3132747.3132757>`__.

.. minigallery:: ../../examples/consensus/pos/plot_03_sortition.py
