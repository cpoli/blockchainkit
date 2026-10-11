Breakthroughs in Proof Systems
==============================

.. include:: /_generated/nav/proofs.rst

.. epigraph::

   "Usually, a proof of a theorem contains more knowledge than the mere fact
   that the theorem is true."
   -- Shafi Goldwasser, Silvio Micali and Charles Rackoff, *The Knowledge
   Complexity of Interactive Proof-Systems*, 1985

A blockchain asks every node to re-execute every transaction. Proof systems
offer another bargain: one party does the work and writes a short proof,
and everyone else checks the proof instead, quickly, and without learning
the secrets behind it. :doc:`crypto_breakthroughs` covers the beginning,
zero-knowledge identification and the Fiat-Shamir heuristic. This
chronology follows the argument from there in five steps:

1. Randomness lets a verifier check a polynomial identity, and through it a
   sum over exponentially many points, by evaluating at one random point
   (Schwartz-Zippel, sum-check, IP = PSPACE).
2. A proof can be written so that reading a few random bits of it suffices
   (the PCP theorem), and committing to it with a Merkle tree makes it short
   enough to send (Kilian, Micali).
3. Pairings let a verifier check a polynomial identity at a *secret* point,
   which gives constant-size proofs (KZG, QAPs, Groth16, PLONK), at the
   price of a trusted setup (the parameter ceremonies), and they made
   private payments practical (Zerocash).
4. Hash functions alone can replace the setup, at the cost of larger proofs
   (FRI, STARKs).
5. Discrete-logarithm groups can replace it too, with logarithmic proofs and,
   eventually, recursion (Bulletproofs, Halo).

The models in :mod:`blockchainkit.proofs` work over the BabyBear field
(:math:`p = 15 \cdot 2^{27} + 1`), a 35-bit toy pairing curve, and the
62-bit teaching group of :mod:`blockchainkit.crypto`. Every number is small
enough to print, and the setup secrets of the pairing curve can be
recovered by brute force, which shows concretely why they must be
destroyed. :doc:`/protocol` lists where the models depart from deployed
systems.

.. contents:: Timeline
   :local:
   :depth: 1

1980 -- The Schwartz-Zippel Lemma: Polynomial Identities at Random Points
-------------------------------------------------------------------------

Deciding whether two arithmetic expressions define the same polynomial
can take exponential time if one expands them. Schwartz, and independently
Zippel and DeMillo and Lipton, observed that a nonzero polynomial cannot
vanish at many points: if :math:`f` is nonzero with total degree :math:`d`
over a field :math:`\mathbb{F}` and :math:`S \subseteq \mathbb{F}` is
finite, then for :math:`r_1, \dots, r_n` drawn uniformly from :math:`S`,

.. math::

   \Pr\left[f(r_1, \dots, r_n) = 0\right] \le \frac{d}{|S|}.

For one variable this is the familiar fact that a nonzero polynomial of
degree :math:`d` has at most :math:`d` roots. Now apply it to
:math:`f = g - h`. If :math:`g` and :math:`h` are the same polynomial they
agree everywhere; if they differ, :math:`f` is nonzero, so they agree at a
random point with probability at most :math:`d/|S|`. One evaluation of
each side therefore decides equality, with an error that a large field
makes negligible. This is the single probabilistic fact behind every
succinct proof system below: each reduces its claim to a polynomial
identity and checks it at a point the prover could not predict, because a
prover who knew the point in advance could make a false identity hold
there.

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

Lund, Fortnow, Karloff and Nisan used this fact to let a verifier check a
claimed sum :math:`H = \sum_{b \in \{0,1\}^n} f(b)` over all :math:`2^n`
points of the Boolean cube while evaluating :math:`f` at a single point.
The idea is to strip off one variable per round. In round :math:`i` the
prover sends the univariate polynomial

.. math::

   g_i(X) = \sum_{b_{i+1}, \dots, b_n \in \{0, 1\}} f(r_1, \dots, r_{i-1}, X, b_{i+1}, \dots, b_n),

in which the earlier variables are fixed to the verifier's past challenges
and the later ones are summed out. The verifier checks that it is
consistent with the previous claim, :math:`g_i(0) + g_i(1) = g_{i-1}(r_{i-1})`
(with :math:`g_0(r_0) = H`), and replies with a random :math:`r_i`; the new
claim is the value :math:`g_i(r_i)`. After :math:`n` rounds every variable
is fixed, and the verifier compares :math:`g_n(r_n)` with one evaluation
:math:`f(r_1, \dots, r_n)`.

Soundness follows round by round. If the claim entering a round is false,
the true :math:`g_i` fails the consistency check, so a prover that passes
must send some other polynomial. Two distinct polynomials of degree at most
:math:`d` (the degree of :math:`f` in each variable) agree at no more than
:math:`d` points, so the random :math:`r_i` exposes the lie with
probability at least :math:`1 - d/|\mathbb{F}|`; otherwise the prover
carries a false claim into the next round. Over :math:`n` rounds a false
sum survives with probability at most :math:`nd/|\mathbb{F}|`. Taking
:math:`f` to be the arithmetization of a Boolean formula, the sum counts its
satisfying assignments, so even counting (#SAT, believed far harder than
NP) has a short interactive proof. Sum-check is now the core of GKR,
Spartan, Lasso and Jolt.

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

A few weeks after sum-check, Shamir proved that interactive proofs capture
exactly the problems solvable in polynomial space. One direction is easy: a
polynomial-space machine can try every strategy of the verifier. For the
other, it suffices to prove the truth of a fully quantified Boolean formula
(TQBF), which is complete for PSPACE. On the values 0 and 1, "for all" is
an AND and "there exists" an OR, so both become polynomials,

.. math::

   \forall_i f = f|_{x_i = 0} \cdot f|_{x_i = 1}, \qquad
   \exists_i f = 1 - \left(1 - f|_{x_i = 0}\right)\left(1 - f|_{x_i = 1}\right),

and the prover peels the operators off one at a time as in sum-check, with
products in place of sums. The obstacle is degree: each product doubles
it, so after :math:`n` quantifiers the prover would send polynomials of
degree :math:`2^n`, too long to send and too high for the
:math:`d/|\mathbb{F}|` bound to mean anything. Shen's simplification
inserts after every quantifier the linearization

.. math::

   L_i f = (1 - x_i)\, f|_{x_i=0} + x_i\, f|_{x_i=1},

which agrees with :math:`f` whenever :math:`x_i` is 0 or 1 (so the truth
value is unchanged) but has degree one in :math:`x_i`. Every polynomial the
prover sends then stays of low degree, and the sum-check argument goes
through. The result showed that interaction and randomness make a
polynomial-time verifier far more powerful than one that only reads a
static NP certificate.

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

Interactive proofs need a live prover. Arora and Safra, and Arora, Lund,
Motwani, Sudan and Szegedy, showed that a fixed, written proof can be
checked almost as cheaply: every NP statement has a proof in which a
verifier, using :math:`O(\log n)` random bits, reads a *constant* number of
positions, always accepts a correct proof, and rejects any proof of a false
statement with probability at least 1/2. In symbols,
:math:`\mathrm{NP} = \mathrm{PCP}(\log n, 1)`.

The simplest piece of their construction shows why so few reads can
suffice. To prove that quadratic equations over GF(2) have a solution
:math:`u`, the prover writes down every parity of :math:`u` and of
:math:`u \otimes u`, the tables :math:`f(x) = \langle u, x\rangle` and
:math:`h(y) = \langle u \otimes u, y\rangle`. This encoding is exponentially
long but very redundant, and the verifier makes three random tests. First,
Blum, Luby and Rubinfeld's linearity test,

.. math::

   f(x) + f(y) = f(x + y)

at random :math:`x, y`, passes with high probability only if each table is
close to a linear function, that is, to the parities of *some* vector.
Second, the tensor test :math:`f(x) f(y) = h(x \otimes y)` checks that the
second table encodes :math:`u \otimes u` for the *same* :math:`u`. Third,
the sum of a random subset of the equations is a single linear condition
on :math:`u` and :math:`u \otimes u`, which one query to each table
checks; if any equation fails, the random sum fails with probability 1/2.
Because the tables are only known to be *close* to correct, every value is
read through self-correction, :math:`f(x) = f(x + r) - f(r)` for a random
:math:`r`, so that a few corrupted entries are unlikely to be hit. The
theorem also founded the theory of hardness of approximation; for
blockchains, it showed that checking a proof need not mean reading it.

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

A PCP is fast to check but no shorter to send: the verifier reads a few
bits, yet the whole proof must still reach it. Kilian sent only the bits
that are read. The prover first sends a Merkle root of the PCP; the
verifier then chooses its queries, and the prover opens each queried
position with its authentication path. The order matters. The PCP's
soundness assumes the proof is fixed before the queries are known, and the
root fixes it: answering a query differently from the committed string
would require a hash collision. A computationally bounded prover is thus
bound to one proof, and the conversation costs

.. math::

   |\text{root}| + q \cdot \left(1 + |\text{hash}| \cdot \lceil \log_2 N \rceil\right)

bits for :math:`q` queries into an :math:`N`-bit PCP: one root, and for
each query the bit and its path of :math:`\lceil \log_2 N \rceil` hashes.
Because soundness now rests on the hash rather than holding against every
prover, this is an *argument* rather than a proof, but its size is
polylogarithmic in the computation: the first succinct argument for NP.

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

Kilian's argument still needs the verifier online to choose queries after
the commitment. Micali removed the interaction with the Fiat-Shamir idea:
the queries are derived by hashing the Merkle root, so the prover writes
the whole argument at once and anyone can check it later. If the hash
behaves as a random oracle, the prover cannot know which positions will be
read until it has committed, which preserves the order Kilian's soundness
relies on.

What changes is that a cheater can now retry offline. Having committed to a
bad PCP and seen unfavourable queries, it can alter the PCP, commit again,
and get fresh queries, as often as it likes. If a cheating PCP passes each
of :math:`k` independent query repetitions with probability
:math:`\varepsilon`, one commitment succeeds with probability
:math:`\varepsilon^k`, so the cheater needs on average

.. math::

   \mathbb{E}[\text{attempts}] = \varepsilon^{-k}

commitments. Non-interactive soundness is therefore a cost in hashing, and
:math:`k` is chosen to make that cost infeasible. CS proofs are the
template of every transparent SNARK, and this bound is why STARKs add a
proof of work to each attempt: making every retry more expensive lets them
use fewer queries for the same security.

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

Merkle commitments open one value per path of hashes. Kate, Zaverucha and
Goldberg committed to a whole polynomial with one group element and opened
it at any point with one more. A setup publishes :math:`[\tau^i]G`, the
powers of a secret :math:`\tau` hidden in a group, so anyone can compute
:math:`[f(\tau)]G` for a polynomial :math:`f` without learning
:math:`\tau`. The commitment is :math:`C = [f(\tau)]G`.

To prove :math:`f(z) = y`, the prover uses the factor theorem:
:math:`f(z) = y` exactly when :math:`X - z` divides :math:`f(X) - y`. If the
claim is true, :math:`q(X) = (f(X) - y)/(X - z)` is a polynomial and the
prover sends :math:`W = [q(\tau)]G`; if it is false, no such polynomial
exists. The verifier cannot see :math:`\tau`, but a bilinear pairing
multiplies hidden exponents, so it can check the division at the hidden
point,

.. math::

   e(C - [y]G,\ G) = e(W,\ [\tau]G - [z]G),

which says :math:`f(\tau) - y = q(\tau)(\tau - z)`. A prover who does not
know :math:`\tau` cannot satisfy this with a false :math:`y`, by the same
Schwartz-Zippel reasoning: the identity would have to hold at a point it
cannot predict. Commitments and openings are constant-size whatever the
degree. KZG is the polynomial commitment of PLONK and its descendants, and
of Ethereum's blob transactions (EIP-4844).

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

To prove arbitrary computations this way, a computation must become one
polynomial identity. Gennaro, Gentry, Parno and Raykova showed how. Write
the circuit as rank-1 constraints
:math:`\langle a_j, z\rangle \langle b_j, z\rangle = \langle c_j, z\rangle`,
one per gate, over the vector :math:`z` of all wire values. Assign
constraint :math:`j` to the point :math:`\omega^j`, where :math:`\omega` is
a primitive :math:`n`-th root of unity, and interpolate each column into
polynomials :math:`A_i, B_i, C_i` that take the constraint coefficients at
those points. Then

.. math::

   P(X) = \sum_i z_i A_i(X) \cdot \sum_i z_i B_i(X) - \sum_i z_i C_i(X)

evaluates at :math:`\omega^j` to the error of constraint :math:`j`. The
witness satisfies every constraint exactly when :math:`P` vanishes at all
:math:`n` points :math:`\omega^j`, which are the roots of
:math:`X^n - 1`, so exactly when

.. math::

   P(X) = H(X)\,(X^n - 1)

for some polynomial :math:`H`. Pinocchio, by Parno, Howell, Gentry and
Raykova, checked this identity with pairings at one secret setup point, as
KZG does, and added a compiler from C; it was the first general-purpose
SNARK efficient enough to use. Zcash's first circuits ran on its successor
by Ben-Sasson, Chiesa, Tromer and Virza.

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

Ben-Sasson, Chiesa, Garman, Green, Miers, Tromer and Virza used such
SNARKs to build a payment system that hides sender, receiver and amount.
The design has to solve two problems at once: the ledger must stop a coin
from being spent twice, yet must not learn which coin is spent.

A coin is a *note* :math:`(\mathit{owner}, v, \rho, r)`, and the ledger
stores only its commitment, as a leaf of a Merkle tree with root
:math:`\mathit{rt}`. Spending publishes three things: the note's nullifier
:math:`\mathrm{nf} = \mathrm{PRF}_{\mathit{sk}}(\rho)`, the commitment to a
new note, and a zero-knowledge SNARK of

.. math::

   \exists\,\text{note}, \mathit{sk}, \text{path}:\
   \mathrm{Com}(\text{note}) \in \mathrm{Tree}(\mathit{rt}),\
   \mathrm{nf} = \mathrm{PRF}_{\mathit{sk}}(\rho),\
   v_\text{in} = v_\text{out} + v_\text{pub}.

The proof shows that the spent note exists, that the spender owns it, and
that value is conserved, without saying which leaf it is. The nullifier
handles double spending: it is a deterministic function of the note, so a
second spend of the same note would publish the same :math:`\mathrm{nf}`,
which the ledger already recorded and rejects. Since a PRF output looks
random to anyone without :math:`\mathit{sk}`, nobody can link a nullifier
to its commitment, so the anonymity set of each spend is every note ever
created. Zcash launched on this design in 2016.

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

Every byte of a proof stored on chain is paid for, and every pairing in its
verification costs gas. Groth found the shortest pairing-based argument
for a QAP known: three group elements :math:`A, B, C`, checked by one
equation,

.. math::

   e(A, B) = e(\alpha, \beta)\; e\Big(\sum_{i \le \ell} x_i L_i,\ \gamma\Big)\; e(C, \delta),

where :math:`x_i` are the public inputs. The setup encodes the QAP
polynomials at a secret :math:`\tau`, and each extra secret has a job.
:math:`\alpha` and :math:`\beta` force :math:`A` and :math:`B` to be built
from those encoded polynomials, so the prover cannot use arbitrary group
elements. :math:`\gamma` and :math:`\delta` separate the part the verifier
computes from public inputs (:math:`L_i`) from the part only the prover
can compute from the private witness (:math:`C`). Expanded in the exponent,
the equation then holds at :math:`\tau` only if the QAP divisibility does,
which a prover ignorant of :math:`\tau` can arrange only by satisfying the
circuit. The prover also adds fresh randomness to :math:`A` and :math:`B`,
which makes proofs perfectly zero-knowledge. Groth further proved that
arguments of this kind need at least two group elements, so three is close
to optimal. Zcash Sapling, Tornado Cash, Filecoin and many rollups verify
Groth16 proofs.

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
:math:`\tau` and so prove false statements; in Zcash, that means printing
money that nobody can see. The secret must be generated and then destroyed,
and nobody can prove they destroyed it. The answer is to split it among
many people so that it is safe if *any one* of them is honest.

In October 2016 six participants generated Zcash's parameters by a
multi-party computation designed by Ben-Sasson, Chiesa, Green, Tromer and
Virza, safe unless all six colluded. Bowe, Gabizon and Miers then made
ceremonies scale to any number of participants. Each in turn multiplies the
published powers by its own secret :math:`s`,

.. math::

   [\tau^i]G \mapsto [(\tau s)^i]G,

publishes :math:`[s]G`, and destroys :math:`s`. The final secret is the
product of all contributions, so recovering it needs every one of them.
Anyone can check each step with pairings: :math:`e([\tau s]G, G) = e([\tau]G, [s]G)`
shows the new powers use the published :math:`s`, and
:math:`e([\tau'^{i+1}]G, G) = e([\tau'^{i}]G, [\tau']G)` shows they are
consecutive powers of one value :math:`\tau' = \tau s`. The Powers of Tau
(2017–2018) and Ethereum's KZG ceremony (2023, over 140,000 contributions)
followed this design.

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

Confidential transactions hide amounts in Pedersen commitments, which are
additively homomorphic: a verifier can check that inputs equal outputs
without seeing either. But the arithmetic is modulo the group order, so a
"negative" output wraps around to a huge number, and outputs of 15 and
:math:`-5` would balance an input of 10 while minting 5 coins. Every amount
must therefore be shown to lie in :math:`[0, 2^n)`, and with no trusted
setup.

Bünz, Bootle, Boneh, Poelstra, Wuille and Maxwell wrote the amount's bits
as a vector :math:`a_L` and set :math:`a_R = a_L - \mathbf{1}`; each entry
of :math:`a_L` is a bit exactly when :math:`a_L \circ a_R = \mathbf{0}`.
Random challenges combine this condition and "the bits sum to the
committed amount" into a single inner product
:math:`\langle a, b\rangle = c`, which they proved by halving. Each round
the prover sends two group elements :math:`L` and :math:`R`, receives a
challenge :math:`x`, and both sides fold the vectors and generators to half
their length,

.. math::

   a' = x\, a_\text{lo} + x^{-1} a_\text{hi}, \qquad G' = G_\text{lo}^{x^{-1}} \circ G_\text{hi}^{x}.

The cross terms that folding creates are exactly what :math:`L` and
:math:`R` account for, so a valid claim stays valid and, because :math:`x`
comes after :math:`L` and :math:`R`, a false one stays false except with
negligible probability. After :math:`\log_2 n` rounds one scalar remains. A
proof is :math:`2\log_2 n + 4` group elements and five scalars, and the
generators are hashed into the group, so nobody knows a secret relating
them and no setup is needed. Monero adopted Bulletproofs in 2018 and cut
its transaction sizes by about 80%.

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

KZG needs a trusted setup to bind a prover to a low-degree polynomial.
Ben-Sasson, Bentov, Horesh and Riabzev did it with hashes alone. The
prover Merkle-commits to a polynomial's values on a domain much larger
than its degree, a Reed-Solomon codeword, and FRI lets the verifier check,
with logarithmically many queries, that the committed values are close to
such a codeword. The key step halves the problem. Split :math:`f` into its
even and odd parts, :math:`f(X) = f_e(X^2) + X f_o(X^2)`; both have half
the degree, and both can be recovered from the two values at :math:`x` and
:math:`-x`. A random :math:`\alpha` from the verifier combines them into

.. math::

   f'(x^2) = f_e(x^2) + \alpha f_o(x^2) = \frac{f(x) + f(-x)}{2} + \alpha\, \frac{f(x) - f(-x)}{2x},

a function of half the degree on a domain of half the size (squaring maps
:math:`x` and :math:`-x` to one point). If :math:`f` has low degree, so
does :math:`f'`; if :math:`f` is far from low degree, a random
:math:`\alpha` keeps :math:`f'` far with high probability. After
:math:`\log_2 d` folds an honest codeword has become a constant. The prover
commits to each layer with a Merkle tree, and the verifier checks, along a
few random paths, that each layer is the fold of the one before. FRI is the
low-degree test of STARKs, Plonky2, RISC Zero and SP1.

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

The same authors used FRI to build scalable, transparent arguments of
knowledge: proofs that need no trusted setup, rely only on hash functions
(so no known quantum attack applies), and grow polylogarithmically with the
computation. The computation is recorded as an execution trace, one value
per step, interpolated as a polynomial :math:`f` with :math:`f(g^i)` the
value at step :math:`i` over a subgroup :math:`\langle g\rangle`. Each rule
of the computation is a polynomial in shifted copies of :math:`f`; for the
Fibonacci recurrence, :math:`f(g^2 X) - f(gX) - f(X)` is zero at
:math:`X = g^i` exactly when step :math:`i + 2` was computed correctly. As
in a QAP, being zero at all those points is the same as being divisible by
the polynomial with those roots, so the trace is correct exactly when

.. math::

   \frac{f(g^2 X) - f(gX) - f(X)}{\prod_{i=0}^{T-3} (X - g^i)} \quad \text{is a polynomial}

for a trace of length :math:`T`. If any step is wrong the quotient is not
a polynomial, and its values on a large domain are far from every
low-degree codeword. The prover therefore commits to a low-degree
extension of the trace, and proves with FRI that a random combination of
all the quotients has low degree. StarkWare's StarkEx and StarkNet were
built on this design.

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

Groth16 needs a new ceremony for every circuit, because its setup encodes
the circuit itself. Gabizon, Williamson and Ciobotaru removed that by
moving the circuit out of the setup. Every gate has the same form,
:math:`q_L a + q_R b + q_O c + q_M ab + q_C = 0`, with the selectors
:math:`q` choosing addition, multiplication or a constant, and the wiring
becomes a separate check: wires that carry the same variable must hold the
same value. Number every wire slot, and let the permutation :math:`\sigma`
send each slot to the next slot carrying the same variable. The values are
consistent exactly when they are unchanged by :math:`\sigma`, that is, when
the multisets :math:`\{(w, \mathrm{id})\}` and :math:`\{(w, \sigma)\}` of
(value, slot) pairs coincide. With random :math:`\beta, \gamma` from the
verifier, that is tested by

.. math::

   \prod_{\text{wires}} (w + \beta\, \mathrm{id} + \gamma) = \prod_{\text{wires}} (w + \beta\, \sigma + \gamma).

Both sides are polynomials in :math:`\beta` and :math:`\gamma` that are
identical exactly when the multisets are, so by Schwartz-Zippel the
equation holds at a random point with high probability only if the wiring
is respected. The running product becomes a committed polynomial, and
gates, copies and boundary conditions combine into one quotient checked at
a random point with KZG. Since the circuit enters only through committed
polynomials, the setup is *universal*: one powers of tau serves every
circuit up to a given size. Aztec, zkSync, Scroll and Halo 2 descend from
PLONK.

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

A proof that verifies the previous proof, at every block, would let
anyone check a whole chain from one short proof. That requires
verification cheap enough to run inside a circuit. Inner-product arguments
such as Bulletproofs need no setup, but their verifier is not cheap: after
the folding rounds it must compute the folded generator
:math:`G_\text{final}`, a multi-exponentiation as long as the vector.

Bowe, Grigg and Hopwood observed that this expensive value has structure.
The exponent of each original generator in :math:`G_\text{final}` is a
coefficient of

.. math::

   g(X) = \prod_{j=1}^{k} \left(1 + c_j X^{2^{k-j}}\right),

built from the :math:`k` round challenges, so :math:`G_\text{final}` is just
a commitment to :math:`g`. Computing the commitment takes linear time, but
*evaluating* :math:`g` takes only :math:`O(\log n)`. The verifier
therefore skips the expensive step and keeps :math:`G_\text{final}` as an
unchecked claim, an accumulator. Two such claims merge into one by opening
a random combination of them at a random point, which needs only cheap
evaluations of each :math:`g` and leaves a single new deferred claim. A
chain of proofs thus carries one accumulator forward, and whoever finally
needs certainty pays the linear cost once. Zcash's Orchard pool (2022)
runs on Halo 2.

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
