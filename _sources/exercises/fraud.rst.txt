Exercises: fraud
================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. A Ponzi scheme with a skimming operator
------------------------------------------

From :doc:`/api/gallery/fraud/schemes/plot_01_ponzi_scheme`. How fast must
deposits grow for a scheme promising 50% in 45 days if the operator keeps
20% of every deposit?

.. dropdown:: Solution

   The condition :math:`(1 - s)(1 + g) \ge 1 + r` gives
   :math:`g = 1.5 / 0.8 - 1 = 87.5\%` per period.

   .. doctest::

      >>> bk.fraud.breakeven_growth(0.5, term=1, skim=0.2)
      0.875
      >>> just_enough = [100 * 1.875**t for t in range(12)]
      >>> bk.fraud.simulate_ponzi(just_enough, promised_return=0.5, skim=0.2).survived
      True
      >>> too_slow = [100 * 1.85**t for t in range(12)]
      >>> bk.fraud.simulate_ponzi(too_slow, promised_return=0.5, skim=0.2).survived
      False

   Every point the operator skims must be made up by faster growth, so a
   greedier operator brings the collapse closer.

2. Multiples of seven
---------------------

From :doc:`/api/gallery/fraud/figures/plot_01_benford_law`. Do the
multiples of 7 up to 7,000 follow Benford's law?

.. dropdown:: Solution

   No. An arithmetic sequence fills each order of magnitude evenly, so the
   numbers from 1,000 to 7,000, most of the sequence, start with 1 to 6
   equally often, and 7, 8 and 9 appear only below 1,000.

   .. doctest::

      >>> test = bk.fraud.benford_test(7 * k for k in range(1, 1001))
      >>> test.counts
      (158, 159, 159, 159, 158, 157, 19, 15, 16)
      >>> test.conformity
      'nonconformity'
      >>> bk.fraud.benford_test(2**k for k in range(1, 1001)).conformity
      'close'

   The powers of 2 spread their logarithms evenly, :math:`k \log_{10} 2`
   modulo 1 being equidistributed, which is exactly Benford's condition.

3. A fake negative balance
--------------------------

From :doc:`/api/gallery/fraud/solvency/plot_01_maxwell_proof_of_reserves`.
The exchange adds an account with a balance of minus 5,000. Which customers
can notice?

.. dropdown:: Solution

   Every customer whose path to the root passes a node with a negative sum.
   Here the fake sits next to alice, and the node above both is negative,
   so bob and carol see it too.

   .. doctest::

      >>> entries = [("alice", 3_000), ("fake", -5_000), ("bob", 4_000), ("carol", 2_000)]
      >>> tree = bk.fraud.MerkleSumTree(entries)
      >>> tree.total
      4000
      >>> [step.amount for step in tree.proof(2).steps]
      [2000, -2000]
      >>> [bk.fraud.verify_sum_proof(name, balance, tree.proof(i), tree.root, tree.total)
      ...  for i, (name, balance) in enumerate(entries) if name != "fake"]
      [False, False, False]

   Without the check on negative sums, every proof would verify, and the
   exchange would have hidden 5,000 of its 9,000 in liabilities. To escape
   notice, a negative leaf must be surrounded by other fake accounts whose
   sums offset it, so it cannot lower the total after all.

4. Two exchanges, one address
-----------------------------

From :doc:`/api/gallery/fraud/solvency/plot_03_provisions_proof_of_solvency`.
Why can't customers detect two exchanges claiming the same address?

.. dropdown:: Solution

   Each proof hides which addresses its exchange owns, so two exchanges
   that share one address, or one that borrows the other's for the day of
   its proof, both produce valid proofs.

   .. doctest::

      >>> public = [1_000, 50, 20]
      >>> first = bk.fraud.SolvencyProver(public, {0}, [900], seed=1)
      >>> second = bk.fraud.SolvencyProver(public, {0}, [800], seed=2)
      >>> bk.fraud.verify_solvency(public, first.prove())
      True
      >>> bk.fraud.verify_solvency(public, second.prove())
      True

   Together they owe 1,700 against 1,000. Provisions' third protocol rules
   this out: each exchange publishes, for every address it owns, a value
   derived from the address's key that is the same whichever exchange
   computes it, so a shared address shows up as a repeated value in two
   proofs, without revealing which address it is.

5. Window dressing
------------------

From :doc:`/api/gallery/fraud/solvency/plot_04_ftx_commingled_funds`. The
affiliate repays its loan the day before a proof of reserves, then borrows
again. Which checks pass?

.. dropdown:: Solution

   All of them, on the day of the proof.

   .. doctest::

      >>> world = bk.contracts.World()
      >>> world.fund("alice", 1_000)
      >>> exchange = world.deploy("operator", bk.fraud.Custodian, "affiliate", 1_000)
      >>> world.transact("alice", exchange, "deposit", value=1_000).success
      True
      >>> world.transact("operator", exchange, "lend_to_affiliate", 900).success
      True
      >>> world.transact("affiliate", exchange, "repay", value=900).success  # The day before.
      True
      >>> tree = bk.fraud.liability_tree(world.view(exchange, "balances"))
      >>> bk.fraud.reserve_ratio(world.view(exchange, "reserves"), tree.total)
      1.0
      >>> world.transact("operator", exchange, "lend_to_affiliate", 900).success  # The day after.
      True
      >>> bk.fraud.reserve_ratio(world.view(exchange, "reserves"), tree.total)
      0.1

   A proof at one instant says nothing about the next. Frequent or
   unannounced proofs make window dressing costlier, and proving that the
   reserves were not borrowed needs the lender's books too, which no proof
   of reserves can provide.

6. Six characters at each end
-----------------------------

From :doc:`/api/gallery/fraud/phishing/plot_02_address_poisoning`. How long
does a poisoner computing ten million addresses a second need to match
twelve hex digits?

.. dropdown:: Solution

   On average :math:`16^{12} \approx 2.8 \cdot 10^{14}` tries, about 326
   days, and half of that for an even chance.

   .. doctest::

      >>> round(16**12 / 10**7 / 86_400)
      326

   Graphics cards compute about a billion candidates a second, which
   brings this down to about three days: checking more characters raises
   the cost by 16 for each one, but only a full comparison makes the
   attack impossible.
