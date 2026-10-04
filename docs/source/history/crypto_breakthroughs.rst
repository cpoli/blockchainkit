Breakthroughs in Cryptography
=============================

.. include:: /_generated/nav/crypto.rst

Every later idea on these pages rests on cryptography: a way to agree on a
secret in public, to prove who authorized a message, and to commit to data
without revealing it. This chronology traces the ideas behind
:mod:`blockchainkit.crypto`, from public-key exchange to Schnorr signatures.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

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

**Experiment:** :doc:`/api/gallery/crypto/public_keys/plot_01_public_keys` includes a key-substitution
attack. Agreement on a secret is not authentication of the other person.

*References:* W. Diffie and M. E. Hellman, *New Directions in Cryptography*,
IEEE Transactions on Information Theory 22(6), 644–654 (1976). `DOI
<https://doi.org/10.1109/TIT.1976.1055638>`__; `author's copy
<https://ee.stanford.edu/~hellman/publications/24.pdf>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_01_public_keys.py


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

**Experiment:** :doc:`/api/gallery/crypto/public_keys/plot_01_public_keys` demonstrates multiplicative
malleability: altering a ciphertext can predictably alter its plaintext.
Textbook RSA is deterministic and unpadded; this package does not present it
as a secure encryption or signature interface. Public-key cryptography needs
a complete encoding and protocol, not just an impressive formula.

*References:* R. L. Rivest, A. Shamir, and L. Adleman, *A Method for Obtaining
Digital Signatures and Public-Key Cryptosystems*, Communications of the ACM
21(2), 120–126 (1978). `DOI <https://doi.org/10.1145/359340.359342>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_01_public_keys.py


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


1985–1986 — Zero knowledge and turning interaction into a signature
-------------------------------------------------------------------

**In plain language.** A person may prove they know a secret without handing over the
secret. The important distinction is between responding live to an unpredictable
challenge and merely displaying a record of a conversation.

**Reading the experiment.** A transcript is that conversation record: commitment R,
challenge c, and response s. G is a starting curve point and Q is the public key. A
record constructed after choosing the challenge need not prove that its creator knew the
secret.

Goldwasser, Micali, and Rackoff formalized a striking possibility: an interaction
can convince a verifier while revealing no additional knowledge, in a precise
simulation-based sense. Fiat and Shamir then developed a way to replace
an interactive challenge with a hash-derived one.

Blockchainkit illustrates these ideas through a later Schnorr-style protocol.
An honest-verifier transcript can be simulated by choosing :math:`c,s` first
and computing :math:`R=sG-cQ`. An actual prover must commit to :math:`R` before
receiving an unpredictable :math:`c`. The order is crucial.

**Implementation:** :func:`blockchainkit.crypto.systems.signatures.verify_transcript`
checks the group equation; :func:`blockchainkit.crypto.systems.signatures.challenge`
hashes the message, public key, commitment, and curve domain.

**Experiment:** :doc:`/api/gallery/crypto/signatures/plot_01_schnorr_proofs` constructs both a real
signature and a simulated accepting transcript. It explains honest-verifier
zero-knowledge intuition; it does not implement a general proof system or claim
that every use of Fiat–Shamir is secure without further assumptions.

*References:* S. Goldwasser, S. Micali, and C. Rackoff, *The Knowledge
Complexity of Interactive Proof-Systems*, STOC '85, 291–304 (1985). `DOI
<https://doi.org/10.1145/22145.22178>`__. A. Fiat and A. Shamir, *How To Prove
Yourself: Practical Solutions to Identification and Signature Problems*, CRYPTO
'86, LNCS 263, 186–194 (proceedings 1987). `DOI
<https://doi.org/10.1007/3-540-47721-7_12>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_01_schnorr_proofs.py


1989–1991 — Schnorr identification and compact signatures
---------------------------------------------------------

**In plain language.** A short signature lets others check that a particular key
authorized a message. Its one-time secret must be fresh: reusing that value for two
different messages can expose the long-term private key.

**Reading the experiment.** Here x is the private key, Q its public key, k the secret
signing nonce, R a temporary public point, c a challenge, and s the response. G is the
starting point and n is its group order (the number of points in its cycle). The
experiment deliberately reuses k and recovers x.

Schnorr's identification and signature work made discrete-log proofs compact
and efficient. In additive notation, a prover with secret
:math:`x` commits using fresh :math:`k`, then responds to challenge :math:`c`:

.. math::

   R=kG,\qquad s=k+cx\pmod n,\qquad sG=R+cQ.

Two responses to different challenges under the same commitment expose
:math:`x=(s_1-s_2)(c_1-c_2)^{-1}\pmod n`. This gives a concrete lesson in both
proof extraction and catastrophic signing-nonce reuse.

**Implementation:** :func:`blockchainkit.crypto.systems.signatures.sign`,
:func:`blockchainkit.crypto.systems.signatures.verify`, and
:func:`blockchainkit.crypto.systems.signatures.recover_reused_nonce_key` use a
domain-separated teaching scheme over a prime-order elliptic-curve subgroup.
The historical paper uses multiplicative groups; this is an additive adaptation.

**Experiment:** :doc:`/api/gallery/crypto/signatures/plot_01_schnorr_proofs` signs two different messages
with one deliberately reused nonce and recovers the private key. The scheme
is not BIP-340. Explicit nonces are experiment controls, not a recommendation
for application key management.

*References:* C. P. Schnorr, *Efficient Signature Generation by Smart Cards*,
Journal of Cryptology 4, 161–174 (1991); following the CRYPTO '89 work. `DOI
<https://doi.org/10.1007/BF00196725>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_01_schnorr_proofs.py


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
Python's standard-library implementation instead of reimplementing the
compression function. :func:`blockchainkit.crypto.systems.commitments.commit` adds domain
separation and explicit salt framing for a simple commitment experiment.

.. doctest::

   >>> bk.crypto.sha256(b"abc").hex()
   'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

**Experiment:** :doc:`/api/gallery/crypto/hashing/plot_01_hashing` flips individual input bits and
measures output changes. This illustrates diffusion, not a proof of security.
An unsalted hash of a small guessable message does not hide it; commitment
hiding depends on unpredictable secret salt. Earlier milestones above use
SHA-256 as a modern teaching primitive, not as a historical implementation.

*References:* NIST, *Secure Hash Standard*, FIPS PUB 180-2 (2002). `Historical
standard record <https://csrc.nist.gov/pubs/fips/180-2/final>`__. This is cited
for historical context, not as the latest standards guidance.

.. minigallery:: ../../examples/crypto/hashing/plot_01_hashing.py
