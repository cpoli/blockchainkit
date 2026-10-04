Exercises: execution
====================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. Reverse Polish notation by hand
----------------------------------

From :doc:`/api/gallery/vm/foundations/plot_01_reverse_polish`. Write
``2 * (3 + 4)`` in prefix (Polish) notation and in RPN.

.. dropdown:: Solution

   Prefix: ``* 2 + 3 4``. Postfix (RPN): ``2 3 4 + *``.

   .. doctest::

      >>> bk.vm.to_rpn("2 * (3 + 4)")
      ('2', '3', '4', '+', '*')
      >>> bk.vm.execute(bk.vm.compile_expression("2 * (3 + 4)")).stack
      (14,)

   In RPN every operator follows its operands, so scanning left to right
   with one stack always has the operands ready. In prefix the operator comes
   first and must wait, so a prefix evaluator naturally scans right to left,
   where the same reasoning applies.

2. Stack depth of a balanced sum
--------------------------------

From :doc:`/api/gallery/vm/foundations/plot_03_hardware_stack`. For a balanced
tree of additions over :math:`2^k` numbers, what is the peak stack height?

.. dropdown:: Solution

   .. doctest::

      >>> def balanced(lo, hi):
      ...     if hi - lo == 1:
      ...         return str(lo)
      ...     mid = (lo + hi) // 2
      ...     return f"({balanced(lo, mid)} + {balanced(mid, hi)})"
      >>> [bk.vm.verify_bytecode(bk.vm.compile_expression(balanced(0, 2**k))).max_depth
      ...  for k in range(1, 6)]
      [2, 3, 4, 5, 6]

   The peak is :math:`k + 1`: evaluating the right subtree needs one more
   slot than evaluating a subtree alone, because the left subtree's result
   waits underneath. This is the Ershov (or Strahler) number of the tree.

3. Forth: defining NIP and TUCK
-------------------------------

From :doc:`/api/gallery/vm/foundations/plot_06_forth`. Define
``NIP ( a b -- b )`` and ``TUCK ( a b -- b a b )`` from the basic words.

.. dropdown:: Solution

   .. doctest::

      >>> nip = [("SWAP", None), ("DROP", None)]
      >>> tuck = [("SWAP", None), ("OVER", None)]
      >>> bk.vm.execute(nip, arguments=(1, 2)).stack, bk.vm.execute(tuck, arguments=(1, 2)).stack
      ((2,), (2, 1, 2))

   ``SWAP`` puts ``a`` on top, where ``DROP`` removes it. For ``TUCK``,
   ``SWAP`` gives ``b a`` and ``OVER`` copies ``b`` to the top.

4. The busy beaver: running is not knowing
------------------------------------------

From :doc:`/api/gallery/vm/foundations/plot_04_busy_beaver`. Run the 3-state
champion's 21 steps from its rule table. Why does a budget of 22 steps let
you run it but not know that no 3-state machine runs longer?

.. dropdown:: Solution

   .. doctest::

      >>> champion = {
      ...     ("A", 0): (1, 1, "B"), ("A", 1): (0, -1, "H"),
      ...     ("B", 0): (1, -1, "B"), ("B", 1): (0, 1, "C"),
      ...     ("C", 0): (1, -1, "C"), ("C", 1): (1, -1, "A"),
      ... }
      >>> bk.vm.run_turing_machine(champion, max_steps=22).steps
      21

   To know :math:`S(3) = 21` you must also show that every 3-state machine
   still running after 21 steps never halts. A budget cannot show that;
   Lin and Radó had to prove each remaining machine loops, by hand and by
   pattern-matching programs.

5. Atomic transactions: checks before or after effects
------------------------------------------------------

From :doc:`/api/gallery/vm/replication/plot_02_atomic_transactions`. Move the
balance check before the debit. Does the committed outcome change?

.. dropdown:: Solution

   .. doctest::

      >>> debit_first = bk.vm.assemble('''
      ...     LOAD 0
      ...     OVER
      ...     OVER
      ...     SWAP
      ...     SUB
      ...     STORE 0
      ...     OVER
      ...     LT
      ...     JZ credit
      ...     REVERT
      ... credit:
      ...     LOAD 1
      ...     ADD
      ...     STORE 1
      ... ''')
      >>> check_first = bk.vm.assemble('''
      ...     LOAD 0
      ...     OVER
      ...     LT
      ...     JZ ok
      ...     REVERT
      ... ok:
      ...     LOAD 0
      ...     OVER
      ...     SUB
      ...     STORE 0
      ...     LOAD 1
      ...     ADD
      ...     STORE 1
      ... ''')
      >>> def outcome(program, amount):
      ...     try:
      ...         return dict(bk.vm.execute(program, arguments=(amount,), storage={0: 100, 1: 20}).storage)
      ...     except bk.vm.VMError:
      ...         return "reverted"
      >>> all(outcome(debit_first, a) == outcome(check_first, a) for a in (0, 30, 100, 101, 150))
      True

   Because a failed call commits nothing, the order of a check and a write
   *within one call* does not change the result. It matters as soon as the
   contract calls out to another contract in between, which can observe or
   re-enter the half-updated state: see the DAO example.

6. Integer overflow: which check detects it?
--------------------------------------------

From :doc:`/api/gallery/vm/ethereum/plot_04_integer_overflow`. Why does
``amount / count == value`` detect every overflow of ``count * value``?
Could ``amount >= value`` replace it?

.. dropdown:: Solution

   Without overflow, ``amount / count`` is exactly ``value``. With overflow,
   ``amount = count * value - k * 2**256`` for some :math:`k \ge 1`, which is
   smaller than ``count * value``, so the division falls short of ``value``.
   The weaker check misses overflows:

   .. doctest::

      >>> word = 2**256
      >>> value = 2**255 + 1
      >>> amount = 3 * value % word
      >>> amount >= value, amount // 3 == value
      (True, False)
      >>> try:
      ...     bk.vm.execute(bk.vm.batch_transfer(1, [2, 3, 4], checked=True),
      ...                   arguments=(value,), storage={1: amount})
      ... except bk.vm.VMError as error:
      ...     print(error)
      reverted

   Here three recipients receive more than :math:`2^{255}` each while the
   sender pays only ``amount``, yet ``amount >= value`` holds.

7. Gas repricing: a fair price for storage reads
------------------------------------------------

From :doc:`/api/gallery/vm/ethereum/plot_02_gas_repricing`. Choose a ``LOAD``
price that makes both programs do the same real work per unit of gas.

.. dropdown:: Solution

   Per loop iteration, the arithmetic program costs ``PUSH + ADD + JMP`` =
   3 + 3 + 8 = 14 gas for 3 units of work. The storage-read program costs
   ``LOAD + DROP + JMP`` = :math:`L` + 2 + 8 gas for 100 + 1 + 1 = 102 units.
   Equal work per gas means :math:`102/(L + 10) = 3/14`, so :math:`L = 466`.

   .. doctest::

      >>> from fractions import Fraction
      >>> L = Fraction(102 * 14, 3) - 10
      >>> L
      Fraction(466, 1)

   Real costs differ between machines and change as clients add caches, so
   no schedule is exact. Ethereum instead raised prices enough to remove the
   attack, and EIP-2929 (2021) later charged a first, "cold" access to an
   account or storage slot much more than repeated "warm" ones.

8. Branching: storing one of two values
---------------------------------------

From :doc:`/api/gallery/vm/ethereum/plot_01_gas`. Store one value when two
numbers are equal and another otherwise. Check both branches, stack
underflow, and 256-bit wraparound.

.. dropdown:: Solution

   .. doctest::

      >>> def comparison(left, right):
      ...     return bk.vm.assemble(f'''
      ...         PUSH {left}
      ...         PUSH {right}
      ...         EQ
      ...         JZ different
      ...         PUSH 10
      ...         STORE 0
      ...         STOP
      ...     different:
      ...         PUSH 20
      ...         STORE 0
      ...     ''')
      >>> bk.vm.execute(comparison(3, 3)).storage[0], bk.vm.execute(comparison(3, 4)).storage[0]
      (10, 20)
      >>> bk.vm.execute([("PUSH", 0), ("PUSH", 1), ("SUB", None)]).stack == (2**256 - 1,)
      True
      >>> try:
      ...     bk.vm.execute([("ADD", None)])
      ... except bk.vm.VMError as error:
      ...     print(error)
      stack underflow

   The top of the stack is the rightmost item. Storage written during a run
   is working state, committed only if the whole program succeeds.
