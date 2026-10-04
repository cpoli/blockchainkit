Nonces everywhere
=================

*Nonce* means "number used once", and blockchainkit has at least four of them.
They share a name and almost nothing else: one must be secret, one must be
public and counted, one is a lottery ticket, and one is a salt. Mixing them up
is one of the most common confusions about blockchains, and one of the most
expensive mistakes in their software.

.. list-table::
   :header-rows: 1
   :widths: 18 18 18 46

   * - Nonce
     - Secret?
     - Chosen how?
     - What goes wrong if it is reused
   * - Signing nonce :math:`k`
     - yes
     - random, or derived from key and message
     - Two signatures reveal the private key.
   * - Account nonce
     - no
     - counts up by one
     - A copied transaction is spent again (a replay).
   * - Proof-of-work nonce
     - no
     - searched
     - Nothing: it only has to make the hash small.
   * - Salt
     - until opened
     - random
     - Equal messages get equal commitments, which can be guessed.

All snippets use ``import blockchainkit as bk``.

The signing nonce: secret and fresh
-----------------------------------

A Schnorr signature is :math:`(R, s)` with :math:`R = kG` and
:math:`s = k + c x`, where :math:`x` is the private key and :math:`c` a hash of
the message. The nonce :math:`k` hides :math:`x` in :math:`s`, as a one-time
pad would. Use it twice and the pad cancels out:

.. doctest::

   >>> curve = bk.crypto.TOY_CURVE
   >>> public = bk.crypto.public_key(7, curve)
   >>> first = bk.crypto.sign(b"pay Bob 5", 7, nonce=3, curve=curve)
   >>> second = bk.crypto.sign(b"pay Eve 9", 7, nonce=3, curve=curve)
   >>> c1 = bk.crypto.challenge(b"pay Bob 5", first.commitment, public, curve)
   >>> c2 = bk.crypto.challenge(b"pay Eve 9", second.commitment, public, curve)
   >>> c1 != c2 and bk.crypto.recover_reused_nonce_key(first, second, c1, c2, curve.order)
   7

This is how Sony's PlayStation 3 signing key leaked in 2010. RFC 6979 removes
the need for a random number generator by deriving :math:`k` from the key and
the message, so the same message gets the same nonce (harmless: the same
signature) and different messages get different ones:

.. doctest::

   >>> k1 = bk.crypto.deterministic_nonce(7, b"pay Bob 5")
   >>> k1 == bk.crypto.deterministic_nonce(7, b"pay Bob 5")
   True
   >>> k1 != bk.crypto.deterministic_nonce(7, b"pay Eve 9")
   True

See :doc:`/api/gallery/crypto/signatures/plot_04_nonce_reuse`.

The account nonce: public and sequential
----------------------------------------

In an account-based ledger, a signed transfer is just bytes. Anyone who sees it
could submit it again. The account nonce is a public counter inside the signed
message: the ledger accepts a transaction only if its nonce equals the sender's
current count, then increments the count.

.. doctest::

   >>> alice_public = bk.crypto.public_key(7)
   >>> alice = bk.structures.address(alice_public)
   >>> bob = bk.structures.address(bk.crypto.public_key(11))
   >>> ledger = bk.structures.Ledger({alice: 100})
   >>> payment = bk.structures.Transaction(alice_public, bob, 25, 0).signed(7, signing_nonce=17)
   >>> after = ledger.apply([payment])
   >>> after.nonces[alice], after.balances[bob]
   (1, 25)
   >>> try:
   ...     after.apply([payment])
   ... except ValueError as error:
   ...     print("replay rejected")
   replay rejected

Note the two nonces in that one line: ``0`` is the account nonce, public and
predictable; ``signing_nonce=17`` is the signing nonce, which in real use must
be secret and never repeated. Bitcoin needs no account nonce, because each coin
can be spent only once: see :doc:`/api/gallery/structures/utxo/plot_01_utxo`.

The proof-of-work nonce: a lottery ticket
-----------------------------------------

A block's header has a free field that miners change until the header's hash
falls below a target. The nonce carries no meaning; it only makes each attempt
different.

.. doctest::

   >>> result = bk.consensus.mine(bk.structures.Block(difficulty=8))
   >>> result.block.nonce == result.attempts - 1  # Tried 0, 1, 2, ... in turn.
   True
   >>> bk.consensus.valid_pow(result.block)
   True
   >>> bk.consensus.expected_trials(8)
   256

Reusing a proof-of-work nonce is harmless: another block with other contents
has a different hash. See :doc:`/api/gallery/consensus/pow/plot_02_hashcash`.

The salt: randomness that hides
-------------------------------

A commitment :math:`H(\text{salt} \| m)` hides :math:`m` only if the salt is
unpredictable. Without one, anyone can try the likely messages:

.. doctest::

   >>> import secrets
   >>> salt = secrets.token_bytes(16)
   >>> sealed = bk.crypto.commit(b"heads", salt)
   >>> bk.crypto.verify_commitment(sealed, b"heads", salt)
   True
   >>> unsalted = bk.crypto.sha256(b"heads")
   >>> [guess for guess in (b"heads", b"tails") if bk.crypto.sha256(guess) == unsalted]
   [b'heads']

Compact blocks use a per-block salt for the same reason: it stops an attacker
from precomputing colliding short IDs (see
:doc:`/api/gallery/network/relay/plot_03_compact_blocks`).

Check yourself
--------------

* Which nonce appears in the signed bytes of a transaction, and which one
  never leaves the signer's machine?
* Why does a hardware wallet need a good random number generator, or RFC 6979,
  but a miner does not?
* A transaction is broadcast, dropped, and broadcast again. Which nonce stops
  it being applied twice?
