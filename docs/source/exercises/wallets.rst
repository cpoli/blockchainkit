Exercises: wallets
==================

Each problem comes from the exercise at the end of a gallery example. Try it
in the example's notebook first, then open the solution. Every solution is
run by the documentation build, so its code is known to work.

1. A code that corrects three errors
------------------------------------

From :doc:`/api/gallery/wallets/codes/plot_01_bch_codes`. How many message
bits does a BCH code of length 31 keep if it must correct three errors?

.. dropdown:: Solution

   Length 31 is :math:`2^5 - 1`, so the field is GF(32). The generator is
   the product of the minimal polynomials of :math:`\alpha`,
   :math:`\alpha^3` and :math:`\alpha^5` (the even powers share them), each
   of degree 5, so 15 check bits leave 16.

   .. doctest::

      >>> code = bk.wallets.BCHCode(5, 3)
      >>> code.n, code.k, code.designed_distance
      (31, 16, 7)

2. Luhn's blind spot
--------------------

From :doc:`/api/gallery/wallets/codes/plot_02_verhoeff_check_digit`. Which
pairs of different digits ab can Luhn's scheme not tell from ba?

.. dropdown:: Solution

   Swapping a and b changes the sum by :math:`f(a) - a + b - f(b)`, where
   :math:`f` doubles and subtracts 9 above 4. That is a multiple of 10 only
   for 0 and 9, whose doubles are 0 and 9 again.

   .. doctest::

      >>> [f"{a}{b}" for a in range(10) for b in range(a + 1, 10)
      ...  if bk.wallets.luhn_digit(f"{a}{b}") == bk.wallets.luhn_digit(f"{b}{a}")]
      ['09']

3. Swapped neighbours
---------------------

From :doc:`/api/gallery/wallets/addresses/plot_01_base58check_addresses`.
How many of the typos that swap two neighbouring characters does the
checksum accept?

.. dropdown:: Solution

   None of the 33. The checksum is the first four bytes of a double SHA-256,
   not an error-detecting code: it promises nothing about any kind of typo,
   but lets each one through with probability only :math:`2^{-32}`.

   .. doctest::

      >>> address = bk.wallets.p2pkh_address(bk.crypto.public_key(1))
      >>> swaps = [address[:i] + address[i + 1] + address[i] + address[i + 2 :]
      ...          for i in range(len(address) - 1) if address[i] != address[i + 1]]
      >>> len(swaps), sum(bk.wallets.is_valid_address(s) for s in swaps)
      (33, 0)

4. One case at a time
---------------------

From :doc:`/api/gallery/wallets/addresses/plot_02_bech32_addresses`.
Upper-case the address. Is it still valid? Mix the case. Is it still valid?

.. dropdown:: Solution

   Upper case is valid and decodes to the same program: BIP173 allows it
   because QR codes store capitals more compactly. Mixed case is refused
   before the checksum is checked. The checksum covers the lower-cased
   string, so it could not catch a changed case; refusing mixed case is what
   makes case carry no meaning.

   .. doctest::

      >>> address = bk.wallets.p2wpkh_address(bk.crypto.public_key(1))
      >>> bk.wallets.segwit_decode("bc", address.upper()) == bk.wallets.segwit_decode("bc", address)
      True
      >>> bk.wallets.bech32_decode(address[:10] + address[10:].upper())
      Traceback (most recent call last):
      ...
      ValueError: mixed case

5. Deleting a q
---------------

From :doc:`/api/gallery/wallets/addresses/plot_03_bech32m_checksum_flaw`.
Does deleting a ``q`` before a final ``p`` fool Bech32 too?

.. dropdown:: Solution

   Yes: deleting a zero divides by :math:`x` exactly as inserting one
   multiplies, so both lengths are valid.

   .. doctest::

      >>> text = bk.wallets.bech32_encode("bc", [74 % 32, 74 // 32, 7, 3, 1])
      >>> text
      'bc12z8rpepxuqp'
      >>> bk.wallets.bech32_decode(text[:-2] + "p").data
      (10, 2, 7, 3)

6. Iterations or digits
-----------------------

From :doc:`/api/gallery/wallets/stretching/plot_01_pbkdf2_key_stretching`.
How many iterations make cracking a six-digit PIN cost as many HMAC calls as
cracking an unstretched nine-digit one? What does that say about stretching
against a long, random password?

.. dropdown:: Solution

   A thousand: :math:`10^6 \times 1000 = 10^9`. Each factor of ten in the
   iterations is worth one more digit, so stretching adds only
   :math:`\log_2 c` bits. That rescues a short, human-chosen secret by a few
   digits, and changes nothing for a random 128-bit password, whose
   :math:`2^{128}` guesses no attacker can make anyway. The same trade at a
   size the build can run:

   .. doctest::

      >>> def worst_case(digits, iterations):
      ...     key = bk.wallets.pbkdf2(b"9" * digits, b"salt", iterations, 32)
      ...     return bk.wallets.crack_pin(key, b"salt", iterations, digits).hash_calls
      >>> worst_case(2, 10), worst_case(3, 1)
      (1000, 1000)

7. The cost of a partial table
------------------------------

From :doc:`/api/gallery/wallets/stretching/plot_02_scrypt_memory_hardness`.
Check :math:`N + N(k + 1)/2` against the measured counts.

.. dropdown:: Solution

   Filling the table costs N calls. Each of the N reads then needs
   :math:`j \bmod k` recomputations, about :math:`(k - 1)/2` on average, plus
   its own call. The estimate is close, and gets closer as N grows.

   .. doctest::

      >>> block = bk.wallets.pbkdf2(b"password", b"NaCl", 1, 128)
      >>> for k in (1, 4, 16):
      ...     cost = bk.wallets.romix(block, 256, keep_every=k)[1]
      ...     print(k, cost.block_mixes, 256 + 256 * (k + 1) // 2)
      1 512 512
      4 858 896
      16 2410 2432

8. A stretched famous phrase
----------------------------

From :doc:`/api/gallery/wallets/stretching/plot_03_brain_wallet_drain`.
Brain wallets that stretched their passphrase, such as WarpWallet with
scrypt and PBKDF2, slowed each guess. Why does that still not save a
passphrase from the phrasebook?

.. dropdown:: Solution

   Stretching multiplies the cost of a guess by c, but the thief needs only
   as many guesses as the phrasebook has entries. Here that is 30, and for
   real dictionaries and leaked passwords a few billion: c times a small
   number is still small. Only entropy helps, as a random 12-word phrase has
   128 bits of it.

   .. doctest::

      >>> def stretched(phrase):
      ...     return bk.wallets.pbkdf2(phrase.encode(), b"", 1_000, 32)
      >>> target = stretched("correct horse battery staple")
      >>> next(p for p in bk.wallets.PHRASEBOOK if stretched(p) == target)
      'correct horse battery staple'
      >>> len(bk.wallets.PHRASEBOOK) * 1_000
      30000

9. A hardened child
-------------------

From :doc:`/api/gallery/wallets/derivation/plot_01_bip32_hd_wallets`.
Repeat the attack with a hardened child, ``m/0'/3'``. What stops it?

.. dropdown:: Solution

   A hardened child hashes the parent's *private* key into :math:`I`, so the
   extended public key cannot compute :math:`I_L`, and :math:`I_L` is what
   the attack subtracts. The xpub cannot even derive the child's public key.
   Pretending the index is normal gives a wrong key.

   .. doctest::

      >>> master = bk.wallets.master_key(bytes(range(16)))
      >>> account = bk.wallets.derive_path(master, "m/0'")
      >>> xpub = bk.wallets.neuter(account)
      >>> hardened = 3 + bk.constants.HARDENED_OFFSET
      >>> leaked = bk.wallets.derive_private(account, hardened).private
      >>> bk.wallets.recover_parent_private(xpub, leaked, hardened)
      Traceback (most recent call last):
      ...
      ValueError: a hardened child does not reveal its parent
      >>> bk.wallets.recover_parent_private(xpub, leaked, 3) == account.private
      False

10. A 24-word phrase
--------------------

From :doc:`/api/gallery/wallets/derivation/plot_02_bip39_mnemonic_seed_phrases`.
How many words, and how many checksum bits, encode 256 bits of entropy?

.. dropdown:: Solution

   The checksum is :math:`256 / 32 = 8` bits, and :math:`264 / 11 = 24`
   words. A miscopied word then passes 1 time in 256.

   .. doctest::

      >>> len(bk.wallets.entropy_to_mnemonic(bytes(32)).split())
      24

11. A payment past the gap
--------------------------

From :doc:`/api/gallery/wallets/derivation/plot_03_bip44_derivation_paths`.
The user also pays to address 30 of account 0. What is the smallest gap
limit that finds it?

.. dropdown:: Solution

   Addresses 10 to 29 are unused: a gap of 20. A scan stops after
   ``gap_limit`` unused addresses in a row, so it reaches address 30 only
   with a limit of 21, one more than BIP44's default.

   .. doctest::

      >>> master = bk.wallets.master_key(bytes(range(16)))
      >>> def address(account, index):
      ...     path = bk.wallets.bip44_path(0, account, 0, index)
      ...     return bk.wallets.p2pkh_address(bk.wallets.derive_path(master, path).public)
      >>> used = {address(0, i) for i in (0, 1, 2, 3, 9, 30)} | {address(1, 0)}
      >>> [len(bk.wallets.discover_accounts(master, used, gap_limit=g).found) for g in (20, 21)]
      [6, 7]

12. Which wallets fit
---------------------

From :doc:`/api/gallery/wallets/custody/plot_01_p2sh_multisig`. Which
(m, n) wallets fit in 520 bytes?

.. dropdown:: Solution

   Each branch costs about 68 bytes a key, and there are
   :math:`\binom{n}{m}` branches, so only 2-of-3 and the trivial ones fit.
   With ``OP_CHECKMULTISIG`` a 3-of-5 script lists each of five compressed
   keys once, about :math:`5 \times 34 + 3 = 173` bytes.

   .. doctest::

      >>> sizes = {}
      >>> for n in range(1, 6):
      ...     publics = [bk.crypto.public_key(k) for k in range(2, 2 + n)]
      ...     for m in range(1, n + 1):
      ...         script = bk.wallets.multisig_redeem_script(m, publics)
      ...         sizes[m, n] = len(bk.wallets.serialize_script(script))
      >>> sorted(mn for mn, size in sizes.items() if size <= 520 and 1 < mn[0] < mn[1])
      [(2, 3)]

13. The joint key, assembled
----------------------------

From :doc:`/api/gallery/wallets/custody/plot_02_threshold_ecdsa`. Recover
the joint private key from two shares and check it.

.. dropdown:: Solution

   Lagrange interpolation at 0 turns two shares of a degree-1 polynomial
   into its constant term. The protocol never does this, because whoever
   assembles the key can then sign alone: the point of a threshold key is
   that it exists nowhere.

   .. doctest::

      >>> keys = bk.wallets.threshold_keygen(2, 3, seed=2018)
      >>> shares = dict(keys.shares)
      >>> n = bk.crypto.SECP256K1.order
      >>> x = sum(bk.wallets.lagrange_coefficient(i, (1, 3)) * shares[i] for i in (1, 3)) % n
      >>> bk.crypto.public_key(x) == keys.public
      True

14. The best threshold
----------------------

From :doc:`/api/gallery/wallets/custody/plot_03_social_recovery_wallets`.
Which threshold minimizes the sum of the lockout and theft probabilities for
5 guardians, each lost with probability 0.1 and corrupt with 0.05?

.. dropdown:: Solution

   Theft falls and lockout rises with m. Here 2 of 5 is narrowly best, but 3
   of 5 trades a little lockout risk for twenty times less theft risk, which
   matters more if theft is the worse outcome.

   .. doctest::

      >>> totals = {}
      >>> for m in range(1, 6):
      ...     risk = bk.wallets.recovery_risk(5, m, lost=0.1, corrupt=0.05)
      ...     totals[m] = round(risk.lockout + risk.theft, 4)
      >>> totals
      {1: 0.2263, 2: 0.0248, 3: 0.0278, 4: 0.1648, 5: 0.5563}
      >>> min(totals, key=totals.get)
      2

15. Another chain
-----------------

From :doc:`/api/gallery/wallets/custody/plot_04_erc4337_account_abstraction`.
Sign an operation for another chain ID and submit it. Which check stops it,
and why must the EntryPoint's address be in the hash too?

.. dropdown:: Solution

   The EntryPoint hashes each operation with its own address and chain ID,
   so a signature over any other hash fails the account's signature check,
   and the failed validation reverts the whole bundle. Without the address,
   an operation signed for one EntryPoint would be valid at every other
   EntryPoint on the chain, and an account that trusts two of them, as
   accounts moving to a new EntryPoint version do, could have it run twice.

   .. doctest::

      >>> world = bk.contracts.World()
      >>> entry = world.deploy("deployer", bk.wallets.EntryPoint, name="EntryPoint")
      >>> other = world.deploy("deployer", bk.wallets.EntryPoint, name="EntryPoint 2")
      >>> account = world.deploy("deployer", bk.wallets.SmartAccount, entry, bk.crypto.public_key(7))
      >>> world.fund("alice", 100)
      >>> world.transact("alice", account, value=100).success
      True
      >>> op = bk.wallets.UserOperation(account, 0, "execute", ("bob", 10), 2)
      >>> for signed in (bk.wallets.sign_user_operation(op, 7, entry, "another chain"),
      ...                bk.wallets.sign_user_operation(op, 7, other),
      ...                bk.wallets.sign_user_operation(op, 7, entry)):
      ...     receipt = world.transact("bundler", entry, "handle_ops", [signed], "bundler")
      ...     print(receipt.success, receipt.error and receipt.error.split(": ")[-1])
      False bad signature
      False bad signature
      True None
