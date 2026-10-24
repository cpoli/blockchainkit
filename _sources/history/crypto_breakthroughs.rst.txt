Breakthroughs in Cryptography
=============================

.. include:: /_generated/nav/crypto.rst

.. epigraph::

   "We stand today on the brink of a revolution in cryptography."
   -- Whitfield Diffie and Martin Hellman, *New Directions in Cryptography*,
   1976

Cryptography is the study of keeping and checking secrets when other people
can read, copy or change your messages. A blockchain is a shared record, like
a list of blocks of transactions. Many computers keep copies of it in
step, without trusting each other. Every later idea in a blockchain rests on
three things that cryptography provides:

- a way to agree on a secret in public;
- a way to prove who authorized a message;
- a way to *commit* to data without revealing it: to fix a value now, keep it
  hidden, and be unable to change it later.

This chronology traces the ideas behind :mod:`blockchainkit.crypto`, from the
one-time pad to Schnorr multi-signatures. Each entry follows the same order.
It states the problem. It gives the idea in plain words. It lists the steps of
the mechanism. Then it says why the mechanism works and where it stops
working. The parameters are deliberately small, so you can print and inspect
every value. :doc:`/protocol` lists exactly where the package departs from
deployed systems.

The page uses a few conventions throughout:

- *Alice* and *Bob* are the honest parties. An *attacker* is anyone trying to
  read, forge or change what they send.
- :math:`a \bmod p` is ``a % p``. :math:`g^x \bmod p` is ``pow(g, x, p)``,
  which takes only about :math:`\log_2 x` multiplications because it squares
  repeatedly. :math:`a \equiv b \pmod p` means ``a % p == b % p``.
- :math:`a^{-1} \bmod p` is the *inverse* of :math:`a`: the number that undoes
  multiplication by :math:`a`, so that :math:`a \cdot a^{-1} \equiv 1`. In
  Python it is ``pow(a, -1, p)``.
- :math:`\oplus` is bitwise XOR (``^`` in Python), :math:`\|` joins two byte
  strings (``a + b``), and :math:`|r|` is the length ``len(r)``.

Cryptographers measure strength in bits. A system has *b-bit security* if the
best known attack needs about :math:`2^b` basic operations. Each extra bit
doubles the attacker's work.

- :math:`2^{64} \approx 1.8 \times 10^{19}` operations is within reach: 100,000
  computers doing :math:`10^9` operations a second finish in about two days.
- :math:`2^{128} \approx 3.4 \times 10^{38}` operations is not. One such
  computer would need about :math:`10^{22}` years. The whole Bitcoin mining
  network, the largest computation on Earth at around :math:`10^{21}` hashes a
  second in the mid-2020s, would need about :math:`10^{10}` years. That is
  close to the age of the universe.

.. contents:: Timeline
   :local:
   :depth: 1

1917-1949 -- The One-Time Pad and Perfect Secrecy
-------------------------------------------------

Alice wants to send Bob a message that nobody else can read. This should hold
even against an attacker with unlimited computing power.

A *cipher* is a method for scrambling (encrypting) and unscrambling
(decrypting) a message with a *key*, a secret value. The scrambled message is
the *ciphertext*. Gilbert Vernam built a teleprinter in 1917 that combined
each character of a message with a character of a key tape. Joseph Mauborgne
added the rule that the tape must be random and never reused. In modern terms
the key is a random bit string as long as the message, and the two are
XORed.

#. Alice and Bob meet in advance and share a random key :math:`k`.
#. Alice computes the ciphertext :math:`c = m \oplus k`
   (``bytes(a ^ b for a, b in zip(m, k))``) and sends :math:`c`.
#. Bob computes :math:`c \oplus k`. XORing with the same key twice cancels
   out, because :math:`k \oplus k = 0`, so he gets :math:`m` back.
#. Both destroy the part of the key they used.

Claude Shannon's 1949 theory of secrecy systems proved why this is
unbreakable. Fix a ciphertext :math:`c`. For every candidate message :math:`m`
of the same length there is exactly one key, :math:`k = c \oplus m`, that
produces it. A *uniformly random* key is one where every bit string of that
length is equally likely. Such a key makes all of those candidate keys equally
likely. The ciphertext therefore gives no reason to prefer one message over
another:

.. math::

   c = m \oplus k, \qquad m = c \oplus k, \qquad
   \Pr[M = m \mid C = c] = \Pr[M = m].

The first two equations are encryption and decryption. The third says that
seeing :math:`c` does not change the probability of any message :math:`m`.
This is called *perfect secrecy*.

The pad is secure only if both rules hold:

- **The key is random.** Otherwise some messages become more likely than
  others.
- **The key is never reused.** Reusing it gives
  :math:`c_1 \oplus c_2 = m_1 \oplus m_2`, in which the key has cancelled out.
  The attacker then holds the XOR of two messages, which guesses about the
  language can unpick. Soviet reuse of pads let the US Venona project read
  thousands of messages.

Shannon also showed that every perfectly secret cipher needs at least as much
key as message. That makes the pad impractical for exactly the reason it
works. The two parties must already share a secret as long as everything they
will ever say. Getting such a secret to both parties is the *key-distribution
problem*. *Public-key cryptography*, where part of each key can be published
openly, would solve it.

*Implementation:* :func:`blockchainkit.crypto.systems.one_time_pad.one_time_pad`
refuses a key of the wrong length;
:func:`blockchainkit.crypto.systems.one_time_pad.xor_bytes` is the underlying
operation.

*References:* G. S. Vernam, *Cipher Printing Telegraph Systems for Secret Wire
and Radio Telegraphic Communications*, Journal of the American Institute of
Electrical Engineers 45, 109–115 (1926). C. E. Shannon, *Communication Theory
of Secrecy Systems*, Bell System Technical Journal 28(4), 656–715 (1949). `DOI
<https://doi.org/10.1002/j.1538-7305.1949.tb00928.x>`__.

.. minigallery:: ../../examples/crypto/one_time_pad/plot_01_one_time_pad.py

1971 -- Baby-Step Giant-Step: Square-Root Discrete Logs
-------------------------------------------------------

Most public-key systems on this page are secure only because one particular
calculation is hard to reverse. So the first question is how hard it really
is.

Take a prime :math:`p` and a number :math:`g`. The powers
:math:`g, g^2, g^3, \dots \bmod p` eventually return to 1 and then repeat in a
loop. The values in that loop form a *cyclic group*. :math:`g` is its
*generator*, and the length :math:`n` of the loop is its *order*. (In general
a *group* is any set with one operation that can be combined and undone, like
multiplication modulo :math:`p`. The 1985 entry builds another one from
elliptic curves.) Computing :math:`h = g^x` from :math:`x` is fast with
``pow``. The reverse, finding :math:`x` from :math:`h`, is the *discrete
logarithm* of :math:`h`. It has no obvious shortcut. Brute force, which means
trying every possibility, takes up to :math:`n` steps.

Daniel Shanks, while working on a problem in number theory, traded memory for
time to need only about :math:`\sqrt n` steps. The trick is the same one that
makes a Python dict fast: store values once, then look them up in
:math:`O(1)`.

#. Set :math:`m = \lceil\sqrt n\,\rceil`. Every exponent below :math:`n` can be
   written as :math:`x = im + j` with :math:`0 \le i, j < m`. This is like
   writing a number as tens and units: ``i, j = divmod(x, m)``.
#. **Baby steps.** Compute :math:`g^0, g^1, \dots, g^{m-1}` and store them in a
   table, ``table[pow(g, j, p)] = j``.
#. **Giant steps.** Compute :math:`h, hg^{-m}, hg^{-2m}, \dots`. Each step
   multiplies by :math:`g^{-m}`, the inverse of :math:`g^m`.
#. Stop when the giant step :math:`h\,(g^{-m})^{i}` is in the table, at some
   :math:`j`. Then :math:`x = im + j`.

Step 4 works because multiplying :math:`g^{im + j} = h` by :math:`g^{-im}`
separates the two unknowns:

.. math::

   g^{x} = h \iff g^{j} = h\,(g^{-m})^{i}, \qquad
   \text{cost} \approx 2\sqrt{n}.

In words: :math:`x` is found when some giant step lands on some baby step.
There are only :math:`m` of each, so the cost is about :math:`2\sqrt n`
multiplications, plus a table of :math:`m` entries.

- For :math:`n \approx 10^{12}` this is about two million steps instead of a
  trillion.
- Generic algorithms cannot do fundamentally better. A *generic* algorithm
  uses only the group operations (multiply, invert, compare) and never looks
  at how the elements are written down. Shoup proved in 1997 that any such
  algorithm needs about :math:`\sqrt n` steps.
- For well-chosen elliptic curves no attack better than these generic ones is
  known. That is why a group of about :math:`2^{256}` elements gives about
  128-bit security: :math:`\sqrt{2^{256}} = 2^{128}`.

*Implementation:* :func:`blockchainkit.crypto.systems.discrete_log.baby_step_giant_step`
returns the exponent and the number of table multiplications.

*References:* D. Shanks, *Class Number, a Theory of Factorization, and
Genera*, Proceedings of Symposia in Pure Mathematics 20, American Mathematical
Society, 415–440 (1971).

.. minigallery:: ../../examples/crypto/discrete_log/plot_01_baby_step_giant_step.py

1974-1978 -- Merkle's Puzzles: Key Agreement in Public
------------------------------------------------------

Can two people agree on a secret when every message between them is public?
That would solve the key-distribution problem left by the one-time pad.

As an undergraduate in 1974, Ralph Merkle proposed the first scheme that does
this. The idea: Alice hides many secrets in locked boxes that are each slow,
but possible, to open. Bob opens one box. An eavesdropper, who reads
everything sent but changes nothing, does not know which box Bob opened. So
they must open about half of them.

#. Alice makes :math:`N` puzzles. Each one seals a random identifier and a
   random *session key* (a fresh key for one conversation). The seal is a
   deliberately weak key, so one puzzle can be opened by brute force in about
   :math:`N` trials.
#. Alice keeps a private table, a dict from identifiers to session keys. She
   sends all :math:`N` puzzles to Bob in public.
#. Bob opens one puzzle chosen at random, which costs about :math:`N` trials.
#. Bob announces only its identifier.
#. Alice looks the identifier up in her table. Both now hold the same session
   key.

The eavesdropper hears the identifier but does not know which puzzle contains
it. So they must open puzzles until they find it, about :math:`N/2` of them on
average:

.. math::

   W_{\text{honest}} = O(N), \qquad
   W_{\text{attacker}} \approx \tfrac{N}{2} \cdot N = O(N^2).

In words: the honest work grows like :math:`N` and the attacker's work like
:math:`N^2`.

The idea was hard to publish, and the paper appeared in 1978, after Diffie and
Hellman's. Its limits and legacy:

- A quadratic gap is not practical security. The attacker's work is only about
  :math:`N/2` times Bob's. An attacker with a thousand times Bob's computing
  power can still keep up with a thousand-fold larger :math:`N`.
- Diffie-Hellman replaced it with a gap that grows exponentially in the key
  size: under the generic attacks, doubling the key length squares the
  attacker's work.
- The puzzles showed that public key agreement was possible at all.
- Barak and Mahmoody later proved (2009) that the quadratic gap is the best
  any scheme built only from a *random function* can achieve. A random
  function is one whose every output is an independent random value, like a
  dict filled by coin flips.

*Implementation:* :func:`blockchainkit.crypto.systems.puzzles.merkle_puzzles`
creates the puzzles and Alice's table;
:func:`blockchainkit.crypto.systems.puzzles.solve_puzzle` opens one by brute
force.

*References:* R. C. Merkle, *Secure Communications over Insecure Channels*,
Communications of the ACM 21(4), 294–299 (1978). `DOI
<https://doi.org/10.1145/359460.359473>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_01_merkle_puzzles.py

1976 -- Diffie-Hellman: Agreeing on a Secret over a Public Channel
------------------------------------------------------------------

Sharing an encryption key used to require a secret channel in advance. Diffie
and Hellman asked whether two people could reach the same secret by
exchanging only public values.

Their idea uses a one-way street: ``pow`` is fast forwards, but the discrete
log (1971 entry) is slow backwards. Each party keeps a private exponent and
publishes only a power of :math:`g`.

#. Everyone agrees on public numbers: a prime :math:`p` and a generator
   :math:`g`.
#. Alice picks a private :math:`a` and sends :math:`A = g^a \bmod p`.
#. Bob picks a private :math:`b` and sends :math:`B = g^b \bmod p`.
#. Alice computes ``pow(B, a, p)``. Bob computes ``pow(A, b, p)``.
#. Because exponents multiply in either order, both arrive at the same
   element:

.. math::

   A=g^a\bmod p,\qquad B=g^b\bmod p,\qquad
   B^a=(g^b)^a=g^{ab}=(g^a)^b=A^b \pmod p.

In words: Alice raises Bob's public value to her secret, Bob raises Alice's to
his, and both get :math:`g^{ab}`.

Why it is secure, and what it does not do:

- An observer sees :math:`g, p, A, B`. The only known general way to compute
  :math:`g^{ab}` from them is to recover :math:`a` or :math:`b`. That is a
  discrete logarithm, and the 1971 entry shows its generic cost is about
  :math:`\sqrt n`.
- The honest parties do one exponentiation each, about :math:`\log_2 n`
  multiplications. So the gap between them and the attacker grows
  exponentially with the key size. For :math:`n \approx 2^{256}` it is a few
  hundred multiplications against :math:`2^{128}`.
- The exchange does not say who is at the other end. This allows a
  *man-in-the-middle* attack:

  #. The attacker intercepts :math:`A` and sends Bob their own public value
     instead.
  #. The attacker intercepts :math:`B` and sends Alice their own public value
     instead.
  #. The attacker now shares one secret with each party, and can decrypt,
     read and re-encrypt everything relayed between them.

- Deployed protocols therefore *authenticate* the exchange: they sign the
  public values, so each side can check who sent them. They also pass the
  shared element through a *key derivation function*. This feeds it to a
  *hash function*, which is like Python's ``hash()`` but with a long output,
  built so that nobody can find two inputs with the same output or work back
  from an output to an input. The result is uniformly random key bytes.

In practice :math:`g` is chosen so that its order is a large prime. Its loop
of powers is then a *prime-order subgroup* of all the numbers modulo
:math:`p`; the 1978 Pohlig-Hellman entry explains why. X25519 is
Diffie-Hellman on an elliptic curve (1985 entry).

*Implementation:* :class:`blockchainkit.crypto.systems.asymmetric.DHGroup`
validates the prime-order subgroup and peer elements. It runs in a 62-bit
teaching group with no authentication; deployments use 2048-bit groups or
X25519.

*References:* W. Diffie and M. E. Hellman, *New Directions in Cryptography*,
IEEE Transactions on Information Theory 22(6), 644–654 (1976). `DOI
<https://doi.org/10.1109/TIT.1976.1055638>`__; `author's copy
<https://ee.stanford.edu/~hellman/publications/24.pdf>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_02_diffie_hellman.py

1978 -- RSA and the Public Trapdoor
-----------------------------------

Diffie-Hellman agrees on a key. It does not let anyone encrypt to a published
key, so that only the key's owner can decrypt. Nor does it give signatures. A
*digital signature* is a value that only the key's owner can compute, but that
anyone can check with the published key. It is like a handwritten signature
that cannot be copied onto another document.

Rivest, Shamir and Adleman gave the first concrete system with a *trapdoor*:
a public operation that anyone can apply, and a private one that reverses it.
It works like a padlock that anyone can snap shut but only the keyholder can
open.

#. Bob chooses distinct primes :math:`p, q` and computes :math:`n = pq`.
#. Bob picks an exponent :math:`e` and computes the inverse exponent
   :math:`d`: ``d = pow(e, -1, (p - 1) * (q - 1))``.
#. Bob publishes :math:`n` and :math:`e`, his *public key*, and keeps
   :math:`d`, his *private key*.
#. To send a number :math:`m < n`, Alice computes ``c = pow(m, e, n)``.
#. Bob decrypts with ``m = pow(c, d, n)``.
#. To sign :math:`m`, Bob instead computes ``s = pow(m, d, n)``. Anyone can
   check that ``pow(s, e, n) == m``.

.. math::

   ed\equiv1\pmod{(p-1)(q-1)},\qquad
   c=m^e\bmod n,\qquad m=c^d\bmod n.

In words: raising to :math:`e` and then to :math:`d` brings back the original
number modulo :math:`n`.

Why decryption works:

- :math:`ed = 1 + k(p-1)(q-1)` for some integer :math:`k`, by the choice of
  :math:`d`.
- Euler's theorem says :math:`m^{(p-1)(q-1)} \equiv 1 \pmod n` for every
  :math:`m` that shares no factor with :math:`n`. (The final result below also
  holds for the rare :math:`m` that do.)
- So :math:`c^d = m^{ed} = m \cdot (m^{(p-1)(q-1)})^k \equiv m \pmod n`.

Why it is secure, as far as anyone knows:

- Finding :math:`d` requires :math:`(p-1)(q-1)`, which requires the factors of
  :math:`n`. Computing :math:`d` from :math:`e` is in fact as hard as
  factoring.
- Security therefore rests on factoring being hard, though no proof shows that
  decrypting without :math:`d` is equally hard.
- Real systems add *padding*: random bytes and a fixed structure mixed into
  the message before exponentiating. Without it, RSA has the two weaknesses
  listed below.

*Implementation:* :func:`blockchainkit.crypto.systems.asymmetric.rsa_keypair`
exposes the arithmetic, with the familiar :math:`61\times53` example. This is
textbook RSA: tiny primes and no padding, so it is deterministic (equal
messages give equal ciphertexts) and malleable (multiplying ciphertexts
multiplies plaintexts). Real RSA uses moduli of 2048 bits or more with OAEP
(encryption) or PSS (signatures) padding.

*References:* R. L. Rivest, A. Shamir, and L. Adleman, *A Method for Obtaining
Digital Signatures and Public-Key Cryptosystems*, Communications of the ACM
21(2), 120–126 (1978). `DOI <https://doi.org/10.1145/359340.359342>`__.

.. minigallery:: ../../examples/crypto/public_keys/plot_03_rsa.py

1978 -- Pohlig-Hellman: Why the Group Order Needs a Large Prime Factor
----------------------------------------------------------------------

The :math:`\sqrt n` cost of the 1971 entry assumes the group cannot be taken
apart. Pohlig and Hellman showed that if the order :math:`n` has small prime
factors, the discrete log splits into one small problem per factor.

The idea is like rebuilding a number from its remainders. If you know
``x % 4`` and ``x % 9``, you know ``x % 36``. The *Chinese Remainder Theorem*
says this always works when the moduli share no factor. So it is enough to
find :math:`x` modulo each prime power in :math:`n`.

#. Factor the order as :math:`n = \prod p_i^{e_i}`, for example
   :math:`36 = 2^2 \cdot 3^2`.
#. For each prime power, raise :math:`g` and :math:`h` to the power
   :math:`n/p_i^{e_i}`. This lands them in a smaller loop, a *subgroup* of
   order :math:`p_i^{e_i}`: since :math:`g^n = 1`, the new :math:`g_i`
   returns to 1 after :math:`p_i^{e_i}` steps. There the same equation
   reveals :math:`x` modulo :math:`p_i^{e_i}`.
#. Solve each of these one base-:math:`p_i` digit at a time. Each digit is a
   discrete log in a subgroup of order only :math:`p_i`, found with
   baby-step giant-step.
#. Combine the remainders with the Chinese Remainder Theorem into
   :math:`x \bmod n`.

.. math::

   g_i = g^{n/p_i^{e_i}},\quad h_i = h^{n/p_i^{e_i}}
   \;\Longrightarrow\; h_i = g_i^{\,x \bmod p_i^{e_i}}, \qquad
   \text{cost} \approx \sum_i e_i \sqrt{p_i}.

In words: after the change of base, only :math:`x \bmod p_i^{e_i}` matters,
and the total cost adds up :math:`\sqrt{p_i}` for each digit of each prime.

Consequences:

- The cost is governed by the largest prime factor of :math:`n`, not by
  :math:`n` itself. A group of order :math:`n = 2^{64}` falls in about a hundred
  tiny steps.
- That is why Diffie-Hellman and Schnorr run in a subgroup of large prime
  order.
- It is also why :data:`blockchainkit.crypto.systems.asymmetric.TEACHING_GROUP`
  uses a *safe prime* :math:`p = 2q + 1` with :math:`q` prime: the subgroup of
  order :math:`q` has no smaller pieces to split off.

*Implementation:* :func:`blockchainkit.crypto.systems.discrete_log.pohlig_hellman`
factors the order by trial division, solves each prime-power part with
baby-step giant-step, and combines the answers.

*References:* S. Pohlig and M. Hellman, *An Improved Algorithm for Computing
Logarithms over GF(p) and Its Cryptographic Significance*, IEEE Transactions on
Information Theory 24(1), 106–110 (1978). `DOI
<https://doi.org/10.1109/TIT.1978.1055817>`__.

.. minigallery:: ../../examples/crypto/discrete_log/plot_02_pohlig_hellman.py

1979 -- Shamir's Threshold Secret Sharing
-----------------------------------------

A secret stored in one place can be lost or stolen in one go. Shamir split it
among :math:`n` people so that any :math:`t` of them can recover it, while
fewer learn nothing.

The idea: two points fix a line, three points fix a parabola, and in general
:math:`t` points fix a polynomial of degree :math:`t-1`. Hide the secret in a
random polynomial and give each person one point on it.

#. The dealer, who knows the secret :math:`s`, picks a prime :math:`p` larger than both
   :math:`s` and :math:`n`, and random coefficients :math:`a_1, \dots, a_{t-1}` below :math:`p`.
#. The dealer forms the polynomial :math:`f`, doing all arithmetic modulo
   :math:`p`. (Numbers modulo a prime, with ``+``, ``*`` and division by
   inverses, are called a *prime field*.)
#. The dealer gives person :math:`i` the share :math:`f(i)`, for
   :math:`i = 1, \dots, n`.
#. Any :math:`t` people pool their shares. *Lagrange interpolation*, a formula
   that rebuilds the unique polynomial through given points, returns
   :math:`f(0)`.

.. math::

   f(x)=s+a_1x+\cdots+a_{t-1}x^{t-1}\pmod p,
   \qquad s=f(0).

In words: the secret is the polynomial's value at :math:`x = 0`.

Why it works:

- A polynomial of degree at most :math:`t-1` is determined by any :math:`t` of
  its points, so :math:`t` shares fix :math:`f`.
- With only :math:`t-1` shares, every candidate secret :math:`s'` still fits.
  The :math:`t-1` points together with :math:`(0, s')` are :math:`t` points,
  which define exactly one polynomial.
- Since the coefficients are uniform, each candidate is equally likely.
- So the guarantee is *information-theoretic*: it holds against unlimited
  computing power. It does not rest on a computational hardness assumption,
  that is, on some problem being too slow to solve.

*Implementation:* :func:`blockchainkit.crypto.systems.sharing.split_secret` and
:func:`blockchainkit.crypto.systems.sharing.recover_secret` use integer field
arithmetic.

*References:* A. Shamir, *How to Share a Secret*, Communications of the ACM
22(11), 612–613 (1979). `DOI <https://doi.org/10.1145/359168.359176>`__.

.. minigallery:: ../../examples/crypto/sharing/plot_01_secret_sharing.py

1979 -- Lamport's One-Time Signatures from a Hash
-------------------------------------------------

RSA signatures rest on number theory. Leslie Lamport showed that a *one-way
function* alone suffices: a function that is easy to compute but practically
impossible to reverse. A cryptographic hash :math:`H`, such as SHA-256, is
used as one.

The idea: publish the hashes of many secret strings. To sign, reveal the
secrets that the message picks out. Anyone can hash them and compare.

#. **Key generation.** Pick 256 pairs of random strings
   :math:`x_{i,0}, x_{i,1}`. They are the private key. Their hashes are the
   public key.
#. **Signing.** Compute the 256-bit hash :math:`H(m)`, with bits
   :math:`b_1, \dots, b_{256}`. For each bit :math:`b_i`, reveal
   :math:`x_{i,b_i}`: one string of each pair, chosen by the bit.
#. **Verifying.** For each :math:`i`, check that
   :math:`H(x_{i,b_i}) = y_{i,b_i}`.

.. math::

   \text{public key } y_{i,b} = H(x_{i,b}), \qquad
   \sigma = (x_{1,b_1}, \dots, x_{256,b_{256}}).

In words: the public key is the hashes of all 512 secrets, and a signature
:math:`\sigma` is the 256 secrets that the message's hash bits select.

Why it works, and its limits:

- A forger needs, for every position, the *preimage* selected by the new
  message's hash bit. A preimage of :math:`y` is an input that hashes to
  :math:`y`. Producing an unrevealed one means inverting :math:`H`.
- Each signature, however, reveals half of the private key. After :math:`k`
  signatures on random messages, a given preimage has been revealed with
  probability :math:`1 - 2^{-k}`. A fresh random message can then be forged
  with probability about :math:`(1 - 2^{-k})^{256}`, which reaches 78% at
  :math:`k = 10`.
- An attacker who can try many messages does far better, so a key must sign
  only once.
- Merkle's trees, invented the same year, authenticate many one-time keys
  under one root. They hash the public keys in pairs, then hash those results
  in pairs, and so on up to a single root hash, which is published.
- Because they rely only on hashing, these signatures resist quantum
  computers. A large quantum computer could quickly break RSA, Diffie-Hellman
  and elliptic curves, but it speeds up attacks on hashes only modestly. The
  standardized SPHINCS+ (SLH-DSA) descends from Lamport's scheme.
- Winternitz chains shrink the keys by hashing one secret many times over, so
  that one chain signs several bits at once.

*Implementation:* :func:`blockchainkit.crypto.systems.lamport.lamport_keypair`,
:func:`blockchainkit.crypto.systems.lamport.lamport_sign`, and
:func:`blockchainkit.crypto.systems.lamport.lamport_verify` use full Lamport
pairs. Deployed hash-based signatures (XMSS, SPHINCS+) shrink them with
Winternitz chains and many-time trees.

*References:* L. Lamport, *Constructing Digital Signatures from a One Way
Function*, Technical Report CSL-98, SRI International (1979).

.. minigallery:: ../../examples/crypto/hash_signatures/plot_01_lamport_signatures.py

1979 -- Yuval's Birthday Attack
-------------------------------

Finding two people with the same birthday in a room is much easier than
finding someone with *your* birthday. Every pair of people is a chance for a
match, and the number of pairs grows like the square of the room size. Gideon
Yuval turned this into an attack on signatures. Signatures sign the hash of a
message rather than the message itself. So two messages with the same hash,
a *collision*, share every signature.

#. The attacker writes many harmless variants of a contract (extra spaces,
   swapped synonyms) and many harmful variants.
#. The attacker hashes them all, storing the harmless hashes in a dict.
#. The attacker stops when a harmful variant's hash is already in the dict.
#. The victim signs the harmless variant.
#. The signature also fits the harmful one.

Among :math:`q` random :math:`n`-bit values there are about :math:`q^2/2`
pairs. Each pair is equal with probability :math:`2^{-n}`. So a repeat appears
with probability about :math:`q^2/2^{n+1}` while that is small:

.. math::

   \Pr[\text{collision}] \approx 1 - e^{-q^2 / 2^{n+1}}, \qquad
   E[q] \approx \sqrt{\tfrac{\pi}{2}\, 2^{n}}.

In words: the chance of a collision approaches 1 once :math:`q` passes about
:math:`2^{n/2}`, and :math:`E[q]` is the expected number of hashes before the
first one.

Consequences:

- A collision is expected after about :math:`2^{n/2}` hashes. So an
  :math:`n`-bit hash gives only :math:`n/2` bits of *collision resistance*
  (the difficulty of finding any two inputs with the same hash).
- A 64-bit hash collides after about four billion tries, minutes on a laptop.
- That is why SHA-256's 256-bit output is chosen for 128-bit collision
  security.

*Implementation:* :func:`blockchainkit.crypto.systems.hashing.find_collision`
searches truncated SHA-256;
:func:`blockchainkit.crypto.systems.hashing.truncated_hash` does the
truncation.

*References:* G. Yuval, *How to Swindle Rabin*, Cryptologia 3(3), 187–191
(1979). `DOI <https://doi.org/10.1080/0161-117991854025>`__.

.. minigallery:: ../../examples/crypto/hashing/plot_01_birthday_attack.py

1981 -- Blum's Coin Flipping by Telephone: Commitments
------------------------------------------------------

Manuel Blum asked how two people who do not trust each other can flip a fair
coin over the telephone. His answer uses a sealed envelope.

#. Alice seals her call, heads or tails, in an envelope and sends it.
#. Bob announces a coin flip.
#. Alice opens the envelope.
#. Alice wins if her call matches the flip.

Each property of the envelope stops one cheat:

- It must be *binding*, so Alice cannot open it to the other call after
  hearing the flip.
- It must be *hiding*, so Bob cannot read the call and announce the opposite.

Such an envelope is a *commitment*. It can be built from a hash and a *salt*
:math:`r`, a random byte string mixed into the input:

.. math::

   C = H(\text{domain} \,\|\, |r| \,\|\, r \,\|\, m), \qquad
   \text{open}: (m, r) \ \text{with}\ H(\dots) = C.

In words: the commitment :math:`C` is the hash of a label, the salt's length,
the salt and the message. To open it, Alice reveals :math:`m` and :math:`r`,
and Bob recomputes the hash.

Why each part is there:

- Opening to a different value means finding a second input with the same
  hash, so binding rests on collision resistance.
- Without the salt, hiding would fail. Bob could simply hash "heads" and
  "tails" and compare. A long random salt makes such guessing hopeless.
- Encoding the salt's length :math:`|r|` fixes where the salt ends and the
  message begins, so one input cannot be split two ways.
- The domain label separates uses: a hash made for a commitment can never be
  mistaken for a hash made for something else. This is *domain separation*.
- Checking should take *constant time*: the same time whether the first
  differing byte is early or late (like ``hmac.compare_digest``). Otherwise
  timing leaks how much of a guess was right.

Commitments became a basic building block. A Schnorr prover commits to
:math:`R` before seeing a challenge (1985 entry), and a block header commits
to its transactions.

*Implementation:* :func:`blockchainkit.crypto.systems.commitments.commit` adds
domain separation and explicit salt framing;
:func:`blockchainkit.crypto.systems.commitments.verify_commitment` compares in
constant time.

*References:* M. Blum, *Coin Flipping by Telephone: A Protocol for Solving
Impossible Problems*, CRYPTO '81, 11–15 (1981); reprinted in ACM SIGACT News
15(1), 23–27 (1983). `DOI <https://doi.org/10.1145/1008908.1008911>`__.

.. minigallery:: ../../examples/crypto/commitments/plot_01_coin_flipping.py

1982-1983 -- Chaum's Blind Signatures and Private Payments
----------------------------------------------------------

To spend digital cash privately, a bank must authorize a token without
learning which token it signed. Otherwise it could link each payment back to
the customer who withdrew it.

The idea is like stamping an envelope without seeing the letter inside. David
Chaum introduced *blind signatures* at CRYPTO '82 (proceedings 1983). RSA's
algebra lets the requester hide a message with a random factor :math:`r` and
remove it after signing. :math:`r` must be *invertible* modulo :math:`n`,
meaning ``pow(r, -1, n)`` exists.

#. The requester picks a random invertible :math:`r` and sends the bank
   :math:`m' = mr^e \bmod n`.
#. The bank signs what it sees: :math:`s' = (m')^d \bmod n`.
#. The requester removes the factor: :math:`s = s'r^{-1} \bmod n`.
#. Anyone can check the result as an ordinary RSA signature on :math:`m`.

.. math::

   m'=mr^e\bmod n,\qquad
   s'=(m')^d\bmod n,\qquad
   s=s'r^{-1}\bmod n.

In words: blind, sign, unblind.

Why it works:

- The factor cancels because :math:`(r^e)^d = r`. So :math:`s' = m^d r`, then
  :math:`s = m^d` and :math:`s^e = m \pmod n`.
- The requester holds an ordinary signature on :math:`m`.
- The signer saw only :math:`m'`. Raising to :math:`e` *permutes the
  residues*: it shuffles the remainders modulo :math:`n` with no repeats. Since
  :math:`r` is uniform, :math:`m'` is uniform whatever :math:`m` is. So it
  reveals nothing about the token.

*Implementation:* :func:`blockchainkit.crypto.systems.asymmetric.rsa_blind` and
:func:`blockchainkit.crypto.systems.asymmetric.rsa_unblind` expose this
identity with textbook RSA over a tiny modulus. Standardized blind RSA (RFC
9474) hashes and pads the message and uses full-size keys.

*References:* D. Chaum, *Blind Signatures for Untraceable Payments*, CRYPTO
'82, 199–203 (proceedings 1983). `DOI
<https://doi.org/10.1007/978-1-4757-0602-4_18>`__.

.. minigallery:: ../../examples/crypto/blind_signatures/plot_01_blind_signatures.py

1985 -- Elliptic Curves as a Cryptographic Group
------------------------------------------------

Diffie-Hellman needs only a group in which discrete logs are hard. It does
not need the integers modulo :math:`p` specifically. Victor Miller proposed
elliptic curves for this at CRYPTO '85, and Neal Koblitz independently
developed elliptic-curve cryptosystems.

An *elliptic curve* here is the set of integer pairs :math:`(x, y)` that solve
the equation below modulo :math:`p`, plus one extra "point at infinity". It
is a finite set of curve points with a special addition rule, not a smooth
curve over the real numbers. The rule comes from geometry over the reals:
draw the line through two points, find where it meets the curve a third
time, and reflect that point. The same formulas work modulo :math:`p`. The
point at infinity acts as zero. Because the operation is written as addition,
:math:`xG` plays the role that ``pow(g, x, p)`` played before: the base point
:math:`G` added to itself :math:`x` times.

#. Everyone agrees on a curve and a base point :math:`G`.
#. A private key is an integer :math:`x`.
#. The public key is :math:`Q = xG`, computed by *double-and-add*, the
   addition version of ``pow``'s repeated squaring:

   #. Start with the point at infinity.
   #. For each bit of :math:`x`, from the top: double the running point, and
      if the bit is 1, add :math:`G`.

.. math::

   y^2=x^3+ax+b\pmod p,\qquad Q=xG.

In words: points satisfy the curve equation, and a public key is the base
point multiplied by the private integer.

Why curves allow short keys:

- Double-and-add computes :math:`Q` in about :math:`2\log_2 x` additions.
  Recovering :math:`x` from :math:`G, Q` is the elliptic-curve discrete-log
  problem.
- The integers modulo :math:`p` have extra structure, such as factorization
  into primes. *Index-calculus* algorithms exploit it to solve discrete logs
  (and factor RSA moduli) in *subexponential* time: much faster than
  :math:`2^{c \cdot \text{bits}}` for any fixed :math:`c`, though still slower
  than any polynomial. So those keys must be thousands of bits long.
- No such attack is known for well-chosen curves. That leaves only the
  :math:`\sqrt n` generic attacks, so a 256-bit curve key matches a roughly
  3072-bit RSA key.
- "Well-chosen" matters. A curve whose order has only small prime factors
  falls to Pohlig-Hellman, and some special families reduce to easier
  problems.
- Production code must also run in *constant time* (the same time for every
  key), because timing differences can reveal the private key.

*Implementation:* :class:`blockchainkit.crypto.systems.curves.Curve`,
:func:`blockchainkit.crypto.systems.curves.add`, and
:func:`blockchainkit.crypto.systems.curves.multiply` implement the group law,
including infinity, inverse points, and doubling. ``TOY_CURVE`` has 19 points;
``SECP256K1`` is Bitcoin's curve. The arithmetic is variable-time Python;
production libraries such as libsecp256k1 use constant-time code, because
timing can leak private scalars.

*References:* V. S. Miller, *Use of Elliptic Curves in Cryptography*, CRYPTO
'85, LNCS 218, 417–426 (proceedings 1986). `DOI
<https://doi.org/10.1007/3-540-39799-X_31>`__. N. Koblitz, *Elliptic Curve
Cryptosystems*, Mathematics of Computation 48(177), 203–209 (1987). `DOI
<https://doi.org/10.1090/S0025-5718-1987-0866109-5>`__.

.. minigallery:: ../../examples/crypto/curves/plot_01_elliptic_curves.py

1985 -- Zero Knowledge: Proofs That Reveal Nothing
--------------------------------------------------

Can you convince someone that you know a secret without revealing anything
about it? Goldwasser, Micali and Rackoff formalized this striking
possibility. An interaction between a *prover* and a *verifier* can convince
the verifier that a statement is true while revealing nothing else.

The test for "revealing nothing" uses a *simulator*: a program that does not
know the secret. A *transcript* is the record of every message exchanged. A
proof is *zero-knowledge* if the simulator can produce transcripts
indistinguishable from real ones, meaning no efficient test can tell them
apart. The verifier could have generated such transcripts alone. So the real
ones cannot have taught them anything.

Schnorr's later identification protocol shows the idea concretely. The prover
has a secret :math:`x` and public key :math:`Q = xG`. A *nonce* is a random
number used once.

#. The prover picks a random nonce :math:`k` and sends the commitment
   :math:`R = kG`.
#. The verifier sends a random *challenge* :math:`c`.
#. The prover answers :math:`s = k + cx`.
#. The verifier checks :math:`sG = R + cQ`.

The simulator fakes a transcript by working backwards:

#. Pick :math:`c` and :math:`s` at random.
#. Solve the check for a matching :math:`R = sG - cQ`.
#. Output :math:`(R, c, s)`, which passes the check without :math:`x`.

.. math::

   R = kG,\quad c \xleftarrow{\$} \mathbb{Z}_n,\quad s = k + cx;
   \qquad \text{simulator: } R = sG - cQ.

In words: :math:`c \xleftarrow{\$} \mathbb{Z}_n` means :math:`c` is drawn
uniformly from :math:`0, \dots, n-1`. A real prover fixes :math:`R` first; the
simulator fixes :math:`c` first.

Why the real proof still convinces:

- A prover who could answer two different challenges :math:`c_1 \ne c_2` for
  the same :math:`R` would know :math:`x = (s_1 - s_2)/(c_1 - c_2)`.
- Without :math:`x`, a cheating prover succeeds only by guessing :math:`c`
  before committing, with probability :math:`1/n`.
- So a real prover must commit to :math:`R` before seeing an unpredictable
  :math:`c`. That order is the only thing separating a proof from a
  simulation.
- Hence a recorded transcript proves nothing to a third party.
- The simulation argument assumes the verifier picks :math:`c` at random, as
  an honest one does.

*Implementation:* :func:`blockchainkit.crypto.systems.signatures.verify_transcript`
checks the group equation;
:func:`blockchainkit.crypto.systems.signatures.simulate_transcript` is the
simulator.

*References:* S. Goldwasser, S. Micali, and C. Rackoff, *The Knowledge
Complexity of Interactive Proof-Systems*, STOC '85, 291–304 (1985). `DOI
<https://doi.org/10.1145/22145.22178>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_01_zero_knowledge.py

1986 -- The Fiat-Shamir Heuristic: From Interaction to Signatures
-----------------------------------------------------------------

An interactive proof convinces only the verifier who took part. Fiat and
Shamir replaced the verifier's random challenge with a hash of the transcript
so far. The proof no longer needs a live conversation. Putting the message
into the hash turns it into a signature.

#. The signer picks a nonce :math:`k` and computes :math:`R = kG`.
#. The signer computes the challenge itself, :math:`c = H(R, Q, m)`.
#. The signer computes :math:`s = k + cx`. The signature is :math:`(R, s)`.
#. A verifier recomputes :math:`c` from :math:`R, Q, m` and checks
   :math:`sG = R + cQ`.

.. math::

   c = H(R, Q, m), \qquad \sigma = (R,\ s = k + cx).

In words: the hash plays the honest verifier, and the signature
:math:`\sigma` is the prover's commitment and answer.

Why it works, and what can go wrong:

- The simulator's trick was to pick :math:`c` first and then solve for
  :math:`R`. Now :math:`c` is computed from :math:`R`.
- If :math:`H` behaves like a random function, any change to :math:`R`
  produces an unpredictable new :math:`c`. The trick no longer works, and a
  valid :math:`(R, s)` again shows knowledge of :math:`x`.
- Pointcheval and Stern later proved such signatures secure in this
  *random-oracle model*: the analysis pretends :math:`H` is a truly random
  function that everyone can query.
- Everything the verifier would have seen must go into the hash. Leaving out
  :math:`Q`, for instance, lets an attacker choose the public key after the
  challenge.
- Schnorr signatures, EdDSA, and most zero-knowledge proof systems used by
  blockchains (SNARKs, STARKs: short proofs that a computation was done
  correctly) rely on this transform. Such omissions have broken real
  implementations (the 2022 "Frozen Heart" disclosures).

*Implementation:* :func:`blockchainkit.crypto.systems.signatures.challenge`
hashes the curve domain, public key, commitment, and message.

*References:* A. Fiat and A. Shamir, *How To Prove Yourself: Practical
Solutions to Identification and Signature Problems*, CRYPTO '86, LNCS 263,
186–194 (proceedings 1987). `DOI <https://doi.org/10.1007/3-540-47721-7_12>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_02_fiat_shamir.py

1987 -- Feldman's Verifiable Secret Sharing
-------------------------------------------

In Shamir's scheme everyone must trust the dealer who hands out the shares. A
dishonest dealer can hand out points that lie on no common polynomial. Nobody
notices until recovery fails.

Paul Feldman made the shares checkable without interaction. The dealer
publishes a "locked" copy of each polynomial coefficient, :math:`g^{a_j}`.
These reveal no coefficient directly, but let each share holder test their
own share.

#. The dealer picks a Shamir polynomial with coefficients :math:`a_j` and
   :math:`a_0 = s`.
#. The dealer publishes :math:`C_j = g^{a_j}` for each coefficient.
#. The dealer sends share :math:`f(i)` privately to share holder :math:`i`.
#. Share holder :math:`i` checks the equation below, and complains publicly if
   it fails.

.. math::

   g^{f(i)} = \prod_{j=0}^{t-1} C_j^{\,i^{j}} \pmod p.

In words: from the public values alone, anyone can compute what
:math:`g^{f(i)}` should be, and compare it with the share.

Why it works, and its price:

- Exponentiation turns sums into products, since :math:`g^{a+b} = g^a g^b`.
  So the right side equals :math:`g^{\sum_j a_j i^j} = g^{f(i)}`.
- Because :math:`g` has prime order :math:`q`, the check passes exactly when
  the share equals :math:`f(i)` modulo :math:`q`, that is, when it lies on the
  committed polynomial.
- The price is that :math:`C_0 = g^{s}` is public. So the secret is protected
  only by the hardness of the discrete log rather than
  information-theoretically.
- Complaints need a *broadcast channel*, where everyone is sure to see the
  same message.
- Verifiable sharing underlies *distributed key generation*. Every party
  deals a random secret, and the group key combines them. Threshold wallets,
  which need :math:`t` of :math:`n` parties to sign, use it to create a key
  that no single party ever holds.

*Implementation:* :func:`blockchainkit.crypto.systems.sharing.feldman_split` and
:func:`blockchainkit.crypto.systems.sharing.feldman_verify` work over
:data:`blockchainkit.crypto.systems.asymmetric.TEACHING_GROUP`, where discrete
logs are easy to compute. Real verifiable secret sharing needs a group of
cryptographic size and a broadcast channel for complaints.

*References:* P. Feldman, *A Practical Scheme for Non-interactive Verifiable
Secret Sharing*, 28th Symposium on Foundations of Computer Science (FOCS),
427–438 (1987). `DOI <https://doi.org/10.1109/SFCS.1987.4>`__.

.. minigallery:: ../../examples/crypto/sharing/plot_02_feldman_vss.py

1989 -- The Merkle-Damgård Construction and Length Extension
------------------------------------------------------------

A hash function must accept messages of any length. It is much easier to
design and analyze a *compression function* :math:`f`. This maps a fixed-size
state and one fixed-size block of input to a new state. Ralph Merkle and Ivan
Damgård independently showed at CRYPTO '89 how to chain one into a full hash.
The idea is a loop: ``h = f(h, block)`` for each block.

#. Pad the message so that it ends with its own length and fills a whole
   number of blocks.
#. Split it into blocks :math:`m_1, \dots, m_\ell`.
#. Start the state at a fixed constant, :math:`h_0 = IV` (the *initial
   value*).
#. Feed each block through :math:`f`, updating the state.
#. The final state is the digest, the hash output.

.. math::

   h_0 = IV, \qquad h_i = f(h_{i-1}, m_i), \qquad H(m) = h_\ell.

In words: the digest is the state after the last block.

Why collision resistance carries over:

- If :math:`f` is collision-resistant, so is :math:`H`.
- Trace two colliding messages backward from their equal digests. At the last
  step where the inputs to :math:`f` differ, the outputs are still equal.
  That is a collision in :math:`f`.
- The encoded length guarantees that such a step exists.
- MD5, SHA-1 and SHA-256 all follow this design.

Its side effect is *length extension*. Since :math:`H(m)` *is* the chaining
state, anyone can resume the chain from it. They can compute
:math:`H(m \,\|\, \text{pad} \,\|\, s)` knowing only :math:`H(m)` and
:math:`|m|`. This breaks a naive *MAC* (message authentication code): a short
tag, computed from a message and a shared key, that proves the message came
from a key holder unchanged. A "MAC" computed as :math:`H(k \,\|\, m)` is
therefore forgeable:

#. The attacker sees one valid tag :math:`t = H(k \,\|\, m)` and knows the
   length of :math:`k \,\|\, m`.
#. The attacker sets the state to :math:`t` and works out the padding that
   followed :math:`k \,\|\, m`.
#. The attacker continues the loop over any extra blocks :math:`s`.
#. The result is a valid tag for the extended message
   :math:`m \,\|\, \text{pad} \,\|\, s`, made without knowing :math:`k`.

*Implementation:* :func:`blockchainkit.crypto.systems.merkle_damgard.merkle_damgard_sha256`
reimplements SHA-256 block by block (checked against the standard library);
:func:`blockchainkit.crypto.systems.merkle_damgard.length_extension` performs
the attack.

*References:* R. C. Merkle, *One Way Hash Functions and DES*, CRYPTO '89, LNCS
435, 428–446 (1990). `DOI <https://doi.org/10.1007/0-387-34805-0_40>`__. I. B.
Damgård, *A Design Principle for Hash Functions*, CRYPTO '89, LNCS 435, 416–427
(1990). `DOI <https://doi.org/10.1007/0-387-34805-0_39>`__.

.. minigallery:: ../../examples/crypto/hashing/plot_02_merkle_damgard.py

1989-1991 -- Schnorr Identification and Compact Signatures
----------------------------------------------------------

Claus Schnorr made discrete-log proofs short and fast. This is the protocol
already used in the 1985 entry. It is written in *additive notation*, where
the group operation is ``+`` and repeated addition :math:`xG` replaces
:math:`g^x`, as on elliptic curves.

#. The prover, with secret :math:`x` and public key :math:`Q = xG`, picks a
   fresh nonce :math:`k` and commits with :math:`R = kG`.
#. The prover receives a challenge :math:`c`.
#. The prover answers :math:`s = k + cx \bmod n`.
#. The verifier checks :math:`sG = R + cQ`. The check holds because
   :math:`sG = (k + cx)G = kG + c(xG)`.

.. math::

   R=kG,\qquad s=k+cx\pmod n,\qquad sG=R+cQ.

In words: the answer :math:`s` mixes the nonce and the secret, and the check
confirms the mix using only public points.

Properties:

- The Fiat-Shamir transform with :math:`c = H(R, Q, m)` turns this into a
  signature :math:`(R, s)`: one group element and one scalar (an integer
  modulo :math:`n`).
- The nonce must be fresh. Two signatures with the same :math:`k` give two
  linear equations in :math:`k` and :math:`x` (the 2010-2013 entry).
- The equation is also linear in the keys. If two signers use the same
  :math:`c`, their :math:`R` and :math:`s` values add to a valid signature for
  :math:`Q_1 + Q_2`. This later enabled multi-signatures (the 2018 entry).
- A patent kept Schnorr signatures out of standards until it expired in 2008.
  Bitcoin adopted them in 2021 as BIP-340 (Bitcoin Improvement Proposal 340).
  BIP-340 stores only the x-coordinate of a public key and hashes with a
  tagged hash, a hash prefixed by a label.

*Implementation:* :func:`blockchainkit.crypto.systems.signatures.sign`,
:func:`blockchainkit.crypto.systems.signatures.verify`, and
:func:`blockchainkit.crypto.systems.signatures.recover_reused_nonce_key` use a
domain-separated scheme over a prime-order elliptic-curve group, an additive
adaptation of the original multiplicative groups. The challenge encoding
differs from BIP-340 (no x-only keys or tagged hash), so these signatures do
not verify in Bitcoin.

*References:* C. P. Schnorr, *Efficient Signature Generation by Smart Cards*,
Journal of Cryptology 4, 161–174 (1991); following the CRYPTO '89 work. `DOI
<https://doi.org/10.1007/BF00196725>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_03_schnorr_signatures.py

1991 -- Pedersen Commitments: Perfectly Hiding and Additive
-----------------------------------------------------------

A hash commitment hides its contents only from an attacker who cannot invert
the hash. Also, nothing useful can be computed on sealed values. Torben
Pedersen introduced a commitment with two better properties:

- it hides its contents even from an attacker with unlimited computing power;
- multiplying sealed commitments adds the amounts inside them.

It uses two generators :math:`g, h` of a group of prime order :math:`q`.

#. Setup: :math:`h` is derived by hashing, so that nobody knows the exponent
   :math:`w` with :math:`h = g^w`.
#. Commit: to commit to a value :math:`v`, pick a random *blinding*
   :math:`r` and publish :math:`C = g^v h^r \bmod p`.
#. Open: reveal :math:`v` and :math:`r`. Anyone recomputes :math:`C`.

.. math::

   C(v, r) = g^{v} h^{r} \bmod p, \qquad C(a, r)\,C(b, s) = C(a + b,\ r + s).

In words: a commitment is :math:`g` to the value times :math:`h` to the
blinding. Multiplying two commitments gives a commitment to the sum of the
values, because exponents add.

Why it hides perfectly, and binds only computationally:

- Write :math:`h = g^{w}`. Then :math:`C = g^{v + wr}`.
- For any other value :math:`v'`, the blinding
  :math:`r' = r + (v - v')/w \bmod q` gives the same :math:`C`. Every value is
  equally consistent with :math:`C`, so hiding is perfect.
- Conversely, anyone who opens one commitment to two values
  :math:`(v, r) \ne (v', r')` has :math:`v + wr = v' + wr'`. They can solve for
  :math:`w = \log_g h`.
- So binding is only as strong as that discrete log. That is why :math:`h` is
  derived by hashing, so that nobody knows :math:`w`.
- The additive property lets anyone check that hidden inputs equal hidden
  outputs. This is the basis of *confidential transactions*, whose amounts
  stay hidden, in Monero and Mimblewimble.

*Implementation:* :func:`blockchainkit.crypto.systems.commitments.pedersen_commit`
and :func:`blockchainkit.crypto.systems.commitments.pedersen_generators` work in
the teaching group, so binding holds only while its small discrete logarithm
stays unknown; production uses 256-bit elliptic-curve groups.

*References:* T. P. Pedersen, *Non-Interactive and Information-Theoretic Secure
Verifiable Secret Sharing*, CRYPTO '91, LNCS 576, 129–140 (1992). `DOI
<https://doi.org/10.1007/3-540-46766-1_9>`__.

.. minigallery:: ../../examples/crypto/commitments/plot_02_pedersen.py

1996 -- HMAC: Keyed Hashing Done Right
--------------------------------------

To prove that a message came from someone holding a shared key, the key must
be mixed into the hash in a way that leaves an attacker nothing to extend.
The 1989 entry shows that :math:`H(k \,\|\, m)` fails this test.

Bellare, Canetti and Krawczyk defined HMAC. It hashes twice, with two keys
derived from :math:`k`. They proved it secure under assumptions about the
compression function. *ipad* and *opad* are two fixed byte patterns (``0x36``
and ``0x5c`` repeated), XORed into the key after it is padded to one block.

#. Inner hash: compute :math:`H((k \oplus ipad) \,\|\, m)`.
#. Outer hash: compute :math:`H((k \oplus opad) \,\|\, \text{inner digest})`.
#. The outer digest is the tag.

.. math::

   \mathrm{HMAC}(k, m) = H\bigl((k \oplus opad) \,\|\, H((k \oplus ipad) \,\|\, m)\bigr).

In words: hash the message with one version of the key, then hash that
result with another version of the key.

Why length extension now fails:

- Resuming the outer hash from the tag only appends data after the inner
  digest.
- A tag for :math:`m \,\|\, s` needs the inner digest of
  :math:`m \,\|\, s`, which the attacker cannot compute without the key.

HMAC became RFC 2104 in 1997. (An RFC is an internet standards document.) It
is everywhere: TLS (the protocol behind ``https``), key derivation (HKDF), and
the deterministic nonces of RFC 6979.

*Implementation:* :func:`blockchainkit.crypto.systems.mac.hmac_sha256`,
contrasted with the broken :func:`blockchainkit.crypto.systems.mac.naive_mac`.

*References:* M. Bellare, R. Canetti, and H. Krawczyk, *Keying Hash Functions
for Message Authentication*, CRYPTO '96, LNCS 1109, 1–15 (1996). `DOI
<https://doi.org/10.1007/3-540-68697-5_1>`__.

.. minigallery:: ../../examples/crypto/hashing/plot_03_hmac.py

2002 -- SHA-256 as a Standardized Hash Primitive
------------------------------------------------

Different programs must compute the same fingerprint for the same data.
Otherwise a signature made by one cannot be checked by another. NIST, the US
standards agency, specified SHA-256 in FIPS 180-2 alongside other secure hash
algorithms. The standard includes *test vectors*, known input-output pairs
that independent implementations can check themselves against.

A good hash behaves like a random function, so related inputs must give
unrelated outputs. Changing one input bit should flip each of the 256 output
bits independently with probability one half. This is the *avalanche*
effect. You can measure it:

#. Hash a message :math:`m`.
#. Flip one bit to get :math:`m'`, and hash it.
#. XOR the two digests and count the 1-bits (the *popcount*,
   ``int.bit_count()``).

The number of flipped bits is then binomial, like the number of heads in 256
fair coin tosses:

.. math::

   d = \mathrm{popcount}\bigl(H(m) \oplus H(m')\bigr)
   \sim \mathrm{Binomial}\bigl(256, \tfrac12\bigr), \qquad
   E[d] = 128, \quad \sigma_d = 8.

In words: on average 128 bits change, with a standard deviation of 8 bits.

Why it matters, and what a hash is not:

- If outputs clustered by input instead, an attacker could steer toward a
  target digest. That would beat the :math:`2^{256}` (preimage) or
  :math:`2^{128}` (collision, the 1979 entry) work that a random function
  forces.
- A digest is a compact fingerprint. It does not encrypt the input.
- A guessable input can be found by hashing candidates.

*Implementation:* :func:`blockchainkit.crypto.systems.hashing.sha256` delegates
to Python's standard library;
:func:`blockchainkit.crypto.systems.merkle_damgard.merkle_damgard_sha256` is a
readable reimplementation (the 1989 entry) that the tests check against it.

*References:* NIST, *Secure Hash Standard*, FIPS PUB 180-2 (2002). `Historical
standard record <https://csrc.nist.gov/pubs/fips/180-2/final>`__, cited for
historical context rather than as current standards guidance.

.. minigallery:: ../../examples/crypto/hashing/plot_04_sha256_avalanche.py

2010-2013 -- Nonce Reuse in Practice, and Deterministic Nonces
--------------------------------------------------------------

A signature hides the private key behind a fresh random nonce. If the nonce
repeats, the key leaks. With :math:`s_i = k + c_i x`, two signatures that
share :math:`k` but sign different messages (so :math:`c_1 \ne c_2`) are two
linear equations in two unknowns.

#. The attacker finds two signatures with the same :math:`R`, which means the
   same :math:`k`.
#. The attacker recomputes both challenges :math:`c_1, c_2` from the public
   data.
#. Subtracting the equations eliminates :math:`k`. Dividing by
   :math:`c_1 - c_2` (multiplying by ``pow(c1 - c2, -1, n)``) gives :math:`x`.

.. math::

   s_1 - s_2 = (c_1 - c_2)\,x
   \quad\Longrightarrow\quad
   x = \frac{s_1 - s_2}{c_1 - c_2} \bmod n.

In words: two answers to two challenges with the same nonce reveal the
secret, just as in the 1985 soundness argument.

It happened in practice:

- ECDSA, the elliptic-curve signature standard used by Bitcoin and Ethereum,
  has a different equation, :math:`s = k^{-1}(z + rx)`. The same counting
  applies: a repeated nonce leaves two equations in :math:`k` and :math:`x`.
- In December 2010 the fail0verflow team showed that Sony's PlayStation 3
  signed software with a constant ECDSA nonce, and recovered Sony's private
  key.
- Weak random number generators in Android wallets led to Bitcoin thefts in
  2013.

The fix was to stop needing randomness. Thomas Pornin's RFC 6979 derives the
nonce from an HMAC-based deterministic generator. It is seeded with the
private key and the message hash.

- Distinct messages get distinct nonces, so the equations above never arise.
- The nonce is unpredictable without the key.
- It does not stop *fault attacks*, which disturb the hardware (for example
  with a voltage glitch) so that it computes a wrong signature.

*Implementation:* :func:`blockchainkit.crypto.systems.signatures.recover_reused_nonce_key`
performs the extraction;
:func:`blockchainkit.crypto.systems.signatures.deterministic_nonce` implements
RFC 6979 section 3.2 with SHA-256 and reproduces the RFC's test vectors. It
feeds this package's Schnorr signatures rather than ECDSA, and adds no
protection against fault attacks.

*References:* fail0verflow (bushing, marcan, sven), *Console Hacking 2010: PS3
Epic Fail*, 27th Chaos Communication Congress (2010). T. Pornin,
*Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic
Curve Digital Signature Algorithm (ECDSA)*, RFC 6979 (2013). `DOI
<https://doi.org/10.17487/RFC6979>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_04_nonce_reuse.py

2018 -- MuSig: Schnorr Multi-Signatures and the Rogue-Key Attack
----------------------------------------------------------------

A *multi-signature* is one signature, produced jointly by several key
holders, that is valid for one combined public key. Schnorr signatures are
linear, so this looks easy. With a shared challenge :math:`c`, partial
signatures :math:`s_i = k_i + c x_i` add up to one ordinary signature. It is
valid for the aggregate key :math:`\sum Q_i` and nonce :math:`\sum R_i`.

Done naively, this allows a *rogue-key attack*:

#. The honest signer announces :math:`Q_{\text{honest}}`.
#. The last signer to announce a key waits for the others. They pick an
   :math:`x` they know and announce
   :math:`Q_{\text{rogue}} = xG - Q_{\text{honest}}`.
#. The aggregate key is now
   :math:`Q_{\text{honest}} + Q_{\text{rogue}} = xG`.
#. The attacker does not know the private key of :math:`Q_{\text{rogue}}`, but
   does not need it. They know :math:`x`, so they can sign alone.

Maxwell, Poelstra, Seurin and Wuille's MuSig weights every key by a hash of
the whole key list :math:`L`:

#. Every signer computes the weight :math:`a_i = H(L, Q_i)` of each key.
#. The aggregate key is :math:`Q_{\text{agg}} = \sum_i a_i Q_i`.
#. Each signer contributes a nonce point :math:`R_i`, and the shared challenge
   :math:`c` is computed from their sum, the aggregate key and the message.
#. Each signer sends :math:`k_i + c\, a_i x_i`. The sum :math:`s` completes the
   signature.

.. math::

   a_i = H(L, Q_i), \qquad Q_{\text{agg}} = \sum_i a_i Q_i, \qquad
   s = \sum_i (k_i + c\, a_i x_i).

In words: each key is scaled by a hash of the whole list before adding, and
the partial signatures are scaled the same way.

Why the attack fails:

- The cancellation needs a key chosen as a function of the others' weighted
  keys.
- But the weights depend on the attacker's own key through :math:`L`.
- Changing the key changes every coefficient unpredictably, so the attacker
  is left guessing, as with any hash.

Bitcoin's Taproot upgrade (2021) made such aggregate spends indistinguishable
from single-signer spends.

*Implementation:* :func:`blockchainkit.crypto.systems.multisig.musig_coefficients`,
:func:`blockchainkit.crypto.systems.multisig.aggregate_public_keys`, and
:func:`blockchainkit.crypto.systems.multisig.musig_sign`. All signers run in
one process; real MuSig needs a round of nonce commitments (or MuSig2's two
nonces per signer) to resist attacks across concurrent signing sessions.

*References:* G. Maxwell, A. Poelstra, Y. Seurin, and P. Wuille, *Simple
Schnorr Multi-Signatures with Applications to Bitcoin*, Designs, Codes and
Cryptography 87, 2139–2164 (2019); preprint IACR ePrint 2018/068. `DOI
<https://doi.org/10.1007/s10623-019-00608-x>`__.

.. minigallery:: ../../examples/crypto/signatures/plot_05_musig.py
