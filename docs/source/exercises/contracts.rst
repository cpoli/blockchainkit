Exercises: contracts
====================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. The weakest precondition of a withdrawal
-------------------------------------------

From :doc:`/api/gallery/contracts/verification/plot_01_floyd_hoare`. Compute
the weakest precondition of the withdrawal for ``balance >= 0``. What does the
``require`` contribute, and what changes without it?

.. dropdown:: Solution

   .. doctest::

      >>> withdraw = '''
      ... require(amount <= balance)
      ... balance = balance - amount
      ... received = received + amount
      ... '''
      >>> wp = bk.contracts.weakest_precondition(withdraw, "balance >= 0")
      >>> bk.contracts.to_source(wp)
      'not amount <= balance or balance - amount >= 0'
      >>> unguarded = withdraw.replace("require(amount <= balance)", "")
      >>> bk.contracts.to_source(bk.contracts.weakest_precondition(unguarded, "balance >= 0"))
      'balance - amount >= 0'

   Pushing ``balance >= 0`` back through the assignment gives
   ``balance - amount >= 0``. The ``require`` adds ``not amount <= balance
   or ...``: a call that reverts proves nothing, so the condition only has to
   hold when the check passes, and then it always does. The weakest
   precondition is therefore true for every input. Without the ``require`` it
   is ``balance - amount >= 0`` itself, an obligation every caller must meet.

2. Oyente with three recipients
-------------------------------

From :doc:`/api/gallery/contracts/verification/plot_04_oyente`. With three
recipients the overflowing value is not :math:`2^{255}`. Find one, and let
the solver confirm it.

.. dropdown:: Solution

   We need ``3 * value`` to wrap around to a small number: take
   :math:`\lceil 2^{256}/3 \rceil`, whose triple is :math:`2^{256} + 2
   \equiv 2`.

   .. doctest::

      >>> value = (2**256 + 2) // 3
      >>> 3 * value % 2**256
      2
      >>> program = bk.vm.batch_transfer(1, [2, 3, 4])
      >>> result = bk.contracts.symbolic_bytecode(program, arguments=("value",))
      >>> [stop] = [path for path in result.paths if path.outcome == "stop"]
      >>> bug = bk.contracts.expression("slot2 > s1 + s2", **stop.state)
      >>> witness = bk.contracts.solve((*stop.conditions, bug), modulus=2**256,
      ...                              candidates={"value": [1, value], "s1": [0, 2], "s2": [0]})
      >>> witness["value"] == value, witness["s1"]
      (True, 2)

   A sender holding 2 tokens pays 2 and gives each of three recipients about
   :math:`3.9 \times 10^{76}`. The boundary values miss it because it is
   neither a constant of the program nor half the word size; an SMT solver
   such as Z3 finds it by reasoning about the multiplication instead.

3. Approving zero first
-----------------------

From :doc:`/api/gallery/contracts/tokens/plot_01_erc20_approve_race`. Alice
approves 0, then 50, instead of overwriting 100 with 50. Can Bob still take
150?

.. dropdown:: Solution

   .. doctest::

      >>> world = bk.contracts.World()
      >>> token = world.deploy("alice", bk.contracts.ERC20, 1_000)
      >>> _ = world.transact("alice", token, "approve", "bob", 100)
      >>> _ = world.transact("bob", token, "transfer_from", "alice", "bob", 100)  # Front-run.
      >>> _ = world.transact("alice", token, "approve", "bob", 0)
      >>> _ = world.transact("alice", token, "approve", "bob", 50)
      >>> _ = world.transact("bob", token, "transfer_from", "alice", "bob", 50)
      >>> world.view(token, "balance_of", "bob")
      150

   Yes. Approving zero first only helps if Alice *looks* between her two
   transactions: after the ``approve(0)`` is mined she can see that the 100
   was already spent and decide not to grant 50 more. A
   ``decrease_allowance`` makes that check in the contract, in the same
   transaction.

4. GovernMental under today's gas limit
---------------------------------------

From :doc:`/api/gallery/contracts/payments/plot_02_governmental_gas`. With a
30 million gas limit, how many creditors freeze the payout?

.. dropdown:: Solution

   The payout's gas is linear in the number of creditors: measure two small
   games for the slope and intercept, then solve for the limit.

   .. doctest::

      >>> def payout_gas(creditors):
      ...     world = bk.contracts.World()
      ...     game = world.deploy("operator", bk.contracts.GovernMental)
      ...     for index in range(creditors):
      ...         world.fund(f"p{index}", 1)
      ...         _ = world.transact(f"p{index}", game, "invest", value=1)
      ...     world.advance(seconds=43_200)
      ...     return world.transact("anyone", game, "payout").gas_used
      >>> slope = (payout_gas(20) - payout_gas(10)) // 10
      >>> intercept = payout_gas(10) - 10 * slope
      >>> slope, intercept
      (5000, 31500)
      >>> (30_000_000 - intercept) // slope + 1
      5994

   Each creditor costs one storage write (5,000 gas in this model) and the
   rest of the payout about 31,500, so 5,994 creditors are enough. A bigger
   block only moves the threshold; the loop is still unbounded.

5. Excluding players who do not reveal
--------------------------------------

From :doc:`/api/gallery/contracts/payments/plot_03_commit_reveal`. If a
player who does not reveal is excluded from the draw and loses the stake,
what is Dave's best strategy as the last revealer?

.. dropdown:: Solution

   Withholding now guarantees that Dave loses, while revealing wins with
   probability 1/4, so he always reveals.

   .. doctest::

      >>> import random
      >>> rng = random.Random(1)
      >>> def dave_wins(strategic):
      ...     others = [rng.randrange(2**64) for _ in range(3)]
      ...     mine = rng.randrange(2**64)
      ...     revealed = others[0] ^ others[1] ^ others[2]
      ...     if strategic and (revealed ^ mine) % 4 != 3:
      ...         return False  # Withheld: excluded from the draw.
      ...     return (revealed ^ mine) % 4 == 3
      >>> games = 20_000
      >>> round(sum(dave_wins(True) for _ in range(games)) / games, 2)
      0.25

   Withholding can no longer win Dave the pot. It can still change the
   winner among the others, so a last revealer colluding with another player
   keeps an advantage; that is why penalties are set above what such a
   deviation could gain.

6. A storage collision on the admin slot
----------------------------------------

From :doc:`/api/gallery/contracts/upgrades/plot_01_proxy_storage_collision`.
Behind the naive proxy, an implementation's second field shares slot 1 with
the proxy's ``admin``. What can Mallory do with an open ``store``?

.. dropdown:: Solution

   .. doctest::

      >>> class Open(bk.contracts.Contract):
      ...     layout = ("unused", "value")
      ...     def store(self, value):
      ...         self.write("value", value)
      >>> class Drain(bk.contracts.Contract):
      ...     layout = ()
      ...     def take(self, to):
      ...         self.call(to, None, value=self.ether_balance())
      >>> world = bk.contracts.World()
      >>> proxy = world.deploy("dev", bk.contracts.NaiveProxy, world.deploy("dev", Open))
      >>> world.fund(proxy, 1_000)
      >>> world.transact("mallory", proxy, "store", "mallory").success
      True
      >>> world.read(proxy, "admin")
      'mallory'
      >>> world.transact("mallory", proxy, "upgrade_to", world.deploy("mallory", Drain)).success
      True
      >>> _ = world.transact("mallory", proxy, "take", "mallory")
      >>> world.balance("mallory")
      1000

   Writing ``value`` writes the proxy's ``admin``, so Mallory makes herself
   admin, upgrades to code of her choosing, and takes everything the proxy
   holds. A lost implementation pointer only bricks the contract; a lost
   admin hands it over.
