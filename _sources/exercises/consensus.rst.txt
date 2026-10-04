Exercises: consensus
====================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. Byzantine generals: why m traitors need m + 1 rounds
-------------------------------------------------------

From :doc:`/api/gallery/consensus/agreement/plot_01_byzantine_generals`. Run
``oral_messages(7, {a, b}, "attack", rounds=2)`` for every pair of traitors,
then with ``rounds=1``.

.. dropdown:: Solution

   .. doctest::

      >>> from itertools import combinations
      >>> pairs = list(combinations(range(7), 2))
      >>> all(bk.consensus.oral_messages(7, set(p), "attack", rounds=2).agreement for p in pairs)
      True
      >>> [p for p in pairs if not bk.consensus.oral_messages(7, set(p), "attack", rounds=1).agreement]
      [(0, 1), (0, 3), (0, 5)]

   With one round of relaying, a traitorous commander and one traitorous
   lieutenant can split the loyal lieutenants. Each extra round lets the
   lieutenants check what the others were told, removing one traitor's
   influence, so tolerating :math:`m` traitors takes :math:`m + 1` rounds in all.

2. Ben-Or: the expected number of rounds
----------------------------------------

From :doc:`/api/gallery/consensus/agreement/plot_02_ben_or`. The adversary
stalls unless all four coins agree, which happens with probability 2/16 per
round. Derive the expected number of rounds.

.. dropdown:: Solution

   .. doctest::

      >>> from fractions import Fraction
      >>> p = Fraction(2, 16)
      >>> 1 / p
      Fraction(8, 1)

   The number of rounds until the first success is geometric with mean
   :math:`1/p = 8`. With :math:`n` processes the chance that all coins agree
   is :math:`2^{1-n}`, so this protocol's expected time grows exponentially,
   a weakness later randomized protocols fixed with a common coin.

3. Mining: mean versus median
-----------------------------

From :doc:`/api/gallery/consensus/pow/plot_02_hashcash`. Repeat the search
many times and compare the mean and the median number of attempts.

.. dropdown:: Solution

   .. doctest::

      >>> from statistics import mean, median
      >>> attempts = [
      ...     bk.consensus.mine(bk.structures.Block(difficulty=4, timestamp=i)).attempts
      ...     for i in range(400)
      ... ]
      >>> bk.consensus.expected_trials(4)
      16
      >>> 12 < mean(attempts) < 20, median(attempts) < mean(attempts)
      (True, True)

   Attempts are geometric with mean :math:`2^4 = 16`, a distribution with a
   long right tail: its median, about :math:`16 \ln 2 \approx 11`, is below the
   mean. Keep slow searches in the statistics rather than discarding them.

4. Double spending: how many confirmations?
-------------------------------------------

From :doc:`/api/gallery/consensus/attacks/plot_02_double_spend`. Find the
smallest :math:`z` with risk below 0.1% for :math:`q = 0.1`, 0.2 and 0.3.

.. dropdown:: Solution

   .. doctest::

      >>> def confirmations(q, risk=0.001):
      ...     return next(z for z in range(1000) if bk.consensus.attacker_success_probability(q, z) < risk)
      >>> [confirmations(q) for q in (0.1, 0.2, 0.3)]
      [5, 11, 24]

   The whitepaper's table gives the same answers. The attacker's
   disadvantage per block is the ratio :math:`q/p`, and as :math:`q \to 1/2` that
   ratio tends to 1, so the number of blocks needed to make the risk small
   diverges.

5. Difficulty retargeting: Bitcoin's off-by-one
-----------------------------------------------

From :doc:`/api/gallery/consensus/pow/plot_03_difficulty_retargeting`.
Bitcoin's code measures 2015 intervals but targets the time for 2016.
Estimate the effect on the average block time.

.. dropdown:: Solution

   .. doctest::

      >>> round(600 * 2016 / 2015, 1)
      600.3

   The rule sets the difficulty so that 2015 intervals take as long as 2016
   should, stretching each interval by :math:`2016/2015`: blocks come about
   0.3 seconds, or 0.05%, slower than intended.

6. PBFT: why 2f + 1 and not 2f
------------------------------

From :doc:`/api/gallery/consensus/agreement/plot_05_pbft`. Why does a replica
wait for :math:`2f + 1` commits?

.. dropdown:: Solution

   Two quorums of size :math:`Q` among :math:`n = 3f + 1` replicas share at
   least :math:`2Q - n` replicas. Agreement needs that overlap to contain an
   honest replica, which only vouches for one value: :math:`2Q - n \ge f + 1`.

   .. doctest::

      >>> def overlap(quorum, n):
      ...     return 2 * quorum - n
      >>> [(f, overlap(bk.consensus.quorum_size(3 * f + 1), 3 * f + 1)) for f in (1, 2, 3)]
      [(1, 2), (2, 3), (3, 4)]
      >>> [(f, overlap(2 * f, 3 * f + 1)) for f in (1, 2, 3)]
      [(1, 0), (2, 1), (3, 2)]

   With :math:`2f + 1` the overlap is :math:`f + 1` replicas, always one more
   than the number of faulty ones. With :math:`2f` it is only :math:`f - 1`,
   which the faulty replicas can fill entirely: two honest replicas could
   then each see a commit quorum for a different value.

7. Stake: splitting names does not create weight
------------------------------------------------

From :doc:`/api/gallery/consensus/pos/plot_01_stake`. Split Carol's stake
across ten names. Does her expected influence change?

.. dropdown:: Solution

   .. doctest::

      >>> stakes = {"alice": 10, "bob": 30, **{f"carol-{i}": 6 for i in range(10)}}
      >>> carol = sum(w for name, w in stakes.items() if name.startswith("carol-"))
      >>> carol / sum(stakes.values())
      0.6
      >>> picks = bk.consensus.StakeSampler(stakes, seed=1).sample(5000)
      >>> abs(sum(p.startswith("carol-") for p in picks) / 5000 - 0.6) < 0.03
      True

   Selection is proportional to stake, not to names, so splitting changes
   nothing. Choosing a proposer is not agreement: a proposer can sign two
   conflicting blocks, and votes with slashing must resolve that. A public,
   fixed seed lets everyone predict, and possibly attack, future proposers.

8. Casper FFG: conflicting finality implies slashing
----------------------------------------------------

From :doc:`/api/gallery/consensus/pos/plot_04_casper_ffg`. Two conflicting
checkpoints are each finalized by two thirds of the stake. Show that at
least a third of the stake voted for both.

.. dropdown:: Solution

   .. doctest::

      >>> from fractions import Fraction
      >>> supermajority = Fraction(2, 3)
      >>> 2 * supermajority - 1
      Fraction(1, 3)

   Two sets each holding at least two thirds of the stake overlap in at least
   :math:`2/3 + 2/3 - 1 = 1/3`. Every validator in the overlap cast two votes
   that a slashing rule forbids, so a safety failure always comes with
   provable misbehavior by a third of the stake: *accountable safety*.
