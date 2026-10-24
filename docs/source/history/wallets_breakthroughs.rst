Breakthroughs in Wallets and Key Handling
=========================================

.. include:: /_generated/nav/wallets.rst

.. epigraph::

   "Your keys, your bitcoin. Not your keys, not your bitcoin."
   -- Andreas M. Antonopoulos, 2017

A *cryptocurrency* is digital money. Its record of who owns what is kept on a
*blockchain*: a shared record, like a Python list of blocks of transactions.
Many computers keep copies of it in step, and nobody can quietly edit an old
entry. *Cryptography* is the mathematics of keeping and checking secrets.

Whoever holds the right secret number can spend the coins. So most of the
money lost in cryptocurrencies is not lost to broken cryptography. It is
lost to the way people handle their secrets:

- **a typo** in an address sends a payment nowhere, or to someone else;
- **a guessable secret**, such as a passphrase from a song, is guessed;
- **a lost backup** loses the coins for good;
- **a single point of failure**, one key on one laptop, fails.

A *wallet* is the program, or the habit, that holds a user's secrets. This
chronology follows how wallets learned to defend against each of these. It
runs from the error-detecting codes behind addresses, through stretching
passwords and deriving whole trees of keys from one backup, to sharing
control of a key among several people or devices.

A few terms recur on every page:

- A *key pair* is a secret number, the *private key*, and a public number
  computed from it, the *public key*. Here keys live on *secp256k1*, the
  elliptic curve of Bitcoin and Ethereum: the public key is the point
  :math:`K = kG`, a fixed point :math:`G` added to itself :math:`k` times.
  Computing :math:`K` from :math:`k` is fast; the reverse is infeasible.
- A *digital signature* is a value only the private key could produce, but
  that anyone can check with the public key.
- A *hash function* is like Python's ``hash()``, but built so that nobody can
  find two inputs with the same output, or an input with a chosen output.
  SHA-256 is the standard one. *HMAC* is a hash keyed by a secret.
- An *address* is a short public name for a key or a script, like an account
  number: usually a hash of it, written in a form people can copy.
- A *smart contract* (or just *contract*) is a program stored on a
  blockchain at its own address. Anyone can call its functions by sending a
  transaction. *Ethereum* is the main blockchain for contracts, and *ether*
  is its currency.

Several neighbours live elsewhere: Shamir's and Feldman's secret sharing
and MuSig are in :doc:`crypto_breakthroughs`, Bitcoin Script and P2PKH in
:doc:`vm_breakthroughs`, the Parity multisig wallets in
:doc:`contracts_breakthroughs`, and address poisoning in
:doc:`fraud_breakthroughs`. Those pages explain their own terms.

The models in :mod:`blockchainkit.wallets` come in three kinds:

- *pure functions*, whose output depends only on their input. Where a
  standard exists (Base58Check, Bech32, PBKDF2, scrypt, BIP32, BIP39's seed
  derivation, ECDSA) they reproduce its published test vectors;
- small *seeded simulations*, random but reproducible, as after
  ``random.seed(0)``;
- contracts on :class:`~blockchainkit.contracts.systems.world.World`, a
  Python model of Ethereum.

:doc:`/protocol` lists where the models depart from deployed systems.

.. contents:: Timeline
   :local:
   :depth: 1

1959-1960 -- BCH Codes: Correcting Errors with Polynomials
----------------------------------------------------------

A message sent over a noisy line arrives with some bits flipped. An
*error-correcting code* adds redundant bits, so that the receiver can find
and undo the flips. Alexis Hocquenghem in 1959, and independently Raj
Chandra Bose and Dijen Ray-Chaudhuri in 1960, found how to build binary
codes that correct any chosen number :math:`t` of flipped bits.

The trick is to treat a word of bits as a polynomial, bit :math:`i` being
the coefficient of :math:`x^i`:

#. Work in a finite field GF(:math:`2^m`), a set of :math:`2^m` numbers with
   addition and multiplication. One element, :math:`\alpha`, generates all
   the others as its powers.
#. Pick a *generator polynomial* :math:`g(x)` whose roots include
   :math:`\alpha, \alpha^2, \ldots, \alpha^{2t}`.
#. The *codewords* are the multiples of :math:`g(x)`, of length
   :math:`n = 2^m - 1`. To encode, append to the message the remainder that
   makes it a multiple.

Any two codewords then differ in at least

.. math::

   d \ge 2t + 1

bits (the BCH bound). So a received word with at most :math:`t` errors is
closer to its own codeword than to any other.

- **Decoding** evaluates the received word at :math:`\alpha^j`. A codeword
  gives zero; the nonzero values, the *syndromes*, depend only on where the
  errors are. The Berlekamp-Massey algorithm turns them into a polynomial
  whose roots name the error positions.
- **Beyond t errors** the decoder may give up, or worse, "correct" the word
  to a different codeword.
- Bech32 addresses, in the 2017 entry, use a BCH code over GF(32) to detect,
  rather than correct, a person's typos.

*Implementation:* :class:`blockchainkit.wallets.systems.bch.BCHCode` builds
narrow-sense binary BCH codes for :math:`3 \le m \le 8` over
:class:`blockchainkit.wallets.utils.galois.GaloisField`, with systematic
encoding, syndromes, Berlekamp-Massey and Chien's search. Only binary codes
are built; the Reed-Solomon codes of :doc:`channels_breakthroughs` are their
non-binary cousins.

*References:* A. Hocquenghem, *Codes correcteurs d'erreurs*, Chiffres 2,
147–156 (1959); R. C. Bose and D. K. Ray-Chaudhuri, *On a class of error
correcting binary group codes*, Information and Control 3(1), 68–79 (1960).
`DOI <https://doi.org/10.1016/S0019-9958(60)90287-4>`__; J. L. Massey,
*Shift-register synthesis and BCH decoding*, IEEE Transactions on
Information Theory 15(1), 122–127 (1969).

.. minigallery:: ../../examples/wallets/codes/plot_01_bch_codes.py

1969 -- Verhoeff's Check Digit and Detecting Transpositions
-----------------------------------------------------------

A *check digit* is one extra digit appended to a number, such as an
account number, so that a number copied with a mistake fails a test.
Jacobus Verhoeff studied the mistakes Dutch clerks actually made. Most were
one wrong digit; most of the rest were two neighbouring digits swapped, as
in 1243 for 1234.

- **Adding the digits** modulo 10 catches every wrong digit, but no swap:
  addition does not care about order.
- **Luhn's scheme** (1954), still on payment cards, doubles every second
  digit. It catches every swap except 09 and 90.
- **Verhoeff's scheme** catches every wrong digit and every swap.

Verhoeff's insight was to compute in a group where order matters. The ten
symmetries of a regular pentagon, five rotations and five reflections, form
the *dihedral group* :math:`D_5`. Composing two of them depends on the
order: rotate then reflect is not reflect then rotate. Label them 0 to 9 and
write :math:`a * b` for their composition. Then:

#. Permute each digit by a fixed permutation :math:`\sigma`, applied
   :math:`i` times for the digit in position :math:`i` from the right.
#. Choose the check digit :math:`a_0` so that

.. math::

   \sigma^{0}(a_0) * \sigma^{1}(a_1) * \cdots * \sigma^{k}(a_k) = 0 .

A swap of neighbours changes the product, because neither the group nor the
permutation lets the two digits trade places unnoticed. Addresses, in the
next entries, protect a whole string the same way, with a checksum.

*Implementation:* :func:`blockchainkit.wallets.systems.check_digits.verhoeff_digit`,
:func:`blockchainkit.wallets.systems.check_digits.luhn_digit` and
:func:`blockchainkit.wallets.systems.check_digits.detection_rates`, which
measures each scheme against every single error and adjacent swap of
every short number. The :math:`D_5` table is computed from the
pentagon's symmetries rather than copied.

*References:* J. Verhoeff, *Error Detecting Decimal Codes*, Mathematical
Centre Tracts 29, Mathematisch Centrum, Amsterdam (1969); H. P. Luhn,
*Computer for verifying numbers*, US Patent 2,950,048 (filed 1954, granted
1960).

.. minigallery:: ../../examples/wallets/codes/plot_02_verhoeff_check_digit.py

2000 -- PBKDF2: Stretching Passwords into Keys
----------------------------------------------

A password makes a poor key. People choose a few thousand likely
passwords, and an attacker who can test guesses offline simply tries them
all. Burt Kaliski's PBKDF2, published as RFC 2898, cannot make a password
less guessable, but it can make every guess expensive:

#. Mix in a *salt*, a random value stored with the result. Two users with
   the same password get different keys, and the attacker cannot reuse one
   table of precomputed guesses for everyone.
#. Iterate a keyed hash :math:`c` times, adding up the results with XOR:

.. math::

   U_1 = \mathrm{HMAC}(P, S \,\|\, 1), \quad
   U_j = \mathrm{HMAC}(P, U_{j-1}), \quad
   T = U_1 \oplus U_2 \oplus \cdots \oplus U_c .

The honest user pays :math:`c` HMAC calls once, at login. An attacker
trying :math:`N` passwords pays :math:`N c`.

- **Stretching buys a fixed factor.** 100,000 iterations make a six-digit
  PIN as costly as an unstretched eleven-digit one; it does not make a
  six-digit PIN safe.
- **It needs almost no memory**, so a graphics card or custom chip runs
  thousands of guesses side by side. scrypt, in the second 2009 entry,
  attacks that.
- BIP39 seed phrases, in the 2013 entry, are stretched with PBKDF2.

*Implementation:* :func:`blockchainkit.wallets.systems.stretching.pbkdf2`
(HMAC with SHA-1, SHA-256 or SHA-512, checked against RFC 6070's vectors and
``hashlib``) and :func:`blockchainkit.wallets.systems.stretching.crack_pin`,
which counts the attacker's HMAC calls.

*References:* B. Kaliski, *PKCS #5: Password-Based Cryptography
Specification Version 2.0*, RFC 2898 (September 2000); S. Josefsson,
*PKCS #5: PBKDF2 Test Vectors*, RFC 6070 (January 2011).

.. minigallery:: ../../examples/wallets/stretching/plot_01_pbkdf2_key_stretching.py

2009 -- Base58Check Addresses
-----------------------------

In Bitcoin's first release, an address names a public key by its hash,
written so that people can copy it. Its parts are:

#. a *version byte*, 0 for an ordinary Bitcoin address;
#. the 20-byte ``HASH160`` of the public key, which is
   :math:`\mathrm{RIPEMD160}(\mathrm{SHA256}(K))`;
#. a 4-byte *checksum*: the first bytes of SHA-256 applied twice to the
   first two parts.

The result is written in *base 58*: the digits and letters, without 0, O, I
and l, which are easily confused. Each leading zero byte is written as a
leading ``1``, so ordinary addresses start with 1.

A wallet refuses an address whose checksum fails. A typo slips through only
if the changed address happens to match its own checksum, with probability

.. math::

   2^{-32} \approx 2.3 \times 10^{-10} .

- **Without a checksum**, every typo is a valid address. The account names
  of :mod:`blockchainkit.structures` are bare SHA-256 hex digests, where a
  typo silently pays a stranger, or nobody.
- **A hash promises nothing in particular.** It catches most errors, but no
  class of errors is guaranteed, and it cannot say where a typo is. Bech32
  will improve on both.
- Base58Check also writes private keys and the extended keys of the 2012
  entry.

*Implementation:* :func:`blockchainkit.wallets.systems.base58.base58check_encode`,
:func:`blockchainkit.wallets.systems.base58.base58check_decode` and
:func:`blockchainkit.wallets.systems.base58.p2pkh_address`, with
RIPEMD-160 written out in :func:`blockchainkit.wallets.utils.ripemd160.hash160`
since ``hashlib`` does not always provide it. Addresses match Bitcoin's:
private key 1 gives ``1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH``.

*References:* S. Nakamoto, Bitcoin v0.1 source code, ``base58.h`` (January
2009); H. Dobbertin, A. Bosselaers and B. Preneel, *RIPEMD-160: A
strengthened version of RIPEMD*, Fast Software Encryption, LNCS 1039,
71–82 (1996).

.. minigallery:: ../../examples/wallets/addresses/plot_01_base58check_addresses.py

2009 -- scrypt and Memory-Hard Key Derivation
---------------------------------------------

PBKDF2 makes a guess slow, but a guess fits in a few hundred bytes. So an
attacker builds a chip with thousands of tiny guessing circuits. Colin
Percival's scrypt makes each guess need a large amount of memory as well.
Memory costs chip area, so parallel guessing gets expensive.

Its core, ROMix, works on a block :math:`B` and a table of :math:`N`
entries:

#. Fill the table: each entry is a scrambled version of the last,
   :math:`V_i = \mathrm{BlockMix}^{\,i}(B)`.
#. Then make :math:`N` reads, each at an address that depends on the
   current value:

.. math::

   X \leftarrow \mathrm{BlockMix}(X \oplus V_{\mathrm{Integerify}(X) \bmod N}).

The attacker cannot know in advance which entries will be needed.

- **Keeping the whole table** costs :math:`N` entries of memory and
  :math:`2N` BlockMix calls.
- **Keeping only every k-th entry** saves memory, but each missing entry
  must be recomputed from the last kept one, about :math:`k/2` calls a
  read. Memory times time stays roughly constant.
- Percival proved that no strategy does much better. So an attack's cost,
  in chip area times time, grows with :math:`N^2` rather than :math:`N`.
  Litecoin and many wallets adopted scrypt.

*Implementation:* :func:`blockchainkit.wallets.systems.scrypt.scrypt`
implements RFC 7914 exactly, from
:func:`blockchainkit.wallets.systems.scrypt.salsa20_8` and
:func:`blockchainkit.wallets.systems.scrypt.block_mix`;
:func:`blockchainkit.wallets.systems.scrypt.romix` adds a ``keep_every``
parameter that stores fewer entries and counts the cost. Parameters are
small enough to run in pure Python.

*References:* C. Percival, *Stronger key derivation via sequential
memory-hard functions*, BSDCan (2009); C. Percival and S. Josefsson, *The
scrypt Password-Based Key Derivation Function*, RFC 7914 (August 2016).

.. minigallery:: ../../examples/wallets/stretching/plot_02_scrypt_memory_hardness.py

2012 -- Pay-to-Script-Hash and Multisig Wallets
-----------------------------------------------

One key on one device is one point of failure: lose it, or let it be
copied, and the coins are gone. A coin locked to *2 of 3* keys survives
either. Bitcoin could do this from the start, with a locking script listing
all three keys. But the payer had to write that script into the payment,
and pay a fee for its size, for a policy that was the payee's business.

Gavin Andresen's BIP16, *pay to script hash* (P2SH), moved the script to
the spender:

#. The payee writes a *redeem script*, say "2 of these 3 keys", and gives
   out only its hash, as an address starting with 3.
#. The coin is locked by a short script that only checks that hash:

.. math::

   \texttt{OP\_HASH160}\ \langle H(\text{redeem}) \rangle\ \texttt{OP\_EQUAL} .

#. To spend, the owners reveal the redeem script and their signatures.
   Validation runs in two stages: first the revealed script must hash to
   the locked value, then it runs on the signatures.

- **The policy stays private** until the coin is spent, and the payer's
  fee no longer depends on it.
- **Multisig became routine**: exchanges' cold storage, escrow, and
  wallets that split keys between a phone and a server.
- **The redeem script is capped** at 520 bytes, the largest data push,
  which bounds how many keys it can list.

*Implementation:* :func:`blockchainkit.wallets.systems.p2sh.verify_p2sh`
(the two stages, over :func:`blockchainkit.vm.systems.script.verify_script`),
:func:`blockchainkit.wallets.systems.p2sh.multisig_redeem_script` and
:func:`blockchainkit.wallets.systems.p2sh.serialize_script` (Bitcoin's opcode
bytes and push prefixes). The teaching Script has no ``OP_HASH160`` or
``OP_CHECKMULTISIG``, so the hash is ``OP_HASH256`` and m-of-n is one
``OP_IF`` branch per set of m signers; 2-of-3 fits in 520 bytes, 2-of-4 does
not.

*References:* G. Andresen, *BIP 16: Pay to Script Hash* (January 2012);
G. Andresen, *BIP 11: M-of-N Standard Transactions* (2011).

.. minigallery:: ../../examples/wallets/custody/plot_01_p2sh_multisig.py

2012 -- Hierarchical Deterministic Wallets (BIP32)
--------------------------------------------------

Early Bitcoin wallets drew each new key at random. A backup held only the
keys made so far, so a backup from last month could miss this week's
payments. Pieter Wuille's BIP32 derives a whole tree of keys from one seed,
so one backup, made once, covers every key the wallet will ever use.

An *extended key* is a private key :math:`k` together with 32 extra bytes,
its *chain code* :math:`c`. Child number :math:`i` is made by hashing:

.. math::

   I = \mathrm{HMAC\text{-}SHA512}(c,\ K \,\|\, i), \qquad
   k_i = I_L + k \bmod n, \qquad c_i = I_R ,

where :math:`I_L` and :math:`I_R` are the two halves of the 64-byte
result, and :math:`K = kG` is the parent's public key.

- **Public derivation.** Since :math:`k_i G = I_L G + K`, anyone with the
  parent's public key and chain code, its *extended public key* or *xpub*,
  can compute every child's public key, but no private key. A shop's web
  server can hand out a fresh address per order and hold nothing worth
  stealing.
- **The catch.** The xpub and the private key of any one such child give
  away the parent: :math:`k = k_i - I_L`. Then every sibling falls too.
- **Hardened children**, numbered from :math:`2^{31}` and written
  :math:`i'`, hash the parent's *private* key instead. They cannot be
  derived from an xpub, and do not leak their parent. Accounts are
  hardened for that reason.

*Implementation:* :func:`blockchainkit.wallets.systems.hd.master_key`,
:func:`blockchainkit.wallets.systems.hd.derive_private`,
:func:`blockchainkit.wallets.systems.hd.derive_public`,
:func:`blockchainkit.wallets.systems.hd.serialize_extended_key` (``xprv`` and
``xpub`` strings) and
:func:`blockchainkit.wallets.systems.hd.recover_parent_private`, the leaked
xpub attack. It reproduces BIP32's first test vector on secp256k1.

*References:* P. Wuille, *BIP 32: Hierarchical Deterministic Wallets*
(February 2012).

.. minigallery:: ../../examples/wallets/derivation/plot_01_bip32_hd_wallets.py

2013 -- Mnemonic Seed Phrases (BIP39)
-------------------------------------

A 128-bit seed written in hexadecimal is 32 characters such as
``0c1e24e5917779d2...``, which people miscopy. Marek Palatinus, Pavol
Rusnak, Aaron Voisine and Sean Bowe proposed writing it as words:

#. Take 128 to 256 bits of random *entropy*.
#. Append a checksum: the first ENT/32 bits of its SHA-256.
#. Cut the bits into groups of 11. Each group is a number from 0 to 2047,
   and picks a word from a fixed list of 2048.

So

.. math::

   \frac{ENT + ENT/32}{11} \text{ words}: \qquad
   128 \text{ bits} \to 12 \text{ words}, \quad 256 \text{ bits} \to 24 .

- **A miscopied word** changes 11 bits, and the 4-bit checksum of a 12-word
  phrase catches it 15 times in 16.
- **The seed** for BIP32 comes from stretching the phrase with PBKDF2
  (HMAC-SHA512, 2048 iterations), salted with ``"mnemonic"`` plus an
  optional passphrase.
- **Every passphrase is valid** and gives a different wallet. That allows
  a decoy wallet under duress, but a mistyped passphrase opens an empty
  wallet without any error.

The phrase is the whole wallet. Written on paper it is safe from hackers
and exposed to fire, burglars and heirs who do not know what it is.

*Implementation:* :func:`blockchainkit.wallets.systems.mnemonics.entropy_to_mnemonic`,
:func:`blockchainkit.wallets.systems.mnemonics.mnemonic_to_entropy` and
:func:`blockchainkit.wallets.systems.mnemonics.mnemonic_to_seed`. The word
list is 2048 four-letter words generated by a rule, not BIP39's English
list, so phrases differ from real wallets'; the seed derivation is BIP39's
own and reproduces its test vectors for English phrases.

*References:* M. Palatinus, P. Rusnak, A. Voisine and S. Bowe, *BIP 39:
Mnemonic code for generating deterministic keys* (September 2013).

.. minigallery:: ../../examples/wallets/derivation/plot_02_bip39_mnemonic_seed_phrases.py

2014 -- Multi-Account Derivation Paths (BIP44)
----------------------------------------------

BIP32 allows any tree of keys. So a seed backed up from one wallet program
could restore an empty-looking wallet in another, which looked in other
branches. Marek Palatinus and Pavol Rusnak fixed where keys sit, with five
levels:

.. math::

   m / 44' / \text{coin}' / \text{account}' / \text{change} / \text{index}

- **purpose** 44, hardened, names this scheme;
- **coin type**, hardened: 0 for Bitcoin, 60 for Ether;
- **account**, hardened, like separate bank accounts;
- **change**: 0 for addresses given out to receive payments, 1 for the
  wallet's own change;
- **index**, counting addresses from 0.

A restoring wallet cannot know how many addresses were used, so it scans:

#. On each account's receiving chain, derive addresses in order until 20 in
   a row have never been used. That number is the *gap limit*.
#. Stop at the first account with no used address at all.

A wallet that handed out more than 20 unpaid addresses in a row has made
later payments invisible to any other wallet restoring the seed. The coins
are safe, but nobody looks for them.

*Implementation:* :func:`blockchainkit.wallets.systems.paths.derive_path`,
:func:`blockchainkit.wallets.systems.paths.parse_path` and
:func:`blockchainkit.wallets.systems.paths.discover_accounts`, which scans
P2PKH addresses with a chosen gap limit. Only the receiving chain is
scanned, as BIP44 specifies.

*References:* M. Palatinus and P. Rusnak, *BIP 44: Multi-Account Hierarchy
for Deterministic Wallets* (April 2014).

.. minigallery:: ../../examples/wallets/derivation/plot_03_bip44_derivation_paths.py

2016 -- The Brain-Wallet Drain
------------------------------

A *brain wallet* keeps no file. Its private key is the hash of a passphrase
the owner remembers:

.. math::

   k = \mathrm{SHA256}(\text{passphrase}) .

The appeal is that the coins can be carried across a border in one's head.
The flaw is that anyone can hash the same passphrase. Marie Vasek, Joseph
Bonneau, Ryan Castellucci, Cameron Keith and Tyler Moore searched the
Bitcoin blockchain for brain wallets by hashing billions of candidate
phrases. They found that:

- **thieves had done the same**, hashing dictionaries, quotations, lyrics
  and leaked passwords, and keeping a table from address to key;
- **most funded brain wallets were emptied**, many within minutes of the
  first deposit;
- **thieves raced one another** to sweep the same wallets.

Nothing slows the thieves. There is no salt, so one table serves every
victim, and no stretching. And a phrase a person picks, even an obscure
one, has far less entropy than the 128 bits of a random key.

*Implementation:* :func:`blockchainkit.wallets.systems.brainwallets.brain_wallet_key`,
:func:`blockchainkit.wallets.systems.brainwallets.crack_brain_wallet` and
:func:`blockchainkit.wallets.systems.brainwallets.simulate_brain_drain`, a
seeded race of thieves with precomputed tables of a small
:data:`~blockchainkit.wallets.systems.brainwallets.PHRASEBOOK`. Keys and
addresses are real (``"password"`` gives
``16ga2uqnF1NqpAuQeeg7sTCAdtDUwDyJav``); the population and the thieves'
delays are invented.

*References:* M. Vasek, J. Bonneau, R. Castellucci, C. Keith and T. Moore,
*The Bitcoin brain drain: examining the use and abuse of bitcoin brain
wallets*, Financial Cryptography and Data Security 2016, LNCS 9603
(2017).

.. minigallery:: ../../examples/wallets/stretching/plot_03_brain_wallet_drain.py

2017 -- Bech32 Addresses (BIP173)
---------------------------------

Segregated witness, activated in 2017, needed a new address format, and
Pieter Wuille and Gregory Maxwell took the chance to design one for people
rather than computers. A *Bech32* string is:

#. a human-readable part such as ``bc`` for Bitcoin;
#. the separator ``1``;
#. data in 32 characters, all lower case, chosen to avoid look-alikes;
#. a 6-character checksum.

The checksum is a BCH code over GF(32), as in the 1959-1960 entry. Read the
characters as the coefficients of a polynomial; a valid string leaves a
fixed remainder modulo a generator of degree 6:

.. math::

   \mathrm{polymod}(\mathrm{expand}(hrp) \,\|\, data \,\|\, checksum) = 1 .

- **The code was searched for.** Of 159,605 candidate generators, the one
  chosen detects every error in up to 4 characters, in strings of up to 89
  characters. Base58Check's hash only makes errors unlikely to pass.
- **One case** makes addresses easier to read aloud and to fit in QR codes.
- **Errors can be located**, though wallets are asked not to correct them:
  a corrected address may be a different, valid one.

*Implementation:* :func:`blockchainkit.wallets.systems.bech32.bech32_encode`,
:func:`blockchainkit.wallets.systems.bech32.bech32_decode`,
:func:`blockchainkit.wallets.systems.bech32.segwit_encode` and
:func:`blockchainkit.wallets.systems.bech32.p2wpkh_address`, which pass
BIP173's test vectors: private key 1 gives
``bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4``.

*References:* P. Wuille and G. Maxwell, *BIP 173: Base32 address format
for native v0-16 witness outputs* (March 2017).

.. minigallery:: ../../examples/wallets/addresses/plot_02_bech32_addresses.py

2018 -- Threshold ECDSA (Gennaro and Goldfeder)
-----------------------------------------------

A multisig script, as in the 2012 entry, shows its policy on the chain and
needs one signature per signer. A *threshold signature* is a single,
ordinary signature under a single public key. It is made jointly by any
:math:`t` of :math:`n` parties, each holding a Shamir share of a private key
that nobody ever puts together.

For Schnorr signatures this is easy: responses add, so shares of the key
give shares of the signature (MuSig, in :doc:`crypto_breakthroughs`).
Bitcoin and Ethereum use ECDSA, whose signature

.. math::

   s = k^{-1}(z + r x)

multiplies two secrets, the inverse of the nonce :math:`k` and the key
:math:`x`. Rosario Gennaro and Steven Goldfeder gave a fast protocol for
that:

#. Each party holds a share :math:`k_i` of the nonce and a random mask
   :math:`\gamma_i`.
#. A two-party *multiplicative-to-additive* (MtA) step turns a product of
   secrets held by two parties into a sum, :math:`\alpha + \beta = ab`,
   without revealing them.
#. With MtA the parties get shares of :math:`k\gamma` and of :math:`kx`.
   Revealing :math:`k\gamma` is safe, since :math:`\gamma` hides
   :math:`k`, and it lets them compute :math:`R = k^{-1} G`.
#. Each party's :math:`z k_i + r \sigma_i` adds up to
   :math:`s = k(z + r x)`, an ECDSA signature with nonce :math:`k^{-1}`.

Exchanges and custody companies use threshold ECDSA so that no single
server ever holds a whole key.

*Implementation:* :func:`blockchainkit.wallets.systems.threshold.threshold_keygen`
(each party deals a Shamir sharing with Feldman commitments on secp256k1)
and :func:`blockchainkit.wallets.systems.threshold.threshold_sign`, whose
signatures verify with
:func:`blockchainkit.wallets.systems.ecdsa.ecdsa_verify`. MtA is an ideal
function (:func:`blockchainkit.wallets.systems.threshold.multiplicative_to_additive`),
not Paillier encryption with range proofs, and nothing checks a cheating
party.

*References:* R. Gennaro and S. Goldfeder, *Fast multiparty threshold ECDSA
with fast trustless setup*, ACM CCS 2018, 1179–1194.
`DOI <https://doi.org/10.1145/3243734.3243859>`__

.. minigallery:: ../../examples/wallets/custody/plot_02_threshold_ecdsa.py

2020 -- Bech32m and a Checksum Flaw (BIP350)
--------------------------------------------

In 2019 a blind spot was found in Bech32. When a string ends in ``p``,
inserting or deleting ``q`` characters just before that ``p`` leaves the
checksum valid.

The reason is algebraic:

- ``q`` stands for the value 0, and ``p`` for 1.
- The checksum asks that the remainder equal 1, the very value ``p`` adds.
- Inserting zeros before the last value multiplies part of the polynomial by
  a power of :math:`x` without changing the remainder.

Segregated-witness version 0 was safe by luck: its programs must be exactly
20 or 32 bytes, so an inserted character makes a wrong length. But Taproot,
witness version 1, and later versions allow other lengths. Pieter Wuille's
*Bech32m* changes only the constant:

.. math::

   \mathrm{polymod}(\mathrm{expand}(hrp) \,\|\, data \,\|\, checksum) =
   \texttt{0x2bc830a3} .

With an irregular constant, appended zeros change the remainder. Bech32m is
required from witness version 1 on, and Bech32 stays for version 0.

*Implementation:* the ``encoding`` argument of
:func:`blockchainkit.wallets.systems.bech32.bech32_encode`, and
:func:`blockchainkit.wallets.systems.bech32.segwit_decode`, which demands
Bech32 for version 0 and Bech32m after, passing BIP350's test vectors.

*References:* P. Wuille, *BIP 350: Bech32m format for v1+ witness
addresses* (December 2020).

.. minigallery:: ../../examples/wallets/addresses/plot_03_bech32m_checksum_flaw.py

2021 -- Social-Recovery Wallets
-------------------------------

A single seed phrase fails twice over: lose it and the coins are gone; let
it be copied and they are stolen. Vitalik Buterin argued for wallets that
need no seed-phrase backup at all. A *social-recovery wallet* is a contract
with:

- one *signing key*, for everyday payments;
- a set of :math:`n` *guardians*: friends, family, the owner's other
  devices, or institutions;
- a rule that any :math:`m` guardians together can replace the signing
  key.

If the owner loses the key, the guardians move the wallet to a new one. If
a thief copies the key, the guardians move it away from the thief. Changes
to the guardians themselves are delayed, so that a thief with the key
cannot replace them first.

How to choose :math:`m`? Say each guardian is independently lost with
probability :math:`p_l`, or corrupt with probability :math:`p_c`. The
wallet is stolen when :math:`m` guardians are corrupt:

.. math::

   P(\text{theft}) = \sum_{j \ge m} \binom{n}{j} p_c^{\,j} (1 - p_c)^{n-j} .

It is locked for good when fewer than :math:`m` are honest and reachable. A
higher threshold lowers the risk of theft and raises the risk of lockout.
With 5 guardians and a threshold of 3, both risks can be far below those of
one seed phrase.

*Implementation:* :class:`blockchainkit.wallets.systems.social_recovery.SocialRecoveryWallet`,
a contract on :class:`~blockchainkit.contracts.systems.world.World` with a
delay on guardian changes, and
:func:`blockchainkit.wallets.systems.social_recovery.recovery_risk`. Guardians
vote by sending transactions rather than signing messages, and the wallet
holds only ether.

*References:* V. Buterin, *Why we need wide adoption of social recovery
wallets*, vitalik.ca (11 January 2021).

.. minigallery:: ../../examples/wallets/custody/plot_03_social_recovery_wallets.py

2021 -- Account Abstraction (ERC-4337)
--------------------------------------

Ethereum has two kinds of account:

- an account controlled by a key pair can start transactions, but its
  rules are fixed: one ECDSA key, and fees paid in ether;
- a contract account can follow any rule written in code, but cannot start
  a transaction.

So a social-recovery or multisig wallet needed a separate key-pair account
to pay its fees. Changing the protocol to merge the two was proposed many
times. ERC-4337, by Vitalik Buterin, Yoav Weiss and others, does it with
contracts alone:

#. The owner signs a *user operation*, saying what the account should do,
   and sends it to a separate pool.
#. A *bundler* collects operations and submits them in one ordinary
   transaction to a single *EntryPoint* contract.
#. For each operation the EntryPoint asks the account's own code to
   *validate* it, checking the signature and nonce by whatever rule the
   account chooses, and to pay its fee.
#. Then it runs each operation, and pays the fees to the bundler.

The owner signs a hash that names the EntryPoint and the chain,

.. math::

   h = \mathrm{SHA256}(\text{domain} \,\|\, \text{EntryPoint} \,\|\,
   \text{chain} \,\|\, \text{operation}),

so an operation cannot be replayed elsewhere. A failing validation would
revert the whole bundle at the bundler's cost, so bundlers simulate each
operation first and drop the failures. Since validation is code, an
account can rotate its key, batch payments, or plug in social recovery. The
EntryPoint went live on Ethereum in March 2023.

*Implementation:* :class:`blockchainkit.wallets.systems.account_abstraction.EntryPoint`,
:class:`blockchainkit.wallets.systems.account_abstraction.SmartAccount`
(Schnorr-signed, with key rotation and batches) and
:func:`blockchainkit.wallets.systems.account_abstraction.bundle`, which
simulates on :meth:`~blockchainkit.contracts.systems.world.World.fork`. Fees
are fixed amounts rather than gas times price, and there are no paymasters,
aggregators or account factories.

*References:* V. Buterin, Y. Weiss, D. Tirosh, S. Nacson, A. Forshtat,
K. Gazso and T. Hess, *ERC-4337: Account Abstraction Using Alt Mempool*,
Ethereum Improvement Proposals (September 2021).

.. minigallery:: ../../examples/wallets/custody/plot_04_erc4337_account_abstraction.py
