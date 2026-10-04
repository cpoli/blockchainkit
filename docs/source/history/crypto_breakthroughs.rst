Breakthroughs in Cryptography
=============================

.. include:: /_generated/nav/crypto.rst

Every later idea on these pages rests on cryptography: a way to agree on a
secret in public, to prove who authorized a message, and to commit to data
without revealing it. This chronology traces the ideas behind
:mod:`blockchainkit.crypto`, from the one-time pad to Schnorr multi-signatures.
Each entry has its own experiment in the :doc:`gallery </api/gallery/crypto/index>`.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

1917–1949 — The one-time pad and perfect secrecy
------------------------------------------------

**In plain language.** Add a random key, as long as the message, to the message
itself. Without the key, every possible message of that length is equally
believable. This is the only cipher proven unbreakable, and it is impractical for
exactly the reason that makes it work: the key is as long as everything you send.

**Reading the experiment.** XOR (exclusive or) adds bits without carrying; doing
it twice with the same key returns the original. For one ciphertext the
experiment finds a different key for each candidate message, then reuses a key
and shows the pad cancelling out.

Gilbert Vernam built a teleprinter in 1917 that combined each character of the
message with a character of a key tape. Joseph Mauborgne added the rule that the
tape must be random and never reused. Claude Shannon's 1949 information theory of
secrecy proved the result: with a uniformly random key at least as long as the
message, used once, the ciphertext is statistically independent of the plaintext.

.. math::

   c = m \oplus k, \qquad m = c \oplus k, \qquad
   \Pr[M = m \mid C = c] = \Pr[M = m].

Reusing the key leaks :math:`c_1 \oplus c_2 = m_1 \oplus m_2`. Soviet reuse of
one-time pads let the US Venona project read thousands of messages. Shannon's
theorem also says every perfectly secret cipher needs this much key: the key
distribution problem that public-key cryptography would solve.

**Implementation:** :func:`blockchainkit.crypto.systems.one_time_pad.one_time_pad`
refuses a key of the wrong length; :func:`blockchainkit.crypto.systems.one_time_pad.xor_bytes`
is the underlying operation.

**Experiment:** the gallery example shows that one ciphertext fits every plaintext,
that ciphertext bytes are uniform, and how a reused pad leaks.

*References:* G. S. Vernam, *Cipher Printing Telegraph Systems for Secret Wire and
Radio Telegraphic Communications*, Journal of the American Institute of
Electrical Engineers 45, 109–115 (1926). C. E. Shannon, *Communication Theory of
Secrecy Systems*, Bell System Technical Journal 28(4), 656–715 (1949). `DOI
<https://doi.org/10.1002/j.1538-7305.1949.tb00928.x>`__.

.. minigallery:: ../../examples/crypto/one_time_pad/plot_01_one_time_pad.py


1971 — Baby-step giant-step: square-root discrete logs
------------------------------------------------------

**In plain language.** Finding the secret exponent behind a public key by trying
every possibility takes as many steps as the group has elements. A clever
trade of memory for time needs only about the square root of that.

**Reading the experiment.** n is the group order. The algorithm stores m ≈ √n
"baby steps" and then takes up to m "giant steps"; the plot compares its work with
2√n and with n.

Daniel Shanks described the method while studying class numbers of quadratic
fields. Write the unknown exponent as :math:`x = im + j` with
:math:`m = \lceil\sqrt n\,\rceil`. Store :math:`g^j` for every :math:`j < m`,
then compute :math:`h\,g^{-im}` for :math:`i = 0, 1, \dots` until it appears in
the table:

.. math::

   g^{x} = h \iff g^{j} = h\,(g^{-m})^{i}, \qquad
   \text{cost} \approx 2\sqrt{n}.

Generic algorithms cannot do fundamentally better: Shoup later proved that any
algorithm that only uses the group operations needs about :math:`\sqrt n` steps.
That is why a 256-bit elliptic-curve group gives about 128-bit security.

**Implementation:** :func:`blockchainkit.crypto.systems.discrete_log.baby_step_giant_step`
returns the exponent and the number of table multiplications.

**Experiment:** the gallery example measures the work across safe-prime groups and
compares it with :math:`2\sqrt n`.

*References:* D. Shanks, *Class Number, a Theory of Factorization, and Genera*,
Proceedings of Symposia in Pure Mathematics 20, American Mathematical Society,
415–440 (1971).

.. minigallery:: ../../examples/crypto/discrete_log/plot_01_baby_step_giant_step.py


1974–1978 — Merkle's puzzles: key agreement in public
-----------------------------------------------------

**In plain language.** Alice publishes many small locked boxes, each holding a
key. Bob picks one at random and spends a little effort to open it, then tells
Alice which one he opened. An eavesdropper does not know which box Bob chose and
must open many of them.

**Reading the experiment.** Each puzzle hides an identifier and a session key
under a weak key of a few bits. Bob's work is one puzzle; the eavesdropper's work
grows with the number of puzzles.

As an undergraduate in 1974, Ralph Merkle proposed the first scheme for two
parties to agree on a secret over a public channel. The idea was hard to publish:
his paper appeared in 1978, after Diffie and Hellman's. With :math:`N` puzzles of
difficulty :math:`N`, Alice and Bob each work about :math:`N`, while an
eavesdropper needs about :math:`N^2/2`:

.. math::

   W_{\text{honest}} = O(N), \qquad W_{\text{attacker}} = O(N^2).

The gap is only quadratic, so it is not practical security; Diffie and Hellman's
exponential gap replaced it. But the puzzles showed public key exchange was
possible at all, and the same quadratic barrier was later shown to be the best any
scheme built only from a random function can achieve.

**Implementation:** :func:`blockchainkit.crypto.systems.puzzles.merkle_puzzles`
creates the puzzles and Alice's table; :func:`blockchainkit.crypto.systems.puzzles.solve_puzzle`
opens one by brute force.

**Experiment:** the gallery example runs an exchange, plays the eavesdropper, and
plots honest work against attack work.

*References:* R. C. Merkle, *Secure Communications over Insecure Channels*,
Communications of the ACM 21(4), 294–299 (1978). `DOI
<https://doi.org/10.1145/359460.359473>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_01_merkle_puzzles.py


1976 — Agreeing on a secret over a public channel
-------------------------------------------------

**In plain language.** Two people publicly exchange specially calculated numbers, then
each uses their own secret to arrive at the same value. An eavesdropper sees the
exchange but should find the secret difficult to recover. This alone does not identify
who is at the other end.

**Reading the experiment.** Here a and b are private numbers; A and B are the public
results. The shared settings are g and a prime p. “mod p” means keep the remainder after
dividing by p. The example returns True because both calculations agree.

Sharing an encryption key used to require a secret channel in advance.
Diffie and Hellman's public-key framework changed the question: could two
people perform different private computations that reach the same secret
from publicly exchanged information? Their construction uses exponentiation
in a finite group.

.. math::

   A=g^a\bmod p,\qquad B=g^b\bmod p,\qquad
   B^a=A^b=g^{ab}\bmod p.

An observer sees :math:`g,p,A,B`, but recovering a private exponent requires
solving a discrete logarithm in the chosen group. The shared element still
needs a key derivation function before use as an encryption key.

**Implementation:** :class:`blockchainkit.crypto.systems.asymmetric.DHGroup` validates
the prime-order subgroup and peer elements.

.. doctest::

   >>> group = bk.crypto.DHGroup()
   >>> group.shared(group.public(7), 3) == group.shared(group.public(3), 7)
   True

**Experiment:** :doc:`/api/gallery/crypto/public_keys/plot_02_diffie_hellman` includes a key-substitution
attack. Agreement on a secret is not authentication of the other person.

*References:* W. Diffie and M. E. Hellman, *New Directions in Cryptography*,
IEEE Transactions on Information Theory 22(6), 644–654 (1976). `DOI
<https://doi.org/10.1109/TIT.1976.1055638>`__; `author's copy
<https://ee.stanford.edu/~hellman/publications/24.pdf>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_02_diffie_hellman.py


1978 — RSA and the public trapdoor
----------------------------------

**In plain language.** RSA separates a public operation from a private operation that
reverses it. Think of a publicly usable lock with a private unlocking key, while
remembering that the bare arithmetic here needs additional protections for practical
use.

**Reading the experiment.** The message m becomes ciphertext c. The public key uses n
and e; the private operation uses d. The example turns 65 into 2790 and then back into
65. The primes p and q are used to construct the keys.

Rivest, Shamir, and Adleman gave a concrete public-key construction based on
modular exponentiation with a composite modulus. Choose distinct
primes :math:`p,q`, publish :math:`n=pq` and an exponent :math:`e`, and retain
the inverse exponent :math:`d`.

.. math::

   ed\equiv1\pmod{(p-1)(q-1)},\qquad
   c=m^e\bmod n,\qquad m=c^d\bmod n.

**Implementation:** :func:`blockchainkit.crypto.systems.asymmetric.rsa_keypair`
exposes the arithmetic, including the familiar :math:`61\times53` example.
The code accepts only small factors for inspectable experiments.

.. doctest::

   >>> key = bk.crypto.rsa_keypair()
   >>> key.encrypt(65), key.decrypt(2790)
   (2790, 65)

**Experiment:** :doc:`/api/gallery/crypto/public_keys/plot_03_rsa` demonstrates multiplicative
malleability: altering a ciphertext can predictably alter its plaintext.
Textbook RSA is deterministic and unpadded; this package does not present it
as a secure encryption or signature interface. Public-key cryptography needs
a complete encoding and protocol, not just an impressive formula.

*References:* R. L. Rivest, A. Shamir, and L. Adleman, *A Method for Obtaining
Digital Signatures and Public-Key Cryptosystems*, Communications of the ACM
21(2), 120–126 (1978). `DOI <https://doi.org/10.1145/359340.359342>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_03_rsa.py


1978 — Pohlig–Hellman: why the group order needs a large prime factor
---------------------------------------------------------------------

**In plain language.** A discrete-log problem in a big group can secretly be many
small problems glued together. If the group's size factors into small primes,
each small problem is easy, and so is the whole.

**Reading the experiment.** The order of a group is how many elements it has. The
experiment compares a group whose order is 2²·3⁴·5² with a group of prime order
of similar size.

Pohlig and Hellman showed that if :math:`n = \prod p_i^{e_i}`, a logarithm modulo
:math:`n` follows from logarithms modulo each :math:`p_i^{e_i}`, recombined with the
Chinese Remainder Theorem. Each of those is computed one base-:math:`p_i` digit at
a time in a subgroup of order :math:`p_i`:

.. math::

   x \bmod p_i^{e_i}\ \text{from}\ \bigl(h^{n/p_i^{e_i}}\bigr), \qquad
   \text{cost} \approx \sum_i e_i \sqrt{p_i}.

The cost depends on the largest prime factor of :math:`n`, not on :math:`n`. This is
why Diffie–Hellman and Schnorr run in a subgroup of large prime order, and why
:data:`blockchainkit.crypto.systems.asymmetric.TEACHING_GROUP` uses a safe prime
:math:`p = 2q + 1`.

**Implementation:** :func:`blockchainkit.crypto.systems.discrete_log.pohlig_hellman`
factors the order by trial division, solves each prime-power part with
baby-step giant-step, and combines the answers.

**Experiment:** the gallery example breaks a smooth-order group with a fraction of
the work, and shows no gain in a prime-order group.

*References:* S. Pohlig and M. Hellman, *An Improved Algorithm for Computing
Logarithms over GF(p) and Its Cryptographic Significance*, IEEE Transactions on
Information Theory 24(1), 106–110 (1978). `DOI
<https://doi.org/10.1109/TIT.1978.1055817>`__.

.. minigallery:: ../../examples/crypto/discrete_log/plot_02_pohlig_hellman.py


1979 — Shamir's threshold secret sharing
----------------------------------------

**In plain language.** Split a secret among five people so any three can recover it,
while one or two learn nothing about its value under the scheme’s assumptions. Each
person holds a share, rather than a readable third of the secret.

**Reading the experiment.** The threshold t is the number of shares needed. The secret s
is the value of a polynomial f at zero. A polynomial is a sum of powers of x; shares are
points on it. Enough points determine the value at zero, using arithmetic modulo the
prime p.

Storing a secret in one place creates a single point of loss or compromise.
Shamir's scheme distributes it so that a threshold of participants can
recover it together. Choose a random degree-at-most-:math:`t-1`
polynomial over a prime field with secret constant term :math:`s`.

.. math::

   f(x)=s+a_1x+\cdots+a_{t-1}x^{t-1}\pmod p,
   \qquad s=f(0).

Any :math:`t` distinct evaluations determine :math:`f(0)` by Lagrange
interpolation. With uniform coefficients, fewer than :math:`t` shares are
compatible with every possible secret; this is an information-theoretic
property rather than a computational hardness assumption.

**Implementation:** :func:`blockchainkit.crypto.systems.sharing.split_secret` and
:func:`blockchainkit.crypto.systems.sharing.recover_secret` use integer field arithmetic.

**Experiment:** :doc:`/api/gallery/crypto/sharing/plot_01_secret_sharing` reconstructs from every
three-of-five subset and draws several polynomials compatible with two shares.
Plain sharing does not detect forged shares. Nor does reconstructing a key
implement a threshold signing protocol: those are separate capabilities.

*References:* A. Shamir, *How to Share a Secret*, Communications of the ACM
22(11), 612–613 (1979). `DOI <https://doi.org/10.1145/359168.359176>`__.

.. minigallery:: ../../examples/crypto/sharing/plot_01_secret_sharing.py


1979 — Lamport's one-time signatures from a hash
------------------------------------------------

**In plain language.** Publish the fingerprints of 512 secret strings. To sign,
reveal one secret from each pair, chosen by the bits of the message's fingerprint.
Anyone can check that each revealed string has the published fingerprint.

**Reading the experiment.** A preimage is an input that hashes to a given output.
Each signature reveals 256 of the 512 secrets. The plot shows how many new
messages become forgeable as one key signs more and more messages.

Leslie Lamport showed that a one-way function alone suffices for digital
signatures. For each bit :math:`b_i` of :math:`H(m)`, the signer reveals
:math:`x_{i,b_i}`, and the verifier checks :math:`H(x_{i,b_i}) = y_{i,b_i}`:

.. math::

   \text{public key } y_{i,b} = H(x_{i,b}), \qquad
   \sigma = (x_{1,b_1}, \dots, x_{256,b_{256}}).

After :math:`k` signatures, a random message can be forged with probability about
:math:`(1 - 2^{-k})^{256}`, so a key must sign once. Merkle's trees, invented the
same year, authenticate many one-time keys under one root. Because they rely only
on hashing, these signatures resist quantum computers: the standardized SPHINCS+
(SLH-DSA) descends from them.

**Implementation:** :func:`blockchainkit.crypto.systems.lamport.lamport_keypair`,
:func:`blockchainkit.crypto.systems.lamport.lamport_sign`, and
:func:`blockchainkit.crypto.systems.lamport.lamport_verify`.

**Experiment:** the gallery example signs, verifies, and measures how quickly key
reuse makes forgeries possible.

*References:* L. Lamport, *Constructing Digital Signatures from a One Way
Function*, Technical Report CSL-98, SRI International (1979).

.. minigallery:: ../../examples/crypto/hash_signatures/plot_01_lamport_signatures.py


1979 — Yuval's birthday attack
------------------------------

**In plain language.** Finding two people with the same birthday in a room is much
easier than finding someone with *your* birthday. Finding two documents with the
same fingerprint is likewise much easier than matching a given fingerprint.

**Reading the experiment.** The hash is cut to n bits so collisions are reachable.
The plot compares the trials needed with :math:`\sqrt{2^n}` and with :math:`2^n`.

Gideon Yuval showed how to exploit this against signatures: prepare many harmless
and many harmful variants of a contract until one of each shares a hash, have the
victim sign the harmless one, and the signature also fits the harmful one. Among
:math:`q` random :math:`n`-bit values a repeat appears with probability about
:math:`q^2/2^{n+1}`:

.. math::

   \Pr[\text{collision}] \approx 1 - e^{-q^2 / 2^{n+1}}, \qquad
   E[q] \approx \sqrt{\tfrac{\pi}{2}\, 2^{n}}.

So an :math:`n`-bit hash gives only :math:`n/2` bits of collision resistance. SHA-256's
256-bit output is chosen for 128-bit collision security.

**Implementation:** :func:`blockchainkit.crypto.systems.hashing.find_collision`
searches truncated SHA-256; :func:`blockchainkit.crypto.systems.hashing.truncated_hash`
does the truncation.

**Experiment:** the gallery example finds collisions from 8 to 32 bits and compares
the cost with the birthday bound.

*References:* G. Yuval, *How to Swindle Rabin*, Cryptologia 3(3), 187–191
(1979). `DOI <https://doi.org/10.1080/0161-117991854025>`__.

.. minigallery:: ../../examples/crypto/hashing/plot_01_birthday_attack.py


1981 — Coin flipping by telephone: commitments
----------------------------------------------

**In plain language.** Seal your guess in an envelope, let the other person flip
the coin, then open the envelope. Neither of you can cheat: you cannot change the
guess, and they cannot read it before flipping.

**Reading the experiment.** A commitment is the sealed envelope; the salt is a
random value that keeps it from being guessed. Opening means revealing the
message and salt so anyone can recompute the commitment.

Manuel Blum asked how two people who do not trust each other can flip a fair coin
over the telephone. The answer is a commitment scheme: *binding*, so the committer
cannot open it to a different value, and *hiding*, so it reveals nothing before
opening. With a hash:

.. math::

   C = H(\text{domain} \,\|\, |r| \,\|\, r \,\|\, m), \qquad
   \text{open}: (m, r) \ \text{with}\ H(\dots) = C.

Binding rests on collision resistance; hiding rests on the random salt :math:`r`.
Commitments became a basic building block: a Schnorr prover commits to
:math:`R` before seeing a challenge, and a block header commits to its
transactions.

**Implementation:** :func:`blockchainkit.crypto.systems.commitments.commit` adds
domain separation and explicit salt framing;
:func:`blockchainkit.crypto.systems.commitments.verify_commitment` compares in
constant time.

**Experiment:** the gallery example plays a coin toss, shows that an unsalted hash
of a guessable value hides nothing, and checks fairness over a thousand flips.

*References:* M. Blum, *Coin Flipping by Telephone: A Protocol for Solving
Impossible Problems*, CRYPTO '81, 11–15 (1981); reprinted in ACM SIGACT News 15(1),
23–27 (1983). `DOI <https://doi.org/10.1145/1008908.1008911>`__.

.. minigallery:: ../../examples/crypto/commitments/plot_01_coin_flipping.py


1982–1983 — Chaum's blind signatures and private payments
---------------------------------------------------------

**In plain language.** Imagine asking someone to stamp an envelope without seeing the
message inside, then removing the envelope while retaining a checkable stamp. Blind
signatures provide a mathematical version of this idea.

**Reading the experiment.** The original message is m and the obscured message is m
prime. The random factor r hides it during signing; its inverse removes that factor
afterward. The final s can be checked as a signature on the original message.

A signer may need to authorize a token without learning the token it signs.
Chaum introduced blind signatures at CRYPTO '82, with proceedings published
in 1983. RSA's algebra lets a requester obscure a message with an
invertible random factor and remove that factor after signing.

.. math::

   m'=mr^e\bmod n,\qquad
   s'=(m')^d\bmod n,\qquad
   s=s'r^{-1}\bmod n.

Then :math:`s^e=m\pmod n`. The requester obtains an ordinary signature while
the signer processes the blinded value.

**Implementation:** :func:`blockchainkit.crypto.systems.asymmetric.rsa_blind` and
:func:`blockchainkit.crypto.systems.asymmetric.rsa_unblind` expose this identity.

**Experiment:** :doc:`/api/gallery/crypto/blind_signatures/plot_01_blind_signatures` follows each value
through the exchange. These bare integer operations are not a complete
anonymous cash system: issuance policy, message encoding, and a mechanism to
detect repeated spending remain necessary. Privacy and decentralized agreement
are different design questions.

*References:* D. Chaum, *Blind Signatures for Untraceable Payments*, CRYPTO
'82, 199–203 (proceedings 1983). `DOI
<https://doi.org/10.1007/978-1-4757-0602-4_18>`__.

.. minigallery:: ../../examples/crypto/blind_signatures/plot_01_blind_signatures.py


1985 — Elliptic curves as a cryptographic group
-----------------------------------------------

**In plain language.** Public keys can be built by repeatedly combining points using a
special addition rule. Going forward is easy; recovering how many steps were taken
should be difficult for a carefully chosen large system.

**Reading the experiment.** G is a starting point, x is a secret step count, and Q is
the resulting public point. In Q=xG, multiplication means repeated group addition. The
coordinates in the curve equation wrap modulo p, so the plot shows separate points, not
a continuous curve.

Miller proposed elliptic curves for public-key cryptography at CRYPTO '85;
Koblitz independently developed elliptic-curve cryptosystems. The relevant object is a finite group of curve points, not a
smooth curve drawn over the real numbers.

.. math::

   y^2=x^3+ax+b\pmod p,\qquad Q=xG.

Repeated addition efficiently computes :math:`Q`. Recovering :math:`x` from
:math:`G,Q` is an elliptic-curve discrete-log problem. Group and parameter
selection matter; arbitrary curves do not inherit security merely by name.

**Implementation:** :class:`blockchainkit.crypto.systems.curves.Curve`,
:func:`blockchainkit.crypto.systems.curves.add`, and
:func:`blockchainkit.crypto.systems.curves.multiply` implement the group law,
including infinity, inverse points, and doubling. ``TOY_CURVE`` has 19 points;
``SECP256K1`` supplies a larger, established parameter set.

**Experiment:** :doc:`/api/gallery/crypto/curves/plot_01_elliptic_curves` plots the tiny group and
recovers a private scalar by enumeration. The same API handles secp256k1,
but this readable Python implementation is variable-time and not hardened.

*References:* V. S. Miller, *Use of Elliptic Curves in Cryptography*, CRYPTO
'85, LNCS 218, 417–426 (proceedings 1986). `DOI
<https://doi.org/10.1007/3-540-39799-X_31>`__. N. Koblitz, *Elliptic Curve
Cryptosystems*, Mathematics of Computation 48(177), 203–209 (1987). `DOI
<https://doi.org/10.1090/S0025-5718-1987-0866109-5>`__.

.. minigallery:: ../../examples/crypto/curves/plot_01_elliptic_curves.py


1985 — Zero knowledge: proofs that reveal nothing
-------------------------------------------------

**In plain language.** A person may prove they know a secret without handing over the
secret. The important distinction is between responding live to an unpredictable
challenge and merely displaying a record of a conversation.

**Reading the experiment.** A transcript is that conversation record: commitment R,
challenge c, and response s. G is a starting curve point and Q is the public key. A
record constructed after choosing the challenge need not prove that its creator knew the
secret.

Goldwasser, Micali, and Rackoff formalized a striking possibility: an interaction
can convince a verifier while revealing no additional knowledge, in a precise
simulation-based sense. A proof is *zero-knowledge* if a simulator, without the
secret, can produce transcripts indistinguishable from real ones: then the real
ones cannot have taught the verifier anything.

Blockchainkit illustrates the idea with Schnorr's later identification protocol.
An honest-verifier transcript can be simulated by choosing :math:`c,s` first
and computing :math:`R=sG-cQ`:

.. math::

   R = kG,\quad c \xleftarrow{\$} \mathbb{Z}_n,\quad s = k + cx;
   \qquad \text{simulator: } R = sG - cQ.

An actual prover must commit to :math:`R` before receiving an unpredictable
:math:`c`. The order is crucial: it is the only thing separating a proof from a
simulation.

**Implementation:** :func:`blockchainkit.crypto.systems.signatures.verify_transcript`
checks the group equation; :func:`blockchainkit.crypto.systems.signatures.simulate_transcript`
is the simulator.

**Experiment:** :doc:`/api/gallery/crypto/signatures/plot_01_zero_knowledge` runs an honest
proof and a simulated one, and draws who sends what in which order. It explains
honest-verifier zero-knowledge intuition; it does not implement a general proof
system.

*References:* S. Goldwasser, S. Micali, and C. Rackoff, *The Knowledge
Complexity of Interactive Proof-Systems*, STOC '85, 291–304 (1985). `DOI
<https://doi.org/10.1145/22145.22178>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_01_zero_knowledge.py


1986 — The Fiat–Shamir heuristic: from interaction to signatures
----------------------------------------------------------------

**In plain language.** Instead of waiting for a verifier to pick a random challenge,
the prover computes it as a fingerprint of everything said so far. The proof no
longer needs a live conversation, and binding the message into the fingerprint
turns it into a signature.

**Reading the experiment.** :math:`H` is a hash; :math:`c = H(R, Q, m)` replaces the
verifier's random choice. A forger who picks :math:`c` first must then hope the hash
of the resulting :math:`R` equals it.

Fiat and Shamir proposed replacing the verifier's random challenge with a hash of
the transcript so far:

.. math::

   c = H(R, Q, m), \qquad \sigma = (R,\ s = k + cx).

If :math:`H` behaves like a random function, the prover cannot choose :math:`R` after
knowing :math:`c`, so the simulator's trick no longer works. Pointcheval and Stern
later proved such signatures secure in the random-oracle model. Schnorr signatures,
EdDSA, and most zero-knowledge proof systems used by blockchains (SNARKs, STARKs)
rely on this transform; bugs in what goes into the hash have broken real systems.

**Implementation:** :func:`blockchainkit.crypto.systems.signatures.challenge`
hashes the message, public key, commitment, and curve domain.

**Experiment:** :doc:`/api/gallery/crypto/signatures/plot_02_fiat_shamir` shows the
challenge changing with the message, a simulated forgery failing, and on a
19-point curve, forgeries succeeding about one time in 19: the forger must guess
the hash.

*References:* A. Fiat and A. Shamir, *How To Prove Yourself: Practical Solutions
to Identification and Signature Problems*, CRYPTO '86, LNCS 263, 186–194
(proceedings 1987). `DOI <https://doi.org/10.1007/3-540-47721-7_12>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_02_fiat_shamir.py


1987 — Feldman's verifiable secret sharing
------------------------------------------

**In plain language.** In plain secret sharing, everyone must trust the person who
hands out the shares. Feldman's version lets each share holder check privately
that their share is consistent with everyone else's.

**Reading the experiment.** The dealer publishes a commitment :math:`g^{a_j}` to each
polynomial coefficient. A share is :math:`(x, f(x))`; it passes when it lies on the
committed polynomial.

Paul Feldman made Shamir's scheme verifiable without interaction. The dealer
publishes :math:`C_j = g^{a_j}`; share holder :math:`i` checks

.. math::

   g^{f(i)} = \prod_{j=0}^{t-1} C_j^{\,i^{j}} \pmod p.

Because exponentiation turns the polynomial's sum into a product, the check holds
exactly for points on the committed polynomial. The price is that
:math:`C_0 = g^{s}` is public, so the secret is only computationally hidden.
Verifiable sharing is the basis of distributed key generation, which threshold
wallets use to create a key no single party ever holds.

**Implementation:** :func:`blockchainkit.crypto.systems.sharing.feldman_split` and
:func:`blockchainkit.crypto.systems.sharing.feldman_verify`, over
:data:`blockchainkit.crypto.systems.asymmetric.TEACHING_GROUP`.

**Experiment:** the gallery example verifies honest shares, recovers the secret from
every threshold subset, and catches a corrupted share.

*References:* P. Feldman, *A Practical Scheme for Non-interactive Verifiable Secret
Sharing*, 28th Symposium on Foundations of Computer Science (FOCS), 427–438
(1987). `DOI <https://doi.org/10.1109/SFCS.1987.4>`__.

.. minigallery:: ../../examples/crypto/sharing/plot_02_feldman_vss.py


1989 — The Merkle–Damgård construction and length extension
-----------------------------------------------------------

**In plain language.** A hash function chews through a long message one block at
a time, passing a fixed-size summary from block to block. The final summary is the
fingerprint. Anyone who has it can keep chewing.

**Reading the experiment.** The compression function mixes one 64-byte block into
eight 32-bit state words. The padding ends with the message length. The attack
continues hashing from a published digest.

Ralph Merkle and Ivan Damgård independently showed at CRYPTO '89 that a
collision-resistant compression function :math:`f` yields a collision-resistant hash
for messages of any length, provided the padding encodes the length:

.. math::

   h_0 = IV, \qquad h_i = f(h_{i-1}, m_i), \qquad H(m) = h_\ell.

MD5, SHA-1 and SHA-256 all follow this design. Its side effect: since
:math:`H(m)` *is* the chaining state, anyone can compute
:math:`H(m \,\|\, \text{pad} \,\|\, s)` from :math:`H(m)` and :math:`|m|` alone. A
"MAC" computed as :math:`H(k \,\|\, m)` is therefore forgeable.

**Implementation:** :func:`blockchainkit.crypto.systems.merkle_damgard.merkle_damgard_sha256`
reimplements SHA-256 block by block (checked against the standard library);
:func:`blockchainkit.crypto.systems.merkle_damgard.length_extension` performs the
attack.

**Experiment:** the gallery example hashes block by block and forges a naive MAC
without its key.

*References:* R. C. Merkle, *One Way Hash Functions and DES*, CRYPTO '89, LNCS 435,
428–446 (1990). `DOI <https://doi.org/10.1007/0-387-34805-0_40>`__. I. B. Damgård,
*A Design Principle for Hash Functions*, CRYPTO '89, LNCS 435, 416–427 (1990).
`DOI <https://doi.org/10.1007/0-387-34805-0_39>`__.

.. minigallery:: ../../examples/crypto/hashing/plot_02_merkle_damgard.py


1989–1991 — Schnorr identification and compact signatures
---------------------------------------------------------

**In plain language.** A short signature lets others check that a particular key
authorized a message, and nobody else's. Its one-time secret must be fresh: the
2010–2013 entry below shows what happens when it is not.

**Reading the experiment.** Here x is the private key, Q its public key, k the secret
signing nonce, R a temporary public point, c a challenge, and s the response. G is the
starting point and n is its group order (the number of points in its cycle). The
experiment checks the verification equation by hand and tampers with each part.

Schnorr's identification and signature work made discrete-log proofs compact
and efficient. In additive notation, a prover with secret
:math:`x` commits using fresh :math:`k`, then responds to challenge :math:`c`:

.. math::

   R=kG,\qquad s=k+cx\pmod n,\qquad sG=R+cQ.

Applying the Fiat–Shamir transform with :math:`c = H(R, Q, m)` turns the
identification protocol into a signature :math:`(R, s)`. Schnorr signatures are
linear: when keys add, signatures add, which later enabled multi-signatures (see
the 2018 entry). A patent kept them out of standards until it expired in 2008;
Bitcoin adopted them in 2021 as BIP-340.

**Implementation:** :func:`blockchainkit.crypto.systems.signatures.sign`,
:func:`blockchainkit.crypto.systems.signatures.verify`, and
:func:`blockchainkit.crypto.systems.signatures.recover_reused_nonce_key` use a
domain-separated teaching scheme over a prime-order elliptic-curve subgroup.
The historical paper uses multiplicative groups; this is an additive adaptation.

**Experiment:** :doc:`/api/gallery/crypto/signatures/plot_03_schnorr_signatures` signs a
payment, checks :math:`sG = R + cQ` step by step, and shows that changing the
message, key, :math:`R`, or :math:`s` breaks verification. The scheme is not
BIP-340.

*References:* C. P. Schnorr, *Efficient Signature Generation by Smart Cards*,
Journal of Cryptology 4, 161–174 (1991); following the CRYPTO '89 work. `DOI
<https://doi.org/10.1007/BF00196725>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_03_schnorr_signatures.py


1991 — Pedersen commitments: perfectly hiding and additive
----------------------------------------------------------

**In plain language.** A commitment that hides its contents perfectly, even from
an attacker with unlimited computing power, and where adding sealed envelopes adds
the amounts inside them.

**Reading the experiment.** :math:`g` and :math:`h` are two generators of the same
prime-order group; :math:`r` is a random blinding factor. Multiplying commitments
adds both the values and the blinding factors.

Torben Pedersen introduced the commitment

.. math::

   C(v, r) = g^{v} h^{r} \bmod p, \qquad C(a, r)\,C(b, s) = C(a + b,\ r + s).

For any other value :math:`v'` there is a blinding :math:`r'` with the same :math:`C`, so
hiding is perfect. Opening to two values would reveal :math:`\log_g h`, so binding is
computational, which is why :math:`h` is derived by hashing. The additive property
lets anyone check that hidden inputs equal hidden outputs: the basis of
confidential transactions in Monero and Mimblewimble.

**Implementation:** :func:`blockchainkit.crypto.systems.commitments.pedersen_commit` and
:func:`blockchainkit.crypto.systems.commitments.pedersen_generators`.

**Experiment:** the gallery example balances hidden transaction amounts, opens one
commitment as three different values in a tiny group, and shows that commitments
look the same whatever the value.

*References:* T. P. Pedersen, *Non-Interactive and Information-Theoretic Secure
Verifiable Secret Sharing*, CRYPTO '91, LNCS 576, 129–140 (1992). `DOI
<https://doi.org/10.1007/3-540-46766-1_9>`__.

.. minigallery:: ../../examples/crypto/commitments/plot_02_pedersen.py


1996 — HMAC: keyed hashing done right
-------------------------------------

**In plain language.** To prove a message came from someone who knows a shared
key, mix the key into the hash twice, in a way that leaves an attacker nothing to
continue from.

**Reading the experiment.** ``ipad`` and ``opad`` are two fixed byte patterns that
derive an inner and an outer key. The experiment retries the length-extension
forgery against both MACs.

Bellare, Canetti and Krawczyk defined HMAC and proved it secure under assumptions
about the compression function:

.. math::

   \mathrm{HMAC}(k, m) = H\bigl((k \oplus opad) \,\|\, H((k \oplus ipad) \,\|\, m)\bigr).

The outer hash hides the inner chaining state, so length extension fails. HMAC
became RFC 2104 in 1997 and is everywhere: TLS, key derivation (HKDF), and the
deterministic nonces of RFC 6979.

**Implementation:** :func:`blockchainkit.crypto.systems.mac.hmac_sha256`, contrasted
with the broken :func:`blockchainkit.crypto.systems.mac.naive_mac`.

**Experiment:** the gallery example shows the forgery succeed against
:math:`H(k \,\|\, m)` and fail against HMAC.

*References:* M. Bellare, R. Canetti, and H. Krawczyk, *Keying Hash Functions for
Message Authentication*, CRYPTO '96, LNCS 1109, 1–15 (1996). `DOI
<https://doi.org/10.1007/3-540-68697-5_1>`__.

.. minigallery:: ../../examples/crypto/hashing/plot_03_hmac.py


2002 — SHA-256 as a standardized hash primitive
-----------------------------------------------

**In plain language.** Different programs need to calculate the same fingerprint for the
same data. A standardized hash gives them a shared rule and known examples against which
to check their implementations.

**Reading the experiment.** The displayed result is hexadecimal: two characters
represent each byte. Changing an input bit usually changes many output bits. A
scrambled-looking output does not, by itself, establish that a hash is secure.

NIST's FIPS 180-2 specified SHA-256 alongside other secure hash algorithms. Hashes became shared building blocks that independent systems
could implement and test against common vectors. A fixed-size output gives
a compact fingerprint; it does not encrypt the input.

**Implementation:** :func:`blockchainkit.crypto.systems.hashing.sha256` delegates to
Python's standard-library implementation;
:func:`blockchainkit.crypto.systems.merkle_damgard.merkle_damgard_sha256` is a
readable reimplementation (see the 1989 entry) that the tests check against it.

.. doctest::

   >>> bk.crypto.sha256(b"abc").hex()
   'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

**Experiment:** :doc:`/api/gallery/crypto/hashing/plot_04_sha256_avalanche` flips each
input bit and compares the changed output bits with a Binomial(256, 1/2)
distribution. This illustrates diffusion, not a proof of security. Earlier
milestones above use SHA-256 as a modern teaching primitive, not as a historical
implementation.

*References:* NIST, *Secure Hash Standard*, FIPS PUB 180-2 (2002). `Historical
standard record <https://csrc.nist.gov/pubs/fips/180-2/final>`__. This is cited
for historical context, not as the latest standards guidance.

.. minigallery:: ../../examples/crypto/hashing/plot_04_sha256_avalanche.py


2010–2013 — Nonce reuse in practice, and deterministic nonces
-------------------------------------------------------------

**In plain language.** A signature hides the private key behind a fresh random
number. If the same number is used twice, the key can be calculated. This happened
to a games console, and the fix was to stop needing randomness at all.

**Reading the experiment.** :math:`k` is the signing nonce; :math:`s_i` and
:math:`c_i` are the responses and challenges of two signatures. The deterministic
nonce is derived with HMAC from the private key and the message.

With :math:`s_i = k + c_i x`, two signatures sharing :math:`k` give

.. math::

   x = \frac{s_1 - s_2}{c_1 - c_2} \bmod n.

In December 2010 the fail0verflow team showed that Sony's PlayStation 3 signed
software with a constant ECDSA nonce, and recovered Sony's private key. Weak random
number generators in Android wallets led to Bitcoin thefts in 2013. Thomas Pornin's
RFC 6979 derives the nonce as an HMAC-based deterministic random bit generator
seeded with the private key and the message hash: no randomness needed, distinct
messages get distinct nonces, and the nonce is unpredictable without the key.

**Implementation:** :func:`blockchainkit.crypto.systems.signatures.recover_reused_nonce_key`
performs the extraction; :func:`blockchainkit.crypto.systems.signatures.deterministic_nonce`
implements RFC 6979 section 3.2 with SHA-256 and reproduces the RFC's test vectors.

**Experiment:** the gallery example recovers a key from a reused nonce and generates
deterministic nonces, checking one against the RFC.

*References:* fail0verflow (bushing, marcan, sven), *Console Hacking 2010: PS3 Epic
Fail*, 27th Chaos Communication Congress (2010). T. Pornin, *Deterministic Usage of
the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature
Algorithm (ECDSA)*, RFC 6979 (2013). `DOI <https://doi.org/10.17487/RFC6979>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_04_nonce_reuse.py


2018 — MuSig: Schnorr multi-signatures and the rogue-key attack
---------------------------------------------------------------

**In plain language.** Several people jointly sign so that the result looks like one
ordinary signature from one key. Done naively, the last person to announce a key
can make the joint key their own.

**Reading the experiment.** :math:`Q_i` are the signers' public keys and :math:`a_i`
their MuSig coefficients. The rogue key is chosen to cancel the honest key in a
plain sum.

Schnorr signatures are linear, so partial signatures for keys :math:`Q_i` add up to
a signature for :math:`\sum Q_i`. An attacker announcing
:math:`Q_{\text{rogue}} = xG - Q_{\text{honest}}` controls that sum alone. Maxwell,
Poelstra, Seurin and Wuille's MuSig weights every key by a hash of the whole list
:math:`L`:

.. math::

   a_i = H(L, Q_i), \qquad Q_{\text{agg}} = \sum_i a_i Q_i, \qquad
   s = \sum_i (k_i + c\, a_i x_i).

No participant can choose a key that cancels the others, because changing any key
changes every coefficient. Bitcoin's Taproot upgrade (2021) made such aggregate
spends indistinguishable from single-signer spends.

**Implementation:** :func:`blockchainkit.crypto.systems.multisig.musig_coefficients`,
:func:`blockchainkit.crypto.systems.multisig.aggregate_public_keys`, and
:func:`blockchainkit.crypto.systems.multisig.musig_sign`. As a teaching
simplification, signing runs every signer in one process; real MuSig first
exchanges nonce commitments.

**Experiment:** the gallery example mounts the rogue-key attack on naive aggregation,
shows MuSig stopping it, and verifies a three-party signature.

*References:* G. Maxwell, A. Poelstra, Y. Seurin, and P. Wuille, *Simple Schnorr
Multi-Signatures with Applications to Bitcoin*, Designs, Codes and Cryptography 87,
2139–2164 (2019); preprint IACR ePrint 2018/068. `DOI
<https://doi.org/10.1007/s10623-019-00608-x>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_05_musig.py
