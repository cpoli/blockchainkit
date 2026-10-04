Exercises: cryptography
=======================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. Diffie-Hellman: recovering a tiny secret
-------------------------------------------

From :doc:`/api/gallery/crypto/public_keys/plot_02_diffie_hellman`.
Exhaustively recover Alice's exponent from her public value. Why does this
say nothing about the cost in a carefully chosen large group?

.. dropdown:: Solution

   .. doctest::

      >>> group = bk.crypto.DHGroup()
      >>> public = group.public(3)
      >>> [x for x in range(1, group.q) if group.public(x) == public]
      [3]

   Enumeration works because the group is tiny: it tries at most ``q``
   exponents. In a group of 256-bit order, the same loop would need about
   :math:`2^{256}` steps, and the best generic algorithms still about
   :math:`2^{128}`. The experiment also shows why the exchange needs
   authentication: an attacker who substitutes their own public value is not
   detected by the arithmetic.

2. RSA: factoring the modulus
-----------------------------

From :doc:`/api/gallery/crypto/public_keys/plot_03_rsa`. Factor
:math:`n = 3233` by trial division and recompute :math:`d`.

.. dropdown:: Solution

   .. doctest::

      >>> key = bk.crypto.rsa_keypair()
      >>> p = next(f for f in range(2, key.n) if key.n % f == 0)
      >>> q = key.n // p
      >>> p, q
      (53, 61)
      >>> pow(key.e, -1, (p - 1) * (q - 1)) == key.d
      True

   Knowing the factors gives :math:`\varphi(n) = (p-1)(q-1)` and hence the
   private exponent. Security rests on factoring being infeasible for
   moduli of 2048 bits or more; a scrambled-looking plot of ciphertexts says
   nothing about that.

3. Secret sharing: a forged share
---------------------------------

From :doc:`/api/gallery/crypto/sharing/plot_01_secret_sharing`. Change a share
before reconstruction. What would participants need to detect it?

.. dropdown:: Solution

   .. doctest::

      >>> from random import Random
      >>> shares = bk.crypto.split_secret(42, 3, 5, randbelow=Random(7).randrange)
      >>> bk.crypto.recover_secret(shares[:3])
      42
      >>> altered = [(shares[0][0], (shares[0][1] + 1) % 2089), *shares[1:3]]
      >>> bk.crypto.recover_secret(altered) != 42
      True

   Interpolation still returns an answer, just a wrong one: plain Shamir
   sharing does not authenticate shares. Feldman's verifiable secret sharing
   (see :doc:`/api/gallery/crypto/sharing/plot_02_feldman_vss`) publishes
   commitments that let each share be checked.

4. Blind signatures: a mask that cannot be removed
--------------------------------------------------

From :doc:`/api/gallery/crypto/blind_signatures/plot_01_blind_signatures`. Try
a blinding factor :math:`r` that shares a factor with :math:`n`.

.. dropdown:: Solution

   .. doctest::

      >>> from math import gcd
      >>> key = bk.crypto.rsa_keypair()
      >>> gcd(61, key.n)
      61
      >>> try:
      ...     bk.crypto.rsa_blind(42, 61, key)
      ... except ValueError:
      ...     print("No invertible mask")
      No invertible mask

   Unblinding multiplies by :math:`r^{-1} \bmod n`, which exists only when
   :math:`\gcd(r, n) = 1`. Blinding hides what the signer signs; it does not
   stop the same token being spent twice. That still needs a record of spent
   tokens.

5. Elliptic curves: group identities
------------------------------------

From :doc:`/api/gallery/crypto/curves/plot_01_elliptic_curves`. Verify
:math:`G + (-G) = \infty` and :math:`(a + b)G = aG + bG`.

.. dropdown:: Solution

   .. doctest::

      >>> curve = bk.crypto.TOY_CURVE
      >>> g = curve.generator
      >>> bk.crypto.add(g, bk.crypto.multiply(-1, g, curve), curve) is None
      True
      >>> bk.crypto.multiply(7, g, curve) == bk.crypto.add(
      ...     bk.crypto.multiply(3, g, curve), bk.crypto.multiply(4, g, curve), curve)
      True

   Coordinates are elements of a finite field, so the "curve" is a set of
   isolated points. Double-and-add branches on each bit of the scalar, which
   is why production code uses constant-time ladders.

6. Schnorr: recovering a key from a reused nonce
------------------------------------------------

From :doc:`/api/gallery/crypto/signatures/plot_04_nonce_reuse`. Derive
:math:`x = (s_1 - s_2)/(c_1 - c_2) \bmod n` from :math:`s_i = k + c_i x`.

.. dropdown:: Solution

   Subtracting the two responses cancels :math:`k`:
   :math:`s_1 - s_2 = (c_1 - c_2)x`. Dividing needs :math:`c_1 \ne c_2`, which
   holds for different messages.

   .. doctest::

      >>> curve = bk.crypto.TOY_CURVE
      >>> public = bk.crypto.public_key(7, curve)
      >>> first = bk.crypto.sign(b"a", 7, nonce=3, curve=curve)
      >>> c1 = bk.crypto.challenge(b"a", first.commitment, public, curve)
      >>> messages = [str(i).encode() for i in range(100)]
      >>> message = next(
      ...     m for m in messages if bk.crypto.challenge(m, first.commitment, public, curve) != c1)
      >>> second = bk.crypto.sign(message, 7, nonce=3, curve=curve)
      >>> c2 = bk.crypto.challenge(message, second.commitment, public, curve)
      >>> bk.crypto.recover_reused_nonce_key(first, second, c1, c2, curve.order)
      7

   A deterministic nonce (RFC 6979) is derived from the key *and the
   message*, so signing the same message twice reuses the nonce on the same
   challenge, which reveals nothing, and different messages get different
   nonces.

7. Hashing: collisions in a truncated digest
--------------------------------------------

From :doc:`/api/gallery/crypto/hashing/plot_04_sha256_avalanche`. Keep only the
first byte of each digest and find a collision.

.. dropdown:: Solution

   .. doctest::

      >>> seen = {}
      >>> for i in range(257):
      ...     short = bk.crypto.sha256(str(i).encode())[0]
      ...     if short in seen:
      ...         collision = (seen[short], i)
      ...         break
      ...     seen[short] = i
      >>> first, second = collision
      >>> bk.crypto.sha256(str(first).encode())[0] == bk.crypto.sha256(str(second).encode())[0]
      True

   With 256 possible values, 257 inputs guarantee a collision, but the
   birthday bound predicts one after about :math:`\sqrt{\pi/2 \cdot 256}
   \approx 20`. This attacks an 8-bit truncation, not SHA-256's 256 bits.

8. Birthday attacks: how long a collision takes
-----------------------------------------------

From :doc:`/api/gallery/crypto/hashing/plot_01_birthday_attack`. At a billion
hashes per second, how long does a collision take on a 64-bit hash? On a
128-bit hash?

.. dropdown:: Solution

   .. doctest::

      >>> from math import pi, sqrt
      >>> def seconds(bits, rate=1e9):
      ...     return sqrt(pi / 2 * 2**bits) / rate
      >>> round(seconds(64))
      5
      >>> round(seconds(128) / (365.25 * 24 * 3600), -1)
      730.0

   About five seconds for 64 bits, and some 730 years for 128 bits on one
   machine: a fleet of a million such machines would need under seven hours.
   That is why 128-bit digests are too short for collision resistance today.
   MD5 fell earlier, though, not to this generic bound but to structural
   attacks (Wang et al., 2004) that find collisions in seconds.

9. Hash-based signatures: a Merkle tree of one-time keys
--------------------------------------------------------

From :doc:`/api/gallery/crypto/hash_signatures/plot_01_lamport_signatures`. How
big is a proof that one key belongs to a tree of :math:`2^{20}` keys?

.. dropdown:: Solution

   .. doctest::

      >>> leaves = [str(i).encode() for i in range(2**10)]
      >>> tree = bk.structures.MerkleTree(leaves)
      >>> len(tree.proof(5).siblings)
      10
      >>> 20 * 32
      640

   A proof holds one sibling digest per level: 20 hashes of 32 bytes for
   :math:`2^{20}` keys, 640 bytes, against 16 KiB for one Lamport public
   key. This is the idea behind Merkle's signature scheme and today's
   SPHINCS+.
