Breakthroughs in Proof Systems
==============================

.. include:: /_generated/nav/proofs.rst

.. epigraph::

   "Usually, a proof of a theorem contains more knowledge than the mere fact
   that the theorem is true."
   -- Shafi Goldwasser, Silvio Micali and Charles Rackoff, *The Knowledge
   Complexity of Interactive Proof-Systems*, 1985

A blockchain is a shared record of transactions that thousands of computers
(*nodes*) keep in step. It asks every node to re-run every transaction.
*Proof systems* offer another bargain:

- One party, the *prover*, does the work and writes a short *proof* that the
  result is right.
- Everyone else, the *verifiers*, check the proof instead. Checking is quick.
- In a *zero-knowledge* proof, checking also reveals nothing about the secrets
  behind the result, only that it is right.

:doc:`crypto_breakthroughs` covers the beginning: zero-knowledge
identification, and the Fiat-Shamir heuristic, which replaces the verifier's
random questions by a hash of the conversation so far, so that the prover can
write the whole proof alone. This chronology follows the argument from there
in five steps:

1. **Random checks.** To test whether two polynomials are equal, evaluate
   both at one random point. Repeating the trick lets a verifier check a sum
   over exponentially many points (Schwartz-Zippel, sum-check, IP = PSPACE).
2. **Spot checks of a written proof.** A proof can be written so that reading
   a few random bits of it is enough (the PCP theorem). Committing to it with
   a Merkle tree makes it short enough to send (Kilian, Micali).
3. **Checks at a secret point.** Pairings let a verifier check a polynomial
   identity at a point nobody knows. That gives proofs of constant size (KZG,
   QAPs, Groth16, PLONK). The price is a *trusted setup*: someone must create
   the secret point and then destroy it (the parameter ceremonies). These
   proofs made private payments practical (Zerocash).
4. **Hashes only.** Hash functions alone can replace the setup, at the cost of
   larger proofs (FRI, STARKs).
5. **Discrete-log groups.** These can replace the setup too. They give proofs
   of logarithmic size and, eventually, proofs that check other proofs
   (Bulletproofs, Halo).

The page uses a few conventions throughout:

- A *field* :math:`\mathbb{F}` here means arithmetic modulo a prime :math:`p`:
  the numbers ``0 .. p - 1``, with every result reduced ``% p``. Division by
  :math:`a \ne 0` is multiplication by its *inverse* ``pow(a, -1, p)``.
  :math:`|\mathbb{F}|` is the number of elements, :math:`p`.
- A *polynomial* is like a list of coefficients ``c``. Evaluating it at
  :math:`r` gives ``sum(ci * r**i for i, ci in enumerate(c)) % p``. Its
  *degree* is the highest power with a nonzero coefficient. A *root* is a
  point where it is zero.
- A *hash function* is like Python's ``hash()``, but built so that nobody can
  find two inputs with the same output (a *collision*), or an input with a
  chosen output.
- A *commitment* is like a sealed envelope. The prover fixes a value now. The
  value stays hidden, and the prover cannot change it later.
- A *Merkle tree* commits to a list of values. Hash the values in pairs, then
  hash the results in pairs, and so on, up to a single hash, the *root*. To
  show one value, the prover gives its *authentication path*: the
  :math:`\lceil \log_2 N \rceil` sibling hashes on the way up, from which
  anyone can recompute the root.
- A *group* here is a set of elements that can be combined (written
  :math:`+`) and the combination undone. Fix an element :math:`G`. Then
  :math:`[x]G` means :math:`G` combined with itself :math:`x` times. It is
  fast to compute, by the same repeated doubling as ``pow(g, x, p)``. Going
  back from :math:`[x]G` to :math:`x` is the *discrete logarithm* problem. In
  a large, well-chosen group nobody knows a fast way to solve it, so
  :math:`[x]G` *hides* :math:`x`. Hidden values can still be added:
  :math:`[a]G + [b]G = [a + b]G`. Some entries write the same group
  multiplicatively, as :math:`G^x`.

Cryptographers measure strength in bits. A system has *b-bit security* if the
best known attack needs about :math:`2^b` basic operations.

- :math:`2^{64} \approx 1.8 \times 10^{19}` operations is within reach of a
  large cluster in days.
- :math:`2^{128} \approx 3.4 \times 10^{38}` is not. Even the whole Bitcoin
  mining network, the largest computation on Earth, would need roughly the
  age of the universe.

The models in :mod:`blockchainkit.proofs` work over the BabyBear field
(:math:`p = 15 \cdot 2^{27} + 1`, about two billion), a 35-bit toy pairing
curve, and the 62-bit teaching group of :mod:`blockchainkit.crypto`. Every
number is small enough to print. The setup secrets of the pairing curve can be
recovered by brute force. That shows concretely why they must be destroyed.
:doc:`/protocol` lists where the models depart from deployed systems.

.. contents:: Timeline
   :local:
   :depth: 1

1980 -- The Schwartz-Zippel Lemma: Polynomial Identities at Random Points
-------------------------------------------------------------------------

Are two formulas, such as :math:`(x + y)^{20}` and a long expanded sum, the
same polynomial? Expanding them can take exponential time.

Schwartz, and independently Zippel and DeMillo and Lipton, observed that a
nonzero polynomial cannot be zero at many points. Precisely:

- let :math:`f` be a nonzero polynomial in :math:`n` variables over a field
  :math:`\mathbb{F}`;
- let its *total degree* be :math:`d`: the largest sum of exponents in any
  term, so :math:`x^2 y` has total degree 3;
- let :math:`S` be a finite set of field elements;
- draw :math:`r_1, \dots, r_n` uniformly at random from :math:`S`.

Then

.. math::

   \Pr\left[f(r_1, \dots, r_n) = 0\right] \le \frac{d}{|S|}.

In words: a random point is a root with probability at most the degree divided
by the number of choices. For one variable this is the familiar fact that a
nonzero polynomial of degree :math:`d` has at most :math:`d` roots.

To test whether :math:`g` and :math:`h` are equal:

#. Pick a random point :math:`r`.
#. Evaluate both sides there.
#. Accept if :math:`g(r) = h(r)`.

Why it works:

- Apply the lemma to :math:`f = g - h`. If :math:`g` and :math:`h` are the
  same polynomial, they agree everywhere.
- If they differ, :math:`f` is nonzero. So they agree at a random point with
  probability at most :math:`d/|S|`.
- One evaluation of each side therefore decides equality. A large field makes
  the error *negligible*: so small that it never happens in practice. With
  :math:`d = 100` over a :math:`2^{256}`-element field it is below
  :math:`2^{-249}`.
- This is the single probabilistic fact behind every *succinct* (short,
  fast-to-check) proof system below. Each reduces its claim to a polynomial
  identity and checks it at a point the prover could not predict.
- The point must be unpredictable. A prover who knew it in advance could make
  a false identity hold there.

*Implementation:* :func:`blockchainkit.proofs.systems.identity.identity_test`
and :func:`blockchainkit.proofs.systems.identity.schwartz_zippel_bound`, on
top of the polynomial arithmetic of :mod:`blockchainkit.proofs.utils.polynomials`.
The verifier's randomness is a seeded generator, and the default field is
BabyBear, about :math:`2^{31}` elements; deployed systems use fields of
:math:`2^{64}` to :math:`2^{256}` elements or extensions of them.

*References:* J. T. Schwartz, *Fast probabilistic algorithms for
verification of polynomial identities*, Journal of the ACM 27(4), 701–717
(1980). `DOI <https://doi.org/10.1145/322217.322225>`__. R. Zippel,
*Probabilistic algorithms for sparse polynomials*, EUROSAM 1979, LNCS 72,
216–226.

.. minigallery:: ../../examples/proofs/foundations/plot_01_schwartz_zippel.py

1990 -- The Sum-Check Protocol
------------------------------

A prover claims a sum over :math:`2^n` points. Can a verifier check it
without computing all :math:`2^n` terms?

The *Boolean cube* :math:`\{0,1\}^n` is the set of all :math:`n`-bit
strings, ``itertools.product((0, 1), repeat=n)``. Lund, Fortnow, Karloff and
Nisan used the previous fact to let a verifier check a claimed sum
:math:`H = \sum_{b \in \{0,1\}^n} f(b)` over all :math:`2^n` points of the
cube, while evaluating :math:`f` at a single point. The idea is to strip off
one variable per round. In round :math:`i` the prover sends the *univariate*
polynomial (a polynomial in one variable :math:`X`)

.. math::

   g_i(X) = \sum_{b_{i+1}, \dots, b_n \in \{0, 1\}} f(r_1, \dots, r_{i-1}, X, b_{i+1}, \dots, b_n),

In words: the earlier variables are fixed to the verifier's past random
challenges :math:`r_1, \dots, r_{i-1}`, variable :math:`i` is left free, and
the later ones are summed out over 0 and 1. Each round then runs:

#. The prover sends :math:`g_i`.
#. The verifier checks that it is consistent with the previous claim:
   :math:`g_i(0) + g_i(1) = g_{i-1}(r_{i-1})`. In round 1 the previous claim
   is :math:`H` itself (write :math:`g_0(r_0) = H`).
#. The verifier replies with a random field element :math:`r_i`.
#. The new claim is the value :math:`g_i(r_i)`.

After :math:`n` rounds every variable is fixed. The verifier compares
:math:`g_n(r_n)` with one evaluation :math:`f(r_1, \dots, r_n)`.

Why it is *sound* (a false claim is caught):

- Soundness follows round by round. If the claim entering a round is false,
  the true :math:`g_i` fails the consistency check. So a prover that passes
  must send some other polynomial.
- Let :math:`d` be the degree of :math:`f` in each variable. Two distinct
  polynomials of degree at most :math:`d` agree at no more than :math:`d`
  points. So the random :math:`r_i` exposes the lie with probability at least
  :math:`1 - d/|\mathbb{F}|`. Otherwise the prover carries a false claim into
  the next round.
- Over :math:`n` rounds a false sum survives with probability at most
  :math:`nd/|\mathbb{F}|`.

Why it matters:

- A *Boolean formula* is like a Python expression of ``and``, ``or`` and
  ``not`` over ``bool`` variables. *Arithmetization* turns it into a
  polynomial that equals 1 when the formula is true and 0 when false:
  ``x and y`` becomes :math:`xy`, ``not x`` becomes :math:`1 - x`.
- Take :math:`f` to be the arithmetization of a formula. Then the sum counts
  its *satisfying assignments*: the inputs that make it true.
- So even counting has a short interactive proof. Counting (#SAT) is believed
  far harder than NP, the class of problems whose solutions are quick to check
  once found, like a filled-in sudoku.
- Sum-check is now the core of GKR, Spartan, Lasso and Jolt, modern proof
  systems for general computations.

The model writes formulas in *CNF*: an AND of clauses, each an OR of
variables or their negations. Its *multilinear extension* is the unique
polynomial of degree at most one in each variable that matches given values on
the cube.

*Implementation:* :func:`blockchainkit.proofs.systems.sumcheck.sumcheck`,
:func:`blockchainkit.proofs.systems.sumcheck.verify_sumcheck` and
:func:`blockchainkit.proofs.systems.sumcheck.multilinear_extension`, with
formulas as :class:`~blockchainkit.proofs.core.base.CNF`. The protocol is
run interactively with a seeded verifier, and a false claim makes the
prover lie optimally; deployed uses make it non-interactive with
Fiat-Shamir.

*References:* C. Lund, L. Fortnow, H. Karloff and N. Nisan, *Algebraic
methods for interactive proof systems*, Journal of the ACM 39(4), 859–868
(1992); FOCS 1990. `DOI <https://doi.org/10.1145/146585.146605>`__.

.. minigallery:: ../../examples/proofs/foundations/plot_02_sumcheck.py

1990 -- Shamir's IP = PSPACE
----------------------------

How much can a quick, randomized verifier be convinced of by talking to an
all-powerful prover?

Two classes of problems matter here:

- **IP** (*interactive proofs*): problems where a prover can convince a
  randomized verifier that runs in polynomial time, by exchanging messages.
- **PSPACE**: problems solvable with a polynomial amount of memory, however
  long the computation takes.

A few weeks after sum-check, Shamir proved that the two are equal. One
direction is easy. A polynomial-space machine can explore every possible
conversation with the verifier, one at a time, and so work out whether a
prover could win.

For the other direction, it suffices to prove the truth of a *fully quantified
Boolean formula* (TQBF). Such a formula puts "for all" (:math:`\forall`) or
"there exists" (:math:`\exists`) in front of every variable. For example,
:math:`\forall x\, \exists y\, (x \ne y)` is
``all(any(x != y for y in (0, 1)) for x in (0, 1))``. Every PSPACE problem
can be rewritten as such a formula (TQBF is *complete* for PSPACE).

On the values 0 and 1, "for all" is an AND and "there exists" an OR. So both
become polynomials:

.. math::

   \forall_i f = f|_{x_i = 0} \cdot f|_{x_i = 1}, \qquad
   \exists_i f = 1 - \left(1 - f|_{x_i = 0}\right)\left(1 - f|_{x_i = 1}\right),

Here :math:`f|_{x_i = 0}` means :math:`f` with :math:`x_i` set to 0. In words:
"for all" multiplies the two cases, and "there exists" is one minus the
product of their failures. The prover then peels the operators off one at a
time as in sum-check, with products in place of sums.

The obstacle is degree:

- Each product doubles the degree. After :math:`n` quantifiers the prover
  would send polynomials of degree :math:`2^n`.
- That is too long to send. It is also too high for the
  :math:`d/|\mathbb{F}|` bound to mean anything.

Shen's simplification inserts after every quantifier the *linearization*

.. math::

   L_i f = (1 - x_i)\, f|_{x_i=0} + x_i\, f|_{x_i=1},

In words: draw the straight line between the values at :math:`x_i = 0` and
:math:`x_i = 1`. It agrees with :math:`f` whenever :math:`x_i` is 0 or 1, so
the truth value is unchanged. But it has degree one in :math:`x_i`. Every
polynomial the prover sends then stays of low degree, and the sum-check
argument goes through.

The result showed that interaction and randomness make a polynomial-time
verifier far more powerful than one that only reads a fixed NP *certificate*,
like the filled-in sudoku.

*Implementation:* :func:`blockchainkit.proofs.systems.ip_pspace.tqbf_protocol`
over :class:`~blockchainkit.proofs.core.base.QBF`, with Shen's operator
order from :func:`blockchainkit.proofs.systems.ip_pspace.tqbf_operators`;
``linearize=False`` shows the degree blow-up. The honest prover evaluates
the inner expressions by memoized brute force, so formulas are limited to
a handful of variables.

*References:* A. Shamir, *IP = PSPACE*, Journal of the ACM 39(4),
869–877 (1992); FOCS 1990. `DOI <https://doi.org/10.1145/146585.146609>`__.
A. Shen, *IP = PSPACE: simplified proof*, Journal of the ACM 39(4),
878–880 (1992).

.. minigallery:: ../../examples/proofs/foundations/plot_03_ip_pspace.py

1992 -- The PCP Theorem: Checking a Proof by Reading a Few Bits
---------------------------------------------------------------

Interactive proofs need a live prover. Can a fixed, written proof be checked
by reading only a few of its bits?

A *PCP* (probabilistically checkable proof) is such a proof. Arora and Safra,
and Arora, Lund, Motwani, Sudan and Szegedy, showed that every NP statement
has one. Its verifier:

- uses only :math:`O(\log n)` random bits;
- reads a *constant* number of positions of the proof;
- always accepts a correct proof;
- rejects any proof of a false statement with probability at least 1/2.

In symbols, :math:`\mathrm{NP} = \mathrm{PCP}(\log n, 1)`: logarithmic
randomness, a constant number of reads.

The simplest piece of their construction shows why so few reads can suffice.
:math:`\mathrm{GF}(2)` is the field with two elements: addition is XOR
(``^``) and multiplication is AND (``&``). The prover wants to show that a
system of quadratic equations over :math:`\mathrm{GF}(2)` has a solution
:math:`u`, a bit string. It writes down two tables:

- :math:`f(x) = \langle u, x\rangle`, the *parity* of the bits of :math:`u`
  selected by :math:`x`: ``sum(ui & xi for ui, xi in zip(u, x)) % 2``, for
  every :math:`x`.
- :math:`h(y) = \langle u \otimes u, y\rangle`, the same for the *tensor
  product* :math:`u \otimes u`, the list of all products
  ``[ui & uj for ui in u for uj in u]``.

This encoding is exponentially long but very redundant. The verifier makes
three random tests. First, Blum, Luby and Rubinfeld's *linearity test*,

.. math::

   f(x) + f(y) = f(x + y)

at random :math:`x, y`. In words: a table of parities must respect XOR. It
passes with high probability only if each table is close to a *linear*
function, that is, to the parities of *some* vector. The other two tests:

- **Tensor test.** :math:`f(x) f(y) = h(x \otimes y)` checks that the second
  table encodes :math:`u \otimes u` for the *same* :math:`u`.
- **Equation test.** The sum of a random subset of the equations is a single
  linear condition on :math:`u` and :math:`u \otimes u`. One query to each
  table checks it. If any equation fails, the random sum fails with
  probability 1/2.

The tables are only known to be *close* to correct. So every value is read
through *self-correction*: :math:`f(x) = f(x + r) - f(r)` for a random
:math:`r`. A few corrupted entries are then unlikely to be hit.

The theorem also showed that, for many optimization problems, even finding an
approximately best answer is as hard as finding the best one. For blockchains,
it showed that checking a proof need not mean reading it.

*Implementation:* :func:`blockchainkit.proofs.systems.pcp.hadamard_proof`,
:func:`blockchainkit.proofs.systems.pcp.pcp_verify` and
:func:`blockchainkit.proofs.systems.pcp.run_pcp_verifier` over
:class:`~blockchainkit.proofs.core.base.QuadraticSystem`. This is the
exponentially long Hadamard PCP with 14 queries per repetition, limited to
four variables (65,552 bits); the polynomial-size constructions of the full
theorem are not implemented.

*References:* S. Arora and S. Safra, *Probabilistic checking of proofs: a
new characterization of NP*, Journal of the ACM 45(1), 70–122 (1998); FOCS
1992. `DOI <https://doi.org/10.1145/273865.273901>`__. S. Arora, C. Lund,
R. Motwani, M. Sudan and M. Szegedy, *Proof verification and the hardness
of approximation problems*, Journal of the ACM 45(3), 501–555 (1998); FOCS
1992. `DOI <https://doi.org/10.1145/278298.278306>`__.

.. minigallery:: ../../examples/proofs/pcp/plot_01_pcp_theorem.py

1992 -- Kilian's Succinct Arguments from Merkle Commitments
-----------------------------------------------------------

A PCP is fast to check but no shorter to send. The verifier reads a few bits,
yet the whole proof must still reach it.

Kilian sent only the bits that are read:

#. The prover builds a Merkle tree over the PCP, one leaf per bit, and sends
   the root.
#. The verifier then chooses its queries.
#. The prover opens each queried position: it sends the bit and its
   authentication path.
#. The verifier recomputes the root from each path and runs the PCP checks.

The order matters:

- The PCP's soundness assumes the proof is fixed before the queries are
  known.
- The root fixes it. Answering a query differently from the committed string
  would require a hash collision.
- A *computationally bounded* prover, one that cannot do infeasible amounts of
  work, is thus bound to one proof.

The conversation costs

.. math::

   |\text{root}| + q \cdot \left(1 + |\text{hash}| \cdot \lceil \log_2 N \rceil\right)

bits for :math:`q` queries into an :math:`N`-bit PCP. In words: one root, and
for each query the bit and its path of :math:`\lceil \log_2 N \rceil` hashes.

Proof or argument?

- A *proof* is sound against every prover, even one with unlimited computing
  power.
- Here soundness rests on the hash: a prover who could find collisions could
  cheat. So this is an *argument* rather than a proof.
- Its size is *polylogarithmic* in the computation: it grows like a power of
  :math:`\log N`. This was the first succinct argument for NP.

*Implementation:* :func:`blockchainkit.proofs.systems.kilian.kilian_argument`
and :func:`blockchainkit.proofs.systems.kilian.commit_pcp`, which commits
with :class:`~blockchainkit.structures.systems.merkle.MerkleTree`, one leaf
per PCP bit. The PCP is the Hadamard one above, whose length is
exponential, so the argument is shorter than the PCP only at four
variables, the largest size the model supports; Kilian used the
polynomial-size PCPs of the PCP theorem.

*References:* J. Kilian, *A note on efficient zero-knowledge proofs and
arguments*, STOC 1992, 723–732.
`DOI <https://doi.org/10.1145/129712.129782>`__.

.. minigallery:: ../../examples/proofs/pcp/plot_02_kilian_arguments.py

1994 -- Micali's Computationally Sound Proofs
---------------------------------------------

Kilian's argument still needs the verifier online, to choose queries after the
commitment.

Micali removed the interaction with the Fiat-Shamir idea:

#. The prover commits to the PCP and computes the Merkle root.
#. It derives the query positions by hashing the root.
#. It opens those positions, and publishes root, answers and paths as one
   *computationally sound proof* (CS proof).
#. Anyone can check it later, by recomputing the queries from the root.

Why the order still holds:

- Model the hash as a *random oracle*: an ideal hash that behaves like a
  lookup table filled with truly random outputs.
- Then the prover cannot know which positions will be read until it has
  committed. That preserves the order Kilian's soundness relies on.

What changes is that a cheater can now retry offline:

#. It commits to a bad PCP and sees unfavourable queries.
#. It alters the PCP, commits again, and gets fresh queries.
#. It repeats as often as it likes.

Suppose a cheating PCP passes each of :math:`k` independent query repetitions
with probability :math:`\varepsilon`. Then one commitment succeeds with
probability :math:`\varepsilon^k`, so the cheater needs on average

.. math::

   \mathbb{E}[\text{attempts}] = \varepsilon^{-k}

commitments. In words: each extra repetition multiplies the cheater's work by
:math:`1/\varepsilon`.

Consequences:

- Non-interactive soundness is therefore a cost in hashing. :math:`k` is
  chosen to make that cost infeasible. With :math:`\varepsilon = 1/2` and
  :math:`k = 128`, a cheater needs :math:`2^{128}` attempts, far beyond every
  computer on Earth.
- A *SNARK* is a succinct non-interactive argument of knowledge: a short proof
  that needs no conversation. It is *transparent* if it needs no trusted
  setup. CS proofs are the template of every transparent SNARK.
- This bound is why STARKs add a *proof of work* to each attempt: a small
  brute-force puzzle. Making every retry more expensive lets them use fewer
  queries for the same security.

*Implementation:* :func:`blockchainkit.proofs.systems.kilian.micali_proof`
and :func:`blockchainkit.proofs.systems.kilian.verify_cs_proof`, returning a
:class:`~blockchainkit.proofs.core.base.CSProof`. The queries come from a
SHA-256 :class:`~blockchainkit.proofs.utils.transcript.Transcript` of the
statement, the root and a salt; the salt stands in for the prover's freedom
to recommit, which a real cheater would exercise by changing the PCP.

*References:* S. Micali, *Computationally sound proofs*, SIAM Journal on
Computing 30(4), 1253–1298 (2000); FOCS 1994.
`DOI <https://doi.org/10.1137/S0097539795284959>`__.

.. minigallery:: ../../examples/proofs/pcp/plot_03_micali_cs_proofs.py

2010 -- Kate-Zaverucha-Goldberg Polynomial Commitments
------------------------------------------------------

A Merkle commitment opens one value per path of hashes. Can one commit to a
whole polynomial, and open it anywhere, with a single small value each time?

Kate, Zaverucha and Goldberg did this with one group element for the
commitment and one more per opening. They need a *pairing*: a function
:math:`e` that takes two group elements and multiplies their hidden values,
:math:`e([a]G, [b]G) = e(G, G)^{ab}`. Nobody can compute :math:`[ab]G` from
:math:`[a]G` and :math:`[b]G`. But with a pairing anyone can *check* whether
a third element hides :math:`ab`.

#. **Setup.** Someone picks a secret :math:`\tau` and publishes
   :math:`[\tau^i]G` for :math:`i = 0, 1, \dots, D`: the powers of
   :math:`\tau`, hidden in the group. Then :math:`\tau` must be destroyed.
#. **Commit.** For a polynomial :math:`f` with coefficients :math:`c_i`,
   anyone can compute :math:`[f(\tau)]G = \sum_i c_i [\tau^i]G` without
   learning :math:`\tau`. The commitment is :math:`C = [f(\tau)]G`.
#. **Open.** To prove :math:`f(z) = y`, the prover uses the *factor theorem*:
   :math:`f(z) = y` exactly when :math:`X - z` divides :math:`f(X) - y`. If
   the claim is true, :math:`q(X) = (f(X) - y)/(X - z)` is a polynomial, and
   the prover sends :math:`W = [q(\tau)]G`. If it is false, no such
   polynomial exists.
#. **Verify.** The verifier cannot see :math:`\tau`. But the pairing
   multiplies hidden values, so it can check the division at the hidden
   point:

.. math::

   e(C - [y]G,\ G) = e(W,\ [\tau]G - [z]G),

which says :math:`f(\tau) - y = q(\tau)(\tau - z)`.

Why it works, and where it is used:

- A prover who does not know :math:`\tau` cannot satisfy this with a false
  :math:`y`, by the same Schwartz-Zippel reasoning. The identity would have
  to hold at a point it cannot predict.
- Commitments and openings are constant-size, whatever the degree.
- KZG is the polynomial commitment of PLONK and its descendants. It is also
  used by Ethereum's *blob transactions* (EIP-4844), which attach large
  chunks of data to blocks cheaply.
- Pairings exist only on special groups built from *elliptic curves*. This
  page's toy curve has a *symmetric* pairing, whose two inputs come from the
  same group. Deployed curves use *asymmetric* pairings, whose inputs come
  from two different groups.

*Implementation:* :func:`blockchainkit.proofs.systems.kzg.trusted_setup`,
:func:`blockchainkit.proofs.systems.kzg.kzg_commit`,
:func:`blockchainkit.proofs.systems.kzg.kzg_open` and
:func:`blockchainkit.proofs.systems.kzg.kzg_verify`, over the symmetric
reduced Tate pairing of :func:`blockchainkit.proofs.systems.pairing.pairing`
on :data:`~blockchainkit.proofs.systems.pairing.PAIRING_CURVE`, a 35-bit
supersingular curve whose group order is the BabyBear prime. Its discrete
logarithms take seconds; deployments use BLS12-381 or BN254, with an
asymmetric pairing.

*References:* A. Kate, G. M. Zaverucha and I. Goldberg, *Constant-size
commitments to polynomials and their applications*, ASIACRYPT 2010, LNCS
6477, 177–194. `DOI <https://doi.org/10.1007/978-3-642-17373-8_11>`__.

.. minigallery:: ../../examples/proofs/snarks/plot_01_kzg_commitments.py

2013 -- Quadratic Arithmetic Programs and Pinocchio
---------------------------------------------------

To prove an arbitrary computation this way, the computation must become one
polynomial identity.

Gennaro, Gentry, Parno and Raykova showed how. Write the computation as a
*circuit*: a network of addition and multiplication gates, like a sequence of
Python assignments ``t = x * y``. Then:

#. Collect all *wire values* (inputs, outputs and intermediate results), with
   a leading 1, in a vector :math:`z`. The secret part of :math:`z` is the
   *witness*: the values that make the computation work.
#. Write each gate :math:`j` as a *rank-1 constraint*
   :math:`\langle a_j, z\rangle \langle b_j, z\rangle = \langle c_j, z\rangle`.
   Here :math:`\langle a, z\rangle` is the dot product
   ``sum(ai * zi for ai, zi in zip(a, z))``. So each constraint says "(one
   sum of wires) times (another) equals (a third)".
#. Assign constraint :math:`j` to the point :math:`\omega^j`. Here
   :math:`\omega` is a *primitive* :math:`n`-*th root of unity*: a field
   element with ``pow(w, n, p) == 1`` but no smaller positive power equal to
   1. So :math:`\omega^0, \dots, \omega^{n-1}` are :math:`n` distinct points.
#. *Interpolate* each column into polynomials :math:`A_i, B_i, C_i` that take
   the constraint coefficients at those points. Interpolation finds the
   polynomial through given points, as a line goes through two.

Then

.. math::

   P(X) = \sum_i z_i A_i(X) \cdot \sum_i z_i B_i(X) - \sum_i z_i C_i(X)

evaluates at :math:`\omega^j` to the error of constraint :math:`j`: left side
minus right side. The witness satisfies every constraint exactly when
:math:`P` is zero at all :math:`n` points :math:`\omega^j`. Those points are
the roots of :math:`X^n - 1`. So, by the factor theorem, that happens exactly
when

.. math::

   P(X) = H(X)\,(X^n - 1)

for some polynomial :math:`H`. In words: a whole computation is correct
exactly when one polynomial divides another. This is a *quadratic arithmetic
program* (QAP).

What followed:

- Pinocchio, by Parno, Howell, Gentry and Raykova, checked this identity with
  pairings at one secret setup point, as KZG does.
- It added a compiler from C programs to circuits.
- It was the first general-purpose SNARK efficient enough to use.
- Zcash's first circuits ran on its successor, by Ben-Sasson, Chiesa, Tromer
  and Virza.

*Implementation:* :class:`blockchainkit.proofs.systems.circuits.Circuit`
builds the rank-1 constraint system
(:class:`~blockchainkit.proofs.core.base.R1CS`) and its witness together;
:func:`blockchainkit.proofs.systems.qap.r1cs_to_qap` and
:func:`blockchainkit.proofs.systems.qap.qap_divide` form the QAP and the
division. The pairing-based argument on top is the next-but-one entry,
Groth16, rather than Pinocchio's own.

*References:* R. Gennaro, C. Gentry, B. Parno and M. Raykova, *Quadratic
span programs and succinct NIZKs without PCPs*, EUROCRYPT 2013, LNCS 7881,
626–645. `DOI <https://doi.org/10.1007/978-3-642-38348-9_37>`__. B. Parno,
J. Howell, C. Gentry and M. Raykova, *Pinocchio: nearly practical
verifiable computation*, IEEE S&P 2013, 238–252.
`DOI <https://doi.org/10.1109/SP.2013.47>`__.

.. minigallery:: ../../examples/proofs/snarks/plot_02_qap_pinocchio.py

2014 -- Zerocash: Notes, Nullifiers and Private Payments
--------------------------------------------------------

On Bitcoin, everyone can see who paid whom and how much. Ben-Sasson, Chiesa,
Garman, Green, Miers, Tromer and Virza used SNARKs to build a payment system
that hides sender, receiver and amount.

The design has to solve two problems at once:

- the ledger must stop a coin from being spent twice (*double spending*);
- yet it must not learn which coin is spent.

A coin is a *note* :math:`(\mathit{owner}, v, \rho, r)`: its owner, its value
:math:`v`, a random serial value :math:`\rho`, and randomness :math:`r` for
hiding. The ledger stores only the note's commitment, as a leaf of a Merkle
tree with root :math:`\mathit{rt}`. The owner holds a secret key
:math:`\mathit{sk}`. A *PRF* (pseudorandom function) is like a hash keyed by a
secret: without the key, its outputs look random.

To spend a note:

#. The spender computes the note's *nullifier*
   :math:`\mathrm{nf} = \mathrm{PRF}_{\mathit{sk}}(\rho)`.
#. It creates a new note for the payee and computes its commitment.
#. It writes a zero-knowledge SNARK of the statement below.
#. It publishes the nullifier, the new commitment and the proof.
#. The ledger checks the proof. It rejects the spend if it has already
   recorded :math:`\mathrm{nf}`. Otherwise it records :math:`\mathrm{nf}` and
   adds the new commitment to the tree.

The proof states:

.. math::

   \exists\,\text{note}, \mathit{sk}, \text{path}:\
   \mathrm{Com}(\text{note}) \in \mathrm{Tree}(\mathit{rt}),\
   \mathrm{nf} = \mathrm{PRF}_{\mathit{sk}}(\rho),\
   v_\text{in} = v_\text{out} + v_\text{pub}.

In words: "I know a note, a key and a Merkle path such that the note is in the
tree, this nullifier belongs to it, and the value in equals the value out plus
any amount :math:`v_\text{pub}` leaving the pool in public."

Why it works:

- The proof shows that the spent note exists, that the spender owns it, and
  that value is conserved, without saying which leaf it is.
- The nullifier handles double spending. It is a deterministic function of
  the note, so a second spend of the same note would publish the same
  :math:`\mathrm{nf}`, which the ledger already recorded and rejects.
- A PRF output looks random to anyone without :math:`\mathit{sk}`. So nobody
  can link a nullifier to its commitment.
- The *anonymity set* of each spend, the set of notes it could be, is
  therefore every note ever created.

Zcash launched on this design in 2016.

*Implementation:* :class:`blockchainkit.proofs.systems.zerocash.ShieldedPool`,
:func:`blockchainkit.proofs.systems.zerocash.prove_spend` and
:func:`blockchainkit.proofs.systems.zerocash.spend_circuit`, proving with
Groth16 on the toy pairing and hashing with MiMC
(:func:`blockchainkit.proofs.systems.zerocash.mimc_hash`) rather than
SHA-256. A spend has one input, one output and a public amount, instead of
Zerocash's two and two, and the new note is not encrypted to the payee.

*References:* E. Ben-Sasson, A. Chiesa, C. Garman, M. Green, I. Miers,
E. Tromer and M. Virza, *Zerocash: decentralized anonymous payments from
Bitcoin*, IEEE S&P 2014, 459–474.
`DOI <https://doi.org/10.1109/SP.2014.36>`__.

.. minigallery:: ../../examples/proofs/privacy/plot_01_zerocash.py

2016 -- Groth16: Three Group Elements per Proof
-----------------------------------------------

Every byte of a proof stored on a blockchain is paid for. On Ethereum, every
pairing in its verification also costs *gas*, the fee charged per unit of
computation.

Groth found the shortest pairing-based argument for a QAP known. A proof is
three group elements :math:`A, B, C`, checked by one equation:

.. math::

   e(A, B) = e(\alpha, \beta)\; e\Big(\sum_{i \le \ell} x_i L_i,\ \gamma\Big)\; e(C, \delta),

where :math:`x_i` are the public inputs. In words: the pairing of the prover's
:math:`A` and :math:`B` must equal a fixed part, times a part the verifier
builds from the public inputs, times a part built from the prover's
:math:`C`. (The setup publishes :math:`\alpha, \beta, \gamma, \delta` hidden
in the group; the formula writes them without brackets.)

The protocol:

#. **Setup.** Encode the QAP polynomials at a secret :math:`\tau`, together
   with extra secrets :math:`\alpha, \beta, \gamma, \delta`. All of these
   secrets are the *toxic waste*: they must be destroyed.
#. **Prove.** The prover computes :math:`A, B, C` from the witness and the
   published setup values. It adds fresh randomness to :math:`A` and
   :math:`B` (*blinding*).
#. **Verify.** The verifier computes :math:`\sum x_i L_i` and checks the
   equation with three pairings, :math:`e(\alpha, \beta)` being fixed.

Each extra secret has a job:

- :math:`\alpha` and :math:`\beta` force :math:`A` and :math:`B` to be built
  from those encoded polynomials. So the prover cannot use arbitrary group
  elements.
- :math:`\gamma` and :math:`\delta` separate the part the verifier computes
  from public inputs (:math:`L_i`) from the part only the prover can compute
  from the private witness (:math:`C`).

Why it works, and its limits:

- Expanded in the hidden values, the equation holds at :math:`\tau` only if
  the QAP divisibility does. A prover ignorant of :math:`\tau` can arrange
  that only by satisfying the circuit.
- The blinding makes proofs *perfectly* zero-knowledge: they reveal nothing
  about the witness, even to an unlimited attacker.
- Groth further proved that arguments of this kind need at least two group
  elements. So three is close to optimal.
- Zcash Sapling, Tornado Cash, Filecoin and many *rollups* (systems that
  batch many transactions off chain and post one proof) verify Groth16
  proofs.

*Implementation:* :func:`blockchainkit.proofs.systems.groth16.groth16_setup`,
:func:`blockchainkit.proofs.systems.groth16.groth16_prove` and
:func:`blockchainkit.proofs.systems.groth16.groth16_verify`, with the
toxic waste passed in explicitly as a
:class:`~blockchainkit.proofs.core.base.Groth16Trapdoor`. The pairing is
symmetric, so :math:`B` lies in the same group as :math:`A`; Groth's
analysis assumes an asymmetric pairing.

*References:* J. Groth, *On the size of pairing-based non-interactive
arguments*, EUROCRYPT 2016, LNCS 9666, 305–326.
`DOI <https://doi.org/10.1007/978-3-662-49896-5_11>`__.

.. minigallery:: ../../examples/proofs/snarks/plot_03_groth16.py

2016 -- Zcash's Parameter Ceremony and the Powers of Tau
--------------------------------------------------------

The soundness of KZG, Pinocchio and Groth16 all rests on nobody knowing
:math:`\tau`. Whoever knows it can make a false identity hold at
:math:`\tau`, and so prove false statements. In Zcash, that means printing
money that nobody can see.

The secret must be generated and then destroyed. Nobody can prove they
destroyed it. The answer is to split it among many people, so that it is safe
if *any one* of them is honest.

In October 2016 six participants generated Zcash's parameters. They used a
*multi-party computation* (a calculation done jointly, in which no party
learns the others' inputs) designed by Ben-Sasson, Chiesa, Green, Tromer and
Virza. It was safe unless all six colluded. Bowe, Gabizon and Miers then made
ceremonies scale to any number of participants. Each participant in turn:

#. Picks its own secret :math:`s`.
#. Multiplies the published powers by it:

   .. math::

      [\tau^i]G \mapsto [(\tau s)^i]G,

   that is, it multiplies the :math:`i`-th published element by
   :math:`s^i`, which turns powers of :math:`\tau` into powers of
   :math:`\tau s`.
#. Publishes the new powers and :math:`[s]G`.
#. Destroys :math:`s`.

Why it is safe, and how it is checked:

- The final secret is the product of all contributions. So recovering it
  needs every one of them.
- Anyone can check each step with pairings.
  :math:`e([\tau s]G, G) = e([\tau]G, [s]G)` shows the new powers use the
  published :math:`s`.
- :math:`e([\tau'^{i+1}]G, G) = e([\tau'^{i}]G, [\tau']G)` shows they are
  consecutive powers of one value :math:`\tau' = \tau s`.
- The Powers of Tau (2017–2018) and Ethereum's KZG ceremony (2023, over
  140,000 contributions) followed this design.

Deployed ceremonies also make each participant prove that it knows its
:math:`s`. Bowe, Gabizon and Miers's design ends with a *random beacon*: public
randomness that nobody controls, mixed in last.

*Implementation:* :func:`blockchainkit.proofs.systems.ceremony.start_ceremony`,
:func:`blockchainkit.proofs.systems.ceremony.contribute` and
:func:`blockchainkit.proofs.systems.ceremony.verify_contribution`; with the
secret, :func:`blockchainkit.proofs.systems.kzg.forge_opening` opens a
commitment to any value. Contributions carry no proof of knowledge of
:math:`s` and there is no random-beacon round; the toy group is small
enough to recover :math:`\tau` by brute force.

*References:* E. Ben-Sasson, A. Chiesa, M. Green, E. Tromer and M. Virza,
*Secure sampling of public parameters for succinct zero knowledge proofs*,
IEEE S&P 2015, 287–304. `DOI <https://doi.org/10.1109/SP.2015.25>`__.
S. Bowe, A. Gabizon and I. Miers, *Scalable multi-party computation for
zk-SNARK parameters in the random beacon model*, IACR ePrint 2017/1050.
`Link <https://eprint.iacr.org/2017/1050>`__.

.. minigallery:: ../../examples/proofs/snarks/plot_04_powers_of_tau.py

2018 -- Bulletproofs: Range Proofs without a Trusted Setup
----------------------------------------------------------

*Confidential transactions* hide amounts. A hidden amount must still be shown
to be in range, and with no trusted setup.

The amounts are hidden in *Pedersen commitments*,
:math:`\mathrm{Com}(v, r) = [v]G + [r]H`, where :math:`r` is random. They are
*additively homomorphic*: adding two commitments gives a commitment to the sum.
So a verifier can check that inputs equal outputs without seeing either. But
there is a trap:

- The arithmetic is modulo the *group order*, the number of elements in the
  group. So a "negative" output wraps around to a huge number, as ``-5 % q``
  does in Python.
- Outputs of 15 and :math:`-5` would then balance an input of 10, while
  minting 5 coins.
- Every amount must therefore be shown to lie in :math:`[0, 2^n)`. That is a
  *range proof*.

Bünz, Bootle, Boneh, Poelstra, Wuille and Maxwell built a short one:

#. Write the amount's bits as a vector :math:`a_L`, and set
   :math:`a_R = a_L - \mathbf{1}` (subtract 1 from every entry).
#. Each entry of :math:`a_L` is a bit exactly when
   :math:`a_L \circ a_R = \mathbf{0}`, where :math:`\circ` is the entrywise
   product ``[x * y for x, y in zip(aL, aR)]``. This works because
   :math:`b(b - 1) = 0` only for :math:`b \in \{0, 1\}`.
#. Random challenges combine this condition and "the bits sum to the
   committed amount" into a single *inner product* claim
   :math:`\langle a, b\rangle = c`, that is ``sum(x * y for x, y in zip(a, b))
   == c``.
#. They prove the inner product by halving. Each round the prover sends two
   group elements :math:`L` and :math:`R` and receives a challenge :math:`x`.
#. Both sides fold the vectors and generators to half their length, with
   :math:`a_\text{lo}` and :math:`a_\text{hi}` the two halves of :math:`a`:

.. math::

   a' = x\, a_\text{lo} + x^{-1} a_\text{hi}, \qquad G' = G_\text{lo}^{x^{-1}} \circ G_\text{hi}^{x}.

In words: the new vector is a random-weighted sum of the two halves, and the
new generators are combined the opposite way. (This formula writes the group
multiplicatively.) After :math:`\log_2 n` rounds one scalar remains, and the
prover sends it.

Why it works, and its cost:

- Folding creates cross terms, which mix the two halves. These are exactly
  what :math:`L` and :math:`R` account for. So a valid claim stays valid.
- Because :math:`x` comes after :math:`L` and :math:`R`, a false claim stays
  false except with negligible probability.
- A proof is :math:`2\log_2 n + 4` group elements and five scalars. For a
  64-bit range that is 16 group elements.
- The generators are hashed into the group. So nobody knows a secret relating
  them, and no setup is needed.
- Monero adopted Bulletproofs in 2018 and cut its transaction sizes by about
  80%.

*Implementation:* :func:`blockchainkit.proofs.systems.bulletproofs.range_proof`,
:func:`blockchainkit.proofs.systems.bulletproofs.verify_range_proof` and
:func:`blockchainkit.proofs.systems.bulletproofs.range_commitment`, made
non-interactive by Fiat-Shamir. They run in the multiplicative teaching
group of :mod:`blockchainkit.crypto`, with generators from
:func:`blockchainkit.proofs.utils.groups.independent_generators`, instead
of on an elliptic curve, and prove one value at a time without aggregation.

*References:* B. Bünz, J. Bootle, D. Boneh, A. Poelstra, P. Wuille and
G. Maxwell, *Bulletproofs: short proofs for confidential transactions and
more*, IEEE S&P 2018, 315–334.
`DOI <https://doi.org/10.1109/SP.2018.00020>`__.

.. minigallery:: ../../examples/proofs/transparent/plot_01_bulletproofs.py

2018 -- FRI: Fast Reed-Solomon Proximity Testing
------------------------------------------------

KZG needs a trusted setup to bind a prover to a *low-degree* polynomial (one
whose degree is below a known bound :math:`d`). Can hashes alone do it?

Ben-Sasson, Bentov, Horesh and Riabzev showed they can. The prover evaluates
the polynomial on a *domain* (a set of points) much larger than its degree.
The resulting list of values is a *Reed-Solomon codeword*. It is very
redundant: any :math:`d` values fix all the others, so a few wrong values
stand out. The prover commits to the list with a Merkle tree. *FRI* lets the
verifier check, with logarithmically many queries, that the committed values
are *close* to such a codeword (they differ from one in only a few places).

The key step halves the problem. Split :math:`f` into its even and odd parts,
:math:`f(X) = f_e(X^2) + X f_o(X^2)`:

- both parts have half the degree;
- both can be recovered from the two values at :math:`x` and :math:`-x`.

A random :math:`\alpha` from the verifier combines them into

.. math::

   f'(x^2) = f_e(x^2) + \alpha f_o(x^2) = \frac{f(x) + f(-x)}{2} + \alpha\, \frac{f(x) - f(-x)}{2x},

In words: the folded value at :math:`x^2` needs only the two values
:math:`f(x)` and :math:`f(-x)`. It is a function of half the degree, on a
domain of half the size, because squaring maps :math:`x` and :math:`-x` to
one point.

The protocol:

#. The prover commits to :math:`f` on the domain.
#. The verifier sends a random :math:`\alpha`.
#. The prover computes the folded function :math:`f'` and commits to it with a
   new Merkle tree.
#. Steps 2 and 3 repeat. After :math:`\log_2 d` folds an honest codeword has
   become a constant.
#. Along a few random paths, the verifier opens :math:`f(x)`, :math:`f(-x)`
   and :math:`f'(x^2)` in each layer. It checks that each layer is the fold
   of the one before.

Why it works:

- If :math:`f` has low degree, so does :math:`f'`.
- If :math:`f` is far from low degree, a random :math:`\alpha` keeps
  :math:`f'` far with high probability.
- FRI is the low-degree test of STARKs, Plonky2, RISC Zero and SP1.

The domain must contain :math:`-x` along with every :math:`x`. The model uses
*cosets* of power-of-two subgroups: shifted copies ``[s * h % p for h in H]``
of a set :math:`H` of :math:`2^k` powers of one element.

*Implementation:* :func:`blockchainkit.proofs.systems.fri.fri_prove` and
:func:`blockchainkit.proofs.systems.fri.fri_verify`, on cosets of
power-of-two subgroups of BabyBear, with the FFT of
:func:`blockchainkit.proofs.utils.polynomials.evaluate_on_domain`. The
protocol folds by two down to a constant and has no proof-of-work grinding
or batching of openings.

*References:* E. Ben-Sasson, I. Bentov, Y. Horesh and M. Riabzev, *Fast
Reed-Solomon interactive oracle proofs of proximity*, ICALP 2018, LIPIcs
107, 14:1–14:17. `DOI <https://doi.org/10.4230/LIPIcs.ICALP.2018.14>`__.

.. minigallery:: ../../examples/proofs/transparent/plot_02_fri.py

2018 -- STARKs: Transparent Proofs of Computation from Hashes
-------------------------------------------------------------

FRI tests a single polynomial. A proof system must show that a whole
computation was done correctly.

The same authors used FRI to build *STARKs*: scalable, transparent arguments
of knowledge. These proofs:

- need no trusted setup;
- rely only on hash functions, so no known quantum attack applies (large
  quantum computers would break discrete logarithms, which every
  pairing-based entry above relies on);
- grow polylogarithmically with the computation.

The computation is recorded as an *execution trace*: one value per step, like
the list ``[1, 1, 2, 3, 5, 8, ...]`` for Fibonacci. The trace becomes a
polynomial :math:`f`:

#. Pick a *subgroup* :math:`\langle g\rangle`: the powers
   :math:`g^0, g^1, \dots, g^{T-1}` of an element :math:`g` with
   :math:`g^T = 1`.
#. Interpolate :math:`f` so that :math:`f(g^i)` is the value at step
   :math:`i`.
#. Write each rule of the computation as a polynomial in shifted copies of
   :math:`f`. Since :math:`f(g \cdot g^i) = f(g^{i+1})`, the shift by
   :math:`g` moves to the next step. For the Fibonacci recurrence,
   :math:`f(g^2 X) - f(gX) - f(X)` is zero at :math:`X = g^i` exactly when
   step :math:`i + 2` was computed correctly.

This way of writing rules is an *AIR* (algebraic intermediate
representation). As in a QAP, being zero at all those points is the same as
being divisible by the polynomial with those roots. So the trace is correct
exactly when

.. math::

   \frac{f(g^2 X) - f(gX) - f(X)}{\prod_{i=0}^{T-3} (X - g^i)} \quad \text{is a polynomial}

for a trace of length :math:`T`. In words: the rule's error divides evenly by
the polynomial that is zero at every checked step.

The proof then runs:

#. The prover evaluates the trace polynomial on a much larger domain (a
   *low-degree extension* of the trace) and commits to it with a Merkle tree.
#. It forms the quotients, one per rule.
#. It proves with FRI that a random combination of all the quotients has low
   degree.

Why it works:

- If any step is wrong, the quotient is not a polynomial.
- Its values on a large domain are then far from every low-degree codeword,
  and FRI catches it.
- StarkWare's StarkEx and StarkNet were built on this design.

*Boundary constraints* also fix chosen values, such as the first and last
entries of the trace.

*Implementation:* :func:`blockchainkit.proofs.systems.stark.stark_prove` and
:func:`blockchainkit.proofs.systems.stark.stark_verify` prove one fixed
computation, the Fibonacci trace of
:func:`blockchainkit.proofs.systems.stark.fibonacci_trace`, with boundary
constraints on the first two and last values. There is no general AIR
compiler, no zero-knowledge blinding, and no extension field for the
challenges.

*References:* E. Ben-Sasson, I. Bentov, Y. Horesh and M. Riabzev,
*Scalable, transparent, and post-quantum secure computational integrity*,
IACR ePrint 2018/046. `Link <https://eprint.iacr.org/2018/046>`__.

.. minigallery:: ../../examples/proofs/transparent/plot_03_starks.py

2019 -- PLONK: Permutation Arguments and a Universal Setup
----------------------------------------------------------

Groth16 needs a new ceremony for every circuit, because its setup encodes the
circuit itself.

Gabizon, Williamson and Ciobotaru removed that by moving the circuit out of
the setup. Every gate has the same form,
:math:`q_L a + q_R b + q_O c + q_M ab + q_C = 0`. Here :math:`a, b, c` are the
gate's two inputs and output. The *selectors* :math:`q` are fixed numbers, like
flags, that choose the gate's job:

- addition :math:`a + b = c`: :math:`q_L = q_R = 1`, :math:`q_O = -1`, the
  rest 0;
- multiplication :math:`ab = c`: :math:`q_M = 1`, :math:`q_O = -1`, the rest
  0;
- a constant :math:`a = k`: :math:`q_L = 1`, :math:`q_C = -k`, the rest 0.

The wiring becomes a separate check: wires that carry the same variable must
hold the same value.

#. Number every wire slot (three per gate).
#. Let the *permutation* :math:`\sigma` send each slot to the next slot
   carrying the same variable. Think of a list ``sigma`` where
   ``sigma[i]`` is that next slot.
#. The values are consistent exactly when they are unchanged by
   :math:`\sigma`: ``w[sigma[i]] == w[i]`` for every slot.
#. Equivalently, the *multisets* (collections that count repeats, like
   ``collections.Counter``) :math:`\{(w, \mathrm{id})\}` and
   :math:`\{(w, \sigma)\}` of (value, slot) pairs coincide.
#. With random :math:`\beta, \gamma` from the verifier, that is tested by

.. math::

   \prod_{\text{wires}} (w + \beta\, \mathrm{id} + \gamma) = \prod_{\text{wires}} (w + \beta\, \sigma + \gamma).

In words: fold each (value, slot) pair into one number with random weights,
and multiply all of them together; the two products agree only if the two
collections of pairs do.

Why it works, and its uses:

- Both sides are polynomials in :math:`\beta` and :math:`\gamma` that are
  identical exactly when the multisets are.
- So, by Schwartz-Zippel, the equation holds at a random point with high
  probability only if the wiring is respected.
- The running product becomes a committed polynomial. Gates, copies and
  boundary conditions combine into one quotient, checked at a random point
  with KZG.
- The circuit enters only through committed polynomials. So the setup is
  *universal*: one powers of tau serves every circuit up to a given size.
- Aztec, zkSync, Scroll and Halo 2 descend from PLONK.

*Implementation:* :class:`blockchainkit.proofs.systems.plonk.PlonkCircuit`,
:func:`blockchainkit.proofs.systems.plonk.plonk_setup`,
:func:`blockchainkit.proofs.systems.plonk.plonk_prove`,
:func:`blockchainkit.proofs.systems.plonk.plonk_verify` and
:func:`blockchainkit.proofs.systems.plonk.permutation_product`, with KZG.
Every polynomial is opened at the challenge point instead of using PLONK's
linearization, there is no blinding (so proofs are not zero-knowledge),
and there are no public inputs.

*References:* A. Gabizon, Z. J. Williamson and O. Ciobotaru, *PLONK:
permutations over Lagrange-bases for oecumenical noninteractive arguments
of knowledge*, IACR ePrint 2019/953.
`Link <https://eprint.iacr.org/2019/953>`__.

.. minigallery:: ../../examples/proofs/snarks/plot_05_plonk.py

2019 -- Halo: Recursive Proof Composition without a Trusted Setup
-----------------------------------------------------------------

Imagine a proof, at every block, that also verifies the previous block's
proof. Then anyone could check a whole chain from one short proof. This is
*recursion*. It requires verification cheap enough to run inside a circuit.

Inner-product arguments such as Bulletproofs need no setup. But their verifier
is not cheap. After the folding rounds it must compute the folded generator
:math:`G_\text{final}`. That is a *multi-exponentiation*, a combination of all
the original generators with a different exponent each, as long as the
vector.

Bowe, Grigg and Hopwood observed that this expensive value has structure. The
exponent of each original generator in :math:`G_\text{final}` is a
coefficient of

.. math::

   g(X) = \prod_{j=1}^{k} \left(1 + c_j X^{2^{k-j}}\right),

built from the :math:`k` round challenges :math:`c_j`. In words: the
exponents are products of challenges, one choice per round, which is what
expanding this product gives. So :math:`G_\text{final}` is just a commitment
to :math:`g`.

The asymmetry they exploited:

- *Computing* the commitment takes linear time, :math:`O(n)`.
- *Evaluating* :math:`g` at a point takes only :math:`O(\log n)`, one factor
  per round.

So the verifier works like this:

#. It runs every cheap check of the inner-product argument.
#. It skips the expensive step. It keeps :math:`G_\text{final}` as an
   unchecked claim, an *accumulator*.
#. Two such claims merge into one by opening a random combination of them at
   a random point. That needs only cheap evaluations of each :math:`g`, and
   leaves a single new deferred claim.
#. A chain of proofs thus carries one accumulator forward.
#. Whoever finally needs certainty pays the linear cost once.

Zcash's Orchard pool (2022) runs on Halo 2. Doing this inside circuits needs a
*cycle of curves*: two elliptic curves, each able to check the other's proofs
efficiently.

*Implementation:* :func:`blockchainkit.proofs.systems.halo.ipa_open`,
:func:`blockchainkit.proofs.systems.halo.ipa_defer`,
:func:`blockchainkit.proofs.systems.halo.accumulate`,
:func:`blockchainkit.proofs.systems.halo.verify_accumulation` and
:func:`blockchainkit.proofs.systems.halo.decide`, in the teaching group.
The accumulation is verified in Python rather than inside a circuit over a
cycle of curves, so the recursion itself is not built, and commitments
carry no blinding.

*References:* S. Bowe, J. Grigg and D. Hopwood, *Recursive proof
composition without a trusted setup*, IACR ePrint 2019/1021.
`Link <https://eprint.iacr.org/2019/1021>`__.

.. minigallery:: ../../examples/proofs/transparent/plot_04_halo.py
