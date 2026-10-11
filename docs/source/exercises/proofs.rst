Exercises: proof systems
========================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. Repeating a polynomial identity test
---------------------------------------

From :doc:`/api/gallery/proofs/foundations/plot_01_schwartz_zippel`. Over
the field of 97 elements, how many independent random points are needed
before two distinct polynomials of degree 10 agree on all of them with
probability below one in a million?

.. dropdown:: Solution

   Each point fools the test with probability at most 10/97, independently,
   so :math:`t` points do with probability at most :math:`(10/97)^t`.

   .. doctest::

      >>> next(t for t in range(1, 50) if (10 / 97) ** t < 1e-6)
      7

   Seven evaluations of each side replace expanding both polynomials. In a
   field of :math:`2^{31}` elements one point already gives
   :math:`10 / 2^{31} \approx 5 \cdot 10^{-9}`, which is why proof systems
   use large fields rather than repetition.

2. Who evaluates f in sum-check
-------------------------------

From :doc:`/api/gallery/proofs/foundations/plot_02_sumcheck`. Count the
evaluations of :math:`f` in a sum-check run over the four-variable formula.

.. dropdown:: Solution

   Wrap :math:`f` in a counter.

   .. doctest::

      >>> formula = bk.proofs.CNF(4, ((1, 2), (-2, 3), (3, 4), (-1, -4)))
      >>> calls = []
      >>> def f(x):
      ...     calls.append(x)
      ...     return formula.evaluate(x, 97)
      >>> run = bk.proofs.sumcheck(f, 4, formula.degree, 97)
      >>> run.accepted, formula.degree, len(calls)
      (True, 2, 62)

   The true sum costs :math:`2^4 = 16` evaluations, and round :math:`i`
   costs :math:`(d + 1) 2^{n-i}`, here :math:`3 (8 + 4 + 2 + 1) = 45`: the
   prover's work is :math:`O(d\, 2^n)`. The verifier makes exactly one
   evaluation, the last, at a random point; everything else it does is
   :math:`O(n d)` field arithmetic.

3. The size of a Hadamard proof
-------------------------------

From :doc:`/api/gallery/proofs/pcp/plot_01_pcp_theorem`. For :math:`n = 10`
variables, how long is the Hadamard proof, and how many bits does the
verifier read for an error below one in a million?

.. dropdown:: Solution

   .. doctest::

      >>> 2**10 + 2**100
      1267650600228229401496703206400
      >>> k = next(k for k in range(1, 60) if 0.5**k < 1e-6)
      >>> k, 14 * k
      (20, 280)

   The proof has about :math:`10^{30}` bits, yet 280 of them suffice. The
   full PCP theorem shrinks the proof to polynomial length while keeping
   the query count constant, which is what Kilian's argument needs.

4. Opening a KZG commitment at two points
-----------------------------------------

From :doc:`/api/gallery/proofs/snarks/plot_01_kzg_commitments`. Prove
:math:`f(z_1) = y_1` and :math:`f(z_2) = y_2` with one witness.

.. dropdown:: Solution

   Let :math:`r` be the line through both points and
   :math:`Z = (X - z_1)(X - z_2)`. Then :math:`f - r` vanishes at both
   points exactly when the claims hold, so :math:`q = (f - r)/Z` is a
   polynomial, and the verifier checks
   :math:`e(C - [r(\tau)]G, G) = e([q(\tau)]G, [Z(\tau)]G)`.

   .. doctest::

      >>> srs = bk.proofs.trusted_setup(8, secret=987654321)
      >>> E = srs.curve
      >>> f = [3, 1, 4, 1, 5, 9, 2, 6]
      >>> points = [(z, bk.proofs.poly_eval(f, z)) for z in (10, 20)]
      >>> line = bk.proofs.interpolate(points)
      >>> zeros = bk.proofs.vanishing_polynomial([10, 20])
      >>> quotient, remainder = bk.proofs.poly_divmod(bk.proofs.poly_sub(f, line), zeros)
      >>> remainder
      ()
      >>> C, W = bk.proofs.kzg_commit(f, srs), bk.proofs.kzg_commit(quotient, srs)
      >>> left = bk.crypto.add(C, bk.crypto.multiply(-1, bk.proofs.kzg_commit(line, srs), E), E)
      >>> bk.proofs.pairing(left, E.generator) == bk.proofs.pairing(W, bk.proofs.kzg_commit(zeros, srs))
      True

   The witness stays one point for any number of evaluation points; the
   verifier's work grows with them, through :math:`r` and :math:`Z`.

5. Squaring in a circuit
------------------------

From :doc:`/api/gallery/proofs/snarks/plot_02_qap_pinocchio`. Compare the
constraints for :math:`x^{16}` by repeated squaring and by repeated
multiplication.

.. dropdown:: Solution

   .. doctest::

      >>> def power(squaring):
      ...     circuit = bk.proofs.Circuit()
      ...     out, x = circuit.public(2**16), circuit.private(2)
      ...     y = x
      ...     for _ in range(4 if squaring else 15):
      ...         y = circuit.mul(y, y) if squaring else circuit.mul(y, x)
      ...     circuit.assert_equal(y, out)
      ...     return circuit.r1cs()
      >>> [(r.num_constraints, bk.proofs.domain_size(r)) for r in (power(True), power(False))]
      [(7, 8), (18, 32)]

   Four squarings against fifteen multiplications, plus one equality and
   two public-input rows each. The QAP domain rounds up to a power of two,
   so the prover's FFTs are four times larger for the naive circuit:
   writing circuits well is most of the cost of a SNARK.

6. The range check that stops inflation
---------------------------------------

From :doc:`/api/gallery/proofs/privacy/plot_01_zerocash`. Bob holds a note
of 70 and tries to withdraw 1,070 publicly while keeping a note of
:math:`-1000`. Which constraint stops him?

.. dropdown:: Solution

   Modulo :math:`p` the values balance, so the conservation equation
   alone cannot catch it.

   .. doctest::

      >>> p = bk.proofs.FIELD_PRIME
      >>> (p - 1000 + 1070 - 70) % p
      0
      >>> bob = 2222
      >>> note = bk.proofs.Note(bk.proofs.owner_key(bob), 70, rho=2, randomness=88)
      >>> negative = bk.proofs.Note(bk.proofs.owner_key(bob), p - 1000, rho=3, randomness=1)
      >>> circuit = bk.proofs.spend_circuit(1, bob, note, [0], 0, negative, 1070)
      >>> rows = circuit.r1cs().row_values(circuit.witness())
      >>> failing = [j for j, (a, b, c) in enumerate(rows) if a * b % p != c]
      >>> len(failing), len(rows) - failing[0]
      (1, 6)

   Exactly one row fails: the last constraint before the five public-input
   rows, which says the 16 bits sum to the new value. Without it the spend
   would verify, the pool would pay out 1,070, and 1,000 coins would appear
   from nothing, invisibly. Zcash's 2018 counterfeiting bug was a flaw of
   this kind, in its setup rather than its circuit.

7. A range that is not a power of two
-------------------------------------

From :doc:`/api/gallery/proofs/transparent/plot_01_bulletproofs`. Prove that
a committed value lies in :math:`[0, 1000)`.

.. dropdown:: Solution

   Prove that both :math:`v` and :math:`v + 2^{16} - 1000` lie in
   :math:`[0, 2^{16})`. The second commitment is the first times
   :math:`g^{2^{16} - 1000}`, so the verifier derives it itself.

   .. doctest::

      >>> v, gamma, shift = 999, 42, 2**16 - 1000
      >>> low = bk.proofs.range_proof(v, gamma, 16)
      >>> high = bk.proofs.range_proof(v + shift, gamma, 16, seed=1)
      >>> G, g = bk.crypto.TEACHING_GROUP, bk.proofs.range_commitment(1, 0)
      >>> high.commitment == low.commitment * pow(g, shift, G.p) % G.p
      True
      >>> bk.proofs.verify_range_proof(low, 16) and bk.proofs.verify_range_proof(high, 16)
      True
      >>> bk.proofs.range_proof(1000 + shift, gamma, 16)
      Traceback (most recent call last):
      ...
      ValueError: value must be below 2**16

   For :math:`v \ge 1000` the shifted value reaches :math:`2^{16}`, so no
   second proof exists. Two proofs of :math:`2 \log_2 16 + 9 = 17` elements
   each prove any range.
