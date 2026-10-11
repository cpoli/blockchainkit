Exercises: economics
====================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. A focal point for twenty
---------------------------

From :doc:`/api/gallery/economics/coordination/plot_01_schelling_focal_points`.
With 20 players and 10 options, what salience gives an even chance that
everyone coincides?

.. dropdown:: Solution

   The chance grows with the salience, so a bisection finds it.

   .. doctest::

      >>> low, high = 0.0, 1.0
      >>> while high - low > 1e-6:
      ...     middle = (low + high) / 2
      ...     if bk.economics.coordination_probability(20, 10, middle) < 0.5:
      ...         low = middle
      ...     else:
      ...         high = middle
      >>> round(high, 3)
      0.962

   Each player must pick the focal option with probability
   :math:`0.5^{1/20} \approx 0.966`, so it must be almost certain for each of
   them. Twenty independent choices multiply twenty chances of straying;
   for a pair, a salience of 0.7 already gives about 0.5. Large groups
   coordinate only on overwhelmingly obvious answers, which is why oracle
   designs make the truth the obvious one.

2. A posted price for a single bidder
-------------------------------------

From :doc:`/api/gallery/economics/auctions/plot_02_myerson_optimal_auction`.
With one bidder whose value is uniform on [0, 1], the seller posts a price
:math:`p`. Show that its revenue is :math:`p(1 - p)` and that the best
price is Myerson's reserve.

.. dropdown:: Solution

   The bidder buys if its value exceeds :math:`p`, with probability
   :math:`1 - p`, and then pays :math:`p`. The derivative :math:`1 - 2p`
   vanishes at :math:`p = 1/2`, where the virtual value :math:`2v - 1` is
   zero.

   .. doctest::

      >>> all(abs(bk.economics.expected_revenue(1, reserve=p) - p * (1 - p)) < 1e-12
      ...     for p in (0.1, 0.3, 0.5, 0.9))
      True
      >>> max(range(101), key=lambda c: bk.economics.expected_revenue(1, reserve=c / 100))
      50
      >>> bk.economics.optimal_reserve()
      0.5

3. The halving's rounding
-------------------------

From :doc:`/api/gallery/economics/rewards/plot_02_halving_schedule`. If the
subsidy were divided exactly, how many coins would eventually exist, and
which halving first loses a fraction of a satoshi?

.. dropdown:: Solution

   Exactly halved, the eras sum to :math:`2 \times 210\,000 \times 50 =
   21` million coins. The initial subsidy is
   :math:`5 \cdot 10^9 = 2^9 \cdot 5^{10}` satoshis, so the first nine
   halvings are exact and the tenth is not.

   .. doctest::

      >>> initial = 5_000_000_000
      >>> next(e for e in range(64) if (initial >> e) << e != initial)
      10
      >>> initial >> 9, initial / 2**10
      (9765625, 4882812.5)
      >>> 21_000_000 * 10**8 - bk.economics.issued_supply(64 * 210_000)
      2310000

4. Doubling the base fee
------------------------

From :doc:`/api/gallery/economics/fees/plot_01_eip1559_base_fee`. A
producer fills blocks with its own transactions to raise the base fee. How
many full blocks double it, and who receives what the producer pays?

.. dropdown:: Solution

   .. doctest::

      >>> fee, blocks = 10**9, 0
      >>> while fee < 2 * 10**9:
      ...     fee = bk.economics.next_base_fee(fee, 30_000_000, 15_000_000)
      ...     blocks += 1
      >>> blocks, fee
      (6, 2027286528)

   Each full block raises the fee by 12.5%, and :math:`1.125^6 \approx
   2.03`. The producer pays the base fee on all the gas it uses, and that
   is burned, so nobody receives it; the producer gets only its own tips
   back. Stuffing blocks therefore costs real money, unlike under a
   first-price auction, where the producer would pay its fees to itself.

5. A price gap in a single step
-------------------------------

From :doc:`/api/gallery/economics/defi/plot_01_dai_liquidation`. The
aggressive vault holds 10 ether against 2,600 Dai. If the price jumps
straight from 400 to a price below its liquidation threshold, below which
price does liquidating it lose the keeper money?

.. dropdown:: Solution

   The keeper burns 2,600 Dai and receives at most the vault's 10 ether, so
   it loses money below 260 Dai per ether, a fall of 35% in one step.

   .. doctest::

      >>> world = bk.contracts.World()
      >>> feed = world.deploy("maker", bk.economics.PriceFeed, 400)
      >>> engine = world.deploy("maker", bk.economics.VaultEngine, feed)
      >>> world.fund("alice", 10)
      >>> world.transact("alice", engine, "lock", value=10).success
      True
      >>> world.transact("alice", engine, "draw", 2_600).success
      True
      >>> _ = world.transact("maker", feed, "set_price", 250)
      >>> world.transact("alice", world.view(engine, "dai"), "transfer", "keeper", 2_600).success
      True
      >>> seized = world.transact("keeper", engine, "liquidate", "alice").result
      >>> seized, seized * 250 - 2_600
      (10, -100)

   The contract still lets the keeper liquidate, but no rational keeper
   would, and the 2,600 Dai would remain backed by 2,500 Dai of ether. This
   happened on 12 March 2020, when ether fell by about 40% in a day and
   congestion delayed liquidations. Maker later redesigned its liquidation
   auctions, and sets higher ratios for more volatile collateral.

6. Splitting a trade against a sandwich
---------------------------------------

From :doc:`/api/gallery/economics/mev/plot_02_sandwich_attacks`. The victim
splits its 100,000 swap into ten swaps of 10,000, with the same 2%
tolerance. Assuming each one is sandwiched against the same pool, does the
attacker earn more or less?

.. dropdown:: Solution

   .. doctest::

      >>> whole = bk.economics.sandwich_attack(10_000_000, 10_000_000, 100_000, slippage_bps=200)
      >>> part = bk.economics.sandwich_attack(10_000_000, 10_000_000, 10_000, slippage_bps=200)
      >>> whole.profit, part.profit, part.front_run
      (1402, 0, 0)

   A 10,000 swap moves the price by about 0.2%, less than the 0.6% the
   attacker pays in fees for its two swaps, so no front-run of any size
   profits and the attacker abstains. Splitting a trade into pieces small
   enough to move the price by less than twice the pool's fee defeats the
   sandwich, at the cost of more transactions; private relays that hide
   pending trades are the other defense.
