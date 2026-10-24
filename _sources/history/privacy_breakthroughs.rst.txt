Breakthroughs in Blockchain Privacy
===================================

.. include:: /_generated/nav/privacy.rst

.. epigraph::

   "Privacy is necessary for an open society in the electronic age."
   -- Eric Hughes, *A Cypherpunk's Manifesto*, 1993

A *cryptocurrency* is digital money. Its record of who owns what is kept on a
*blockchain*: a shared record, like a Python list of blocks of transactions.
Many computers keep copies of it in step, and nobody can quietly edit an old
entry. *Cryptography* is the mathematics of keeping and checking secrets.

Anyone can read a public blockchain. Its *ledger* lists every payment ever
made, with the sending and receiving accounts and the amount, forever. Names
are not written down, but a ledger that cannot be edited is a gift to anyone
patient enough to connect the dots. This chronology follows the two sides:

- **measuring what leaks**: anonymity sets, address clustering, and tracing
  ring signatures;
- **hiding it**: mixes and onion routing for messages; CoinJoin, tumblers and
  mixer contracts for coins; ring signatures and stealth addresses for
  senders and receivers; and commitments for amounts.

A few terms recur on every page:

- A *key pair* is a secret number, the *private key*, and a public number
  computed from it, the *public key*. Here a public key is :math:`g^x \bmod p`
  for a private key :math:`x`, written :math:`g^x`. The owner proves a
  payment is theirs with a *digital signature*: a value that only the private
  key could produce, but that anyone can check with the public key. An
  *address* is a public name for a key, like an account number.
- A *hash function* :math:`H` is like Python's ``hash()``, but built so that
  nobody can find two inputs with the same output, or an input with a chosen
  output.
- A *commitment* is a sealed envelope for a number: it hides the number, and
  it can be opened only to that number. A *Pedersen commitment*
  :math:`g^v h^r` hides :math:`v` behind a random :math:`r`, and two
  commitments multiply into a commitment to the sum.
- A *zero-knowledge proof* convinces a verifier that a statement is true and
  reveals nothing else.
- An *anonymity set* is the set of people who could have done something, as
  far as an observer can tell. Privacy here is measured by its size.

Several neighbours live elsewhere: Chaum's blind signatures and Pedersen
commitments in :doc:`crypto_breakthroughs`, Dandelion's transaction-origin
privacy in :doc:`network_breakthroughs`, and Zerocash and Bulletproofs in
:doc:`proofs_breakthroughs`. Those pages explain their own terms.

The models in :mod:`blockchainkit.privacy` work in the 62-bit teaching group
of :mod:`blockchainkit.crypto`, far too small for real security. They come
as pure functions, small seeded simulations (random but reproducible, as
after ``random.seed(0)``), and one contract on
:class:`~blockchainkit.contracts.systems.world.World`, a Python model of
Ethereum. :doc:`/protocol` lists where the models depart from deployed
systems.

.. contents:: Timeline
   :local:
   :depth: 1

1981 -- Chaum's Mix-Nets: Untraceable Electronic Mail
-----------------------------------------------------

Encryption hides what a message says, but not who sent it to whom. Anyone
watching the network sees the envelope go from Alice to Bob.

David Chaum proposed sending it through a *mix*: a server that hides which
message it received became which message it sent. Messages are wrapped like
nested envelopes, one layer per mix:

#. Alice encrypts the message for Bob, then for the last mix with Bob's
   address inside, then for the mix before it, and so on.
#. Each mix collects a *batch* of messages.
#. It removes its layer from every message. That layer told it only where to
   send the message next.
#. It sends the batch on in a random order.

An observer of every wire sees each message change its bytes and its place
in line at every mix. To follow one message through a cascade of :math:`k`
mixes, it needs every mix's shuffle:

.. math::

   \Pr[\text{link a sender}] =
   \begin{cases} 1 & \text{if all } k \text{ mixes reveal their shuffle,} \\
   1/n & \text{otherwise, for a batch of } n. \end{cases}

Why it works:

- Removing a layer needs the mix's private key, so an outsider cannot
  compare a message before and after a mix.
- One honest mix in the cascade is enough. Its shuffle is unknown, so every
  message it sends could be any message it received.
- Chaum also padded messages to one length, so that sizes could not link
  them.

*Implementation:* :class:`blockchainkit.privacy.systems.mixnets.MixNode`,
:func:`blockchainkit.privacy.systems.mixnets.wrap` and
:func:`blockchainkit.privacy.systems.mixnets.mix_cascade`. Each layer is
hashed ElGamal in the teaching group with a SHA-256 keystream, and layers
grow by the next hop's name; Chaum used RSA and fixed-length messages.

*References:* D. Chaum, *Untraceable Electronic Mail, Return Addresses, and
Digital Pseudonyms*, Communications of the ACM 24(2), 84–90 (1981). `DOI
<https://doi.org/10.1145/358549.358563>`__.

.. minigallery:: ../../examples/privacy/networks/plot_01_chaum_mix_nets.py

2001 -- Ring Signatures: How to Leak a Secret
---------------------------------------------

A member of a cabinet wants to leak a document and prove it comes from the
cabinet, without saying which member leaked it.

Rivest, Shamir and Tauman invented the *ring signature*. The signer lists any
public keys it likes, its own among them, and signs. Anyone can check that
one of the listed keys signed, but not which one. Unlike a group signature,
there is no manager and no setup: the other members need not even know.

The signature is a ring of challenges, one per member. Each challenge is the
hash of the previous member's commitment:

#. The signer :math:`s` picks a random :math:`u` and starts the ring at the
   next member, with challenge :math:`c_{s+1} = H(m, g^u)`.
#. Every other member :math:`i` gets a random response :math:`r_i`, and the
   next challenge is computed from it.
#. Back at itself, the signer closes the ring with its private key
   :math:`x_s`.

.. math::

   c_{i+1} = H\big(m,\; g^{r_i} y_i^{c_i}\big), \qquad r_s = u - x_s c_s .

In words: everyone else's link is made up; only the signer's is real, and
nobody can tell which.

Why it works:

- With :math:`r_s = u - x_s c_s`, the signer's commitment is
  :math:`g^{r_s} y_s^{c_s} = g^u`, so the ring closes on the challenge it
  started from.
- Anyone can recompute the ring from :math:`c_0` and the responses. Making
  it close without any member's private key would mean solving a discrete
  logarithm.
- The responses are uniformly random whoever signed, so they say nothing
  about the signer.

*Implementation:* :func:`blockchainkit.privacy.systems.ring_signatures.ring_sign`
and :func:`blockchainkit.privacy.systems.ring_signatures.ring_verify`. This
is the discrete-log ring signature of Abe, Ohkubo and Suzuki (2002), the
ancestor of Monero's; Rivest, Shamir and Tauman built theirs from RSA
trapdoor permutations and a symmetric cipher.

*References:* R. L. Rivest, A. Shamir and Y. Tauman, *How to Leak a Secret*,
ASIACRYPT 2001, LNCS 2248, 552–565 (2001). `DOI
<https://doi.org/10.1007/3-540-45682-1_32>`__; M. Abe, M. Ohkubo and K.
Suzuki, *1-out-of-n Signatures from a Variety of Keys*, ASIACRYPT 2002, LNCS
2501, 415–432 (2002).

.. minigallery:: ../../examples/privacy/signatures/plot_01_ring_signatures.py

2002 -- k-Anonymity and Anonymity Sets: Measuring How Hidden You Are
--------------------------------------------------------------------

How private is "anonymous" data? Removing names is not enough.

Latanya Sweeney found that a ZIP code, a birth date and a sex single out
most Americans. In 1997 she joined "anonymous" Massachusetts hospital records
to a voter list bought for twenty dollars, and found the Governor's. These
columns are *quasi-identifiers*: harmless alone, identifying together.

She defined a table as *k-anonymous* if every combination of
quasi-identifiers appears in at least :math:`k` rows. Each person then hides
among :math:`k`. A table is made k-anonymous by *generalising*: a ZIP to its
first three digits, a birth date to a decade.

The same year, two groups (Serjantov and Danezis; Díaz, Seys, Claessens and
Preneel) measured anonymity on networks by the *anonymity set* of possible
senders. Counting the set is not enough when an attacker suspects some
senders more than others. They used the Shannon entropy of the attacker's
probabilities :math:`p_i` instead:

.. math::

   H = -\sum_i p_i \log_2 p_i, \qquad |S|_{\text{eff}} = 2^{H} .

In words: :math:`2^H` equally likely senders would leave the attacker just
as unsure.

Why it works:

- For :math:`n` equally likely senders, :math:`H = \log_2 n`, so the
  effective size is :math:`n`.
- One sender suspected with probability 0.7 among ten shrinks the effective
  set from 10 to about 3.
- Every later entry on this page can be read as growing an anonymity set,
  or as an attack that shrinks one.

*Implementation:* :func:`blockchainkit.privacy.systems.anonymity.k_anonymity`,
:func:`blockchainkit.privacy.systems.anonymity.equivalence_classes` and
:func:`blockchainkit.privacy.systems.anonymity.effective_anonymity_set`. Rows
are dicts; the example generalises by truncating strings rather than by
Sweeney's value hierarchies.

*References:* L. Sweeney, *k-Anonymity: A Model for Protecting Privacy*,
International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems
10(5), 557–570 (2002). `DOI <https://doi.org/10.1142/S0218488502001648>`__;
A. Serjantov and G. Danezis, *Towards an Information Theoretic Metric for
Anonymity*, PET 2002, LNCS 2482, 41–53 (2003); C. Díaz, S. Seys, J. Claessens
and B. Preneel, *Towards Measuring Anonymity*, PET 2002, LNCS 2482, 54–68
(2003).

.. minigallery:: ../../examples/privacy/analysis/plot_01_k_anonymity_anonymity_sets.py

2004 -- Onion Routing in Tor: Fast Anonymity, Exposed End to End
----------------------------------------------------------------

Mixes wait to fill a batch, which can take minutes. That is fine for email
but useless for browsing the web.

Tor, designed by Dingledine, Mathewson and Syverson, keeps the layers and
drops the waiting:

#. The user picks three *relays*: an entry *guard*, a middle relay and an
   exit.
#. It wraps each packet in three layers of encryption, one per relay.
#. Each relay removes its layer and forwards the packet at once, with no
   batching and no reordering.

The guard knows the user but not the destination; the exit knows the
destination but not the user. The design paper states the price openly. An
adversary that watches both the guard and the exit can match the timing of
packets going in to packets coming out, because a delay shifts every packet
alike. If it runs a fraction :math:`f` of the relays,

.. math::

   \Pr[\text{guard and exit both malicious}] \approx f^2 .

Why it works, and where it does not:

- No single relay links the user to the destination.
- Low latency makes Tor usable, and many users make each one's anonymity
  set large.
- The gaps between packets survive the trip, so end-to-end timing
  correlation defeats it. Tor accepts this rather than adding delays nobody
  would tolerate.

*Implementation:* :func:`blockchainkit.privacy.systems.onion.circuit_compromise_rate`,
:func:`blockchainkit.privacy.systems.onion.simulate_flows` and
:func:`blockchainkit.privacy.systems.onion.match_flows`; the circuit reuses
the mix-net's layers. Relays are chosen uniformly rather than by bandwidth,
and real Tor builds circuits by telescoping handshakes and sends fixed
512-byte cells under symmetric keys.

*References:* R. Dingledine, N. Mathewson and P. Syverson, *Tor: The
Second-Generation Onion Router*, 13th USENIX Security Symposium, 303–320
(2004). `Paper <https://www.usenix.org/legacy/event/sec04/tech/dingledine.html>`__.

.. minigallery:: ../../examples/privacy/networks/plot_02_tor_onion_routing.py

2004 -- Linkable Ring Signatures and Key Images
-----------------------------------------------

A ring signature is too anonymous for money. If a coin is spent by signing
for a ring, the owner could sign twice, with two rings, and nobody could
tell that the same coin was spent twice.

Liu, Wei and Wong made ring signatures *linkable*. Each signature carries a
*key image*

.. math::

   I = H_p(P)^{x}, \qquad P = g^x ,

where :math:`H_p` hashes into the group. The image depends only on the
signer's key pair, so every signature by that key carries the same image. A
ledger stores the images of spent coins and rejects a repeat.

The signature proves the image is honest with the same response that closes
the ring. For each member :math:`i`:

#. :math:`L_i = g^{r_i} P_i^{c_i}` is the ordinary ring commitment.
#. :math:`R_i = H_p(P_i)^{r_i} I^{c_i}` checks the image against the same
   response.
#. :math:`c_{i+1} = H(m, L_i, R_i)` chains them.

Why it works:

- Only a single secret :math:`x` makes both :math:`L_s` and :math:`R_s`
  come out right for the signer, so the image must be :math:`H_p(P_s)^x`.
- Computing :math:`H_p(P)^x` from :math:`I` and the ring's public keys would
  mean solving a discrete logarithm, so the image does not say which member
  signed.
- Hashing the public key, as CryptoNote does, links signatures across
  different rings. Liu, Wei and Wong hashed the ring instead, which links
  only signatures over the same ring.

*Implementation:* :func:`blockchainkit.privacy.systems.linkable.lsag_sign`,
:func:`blockchainkit.privacy.systems.linkable.lsag_verify`,
:func:`blockchainkit.privacy.systems.linkable.key_image` and
:func:`blockchainkit.privacy.systems.linkable.linked`, all one-column cases
of :func:`blockchainkit.privacy.systems.linkable.mlsag_sign`. The image
hashes the public key, CryptoNote's form, rather than the ring.

*References:* J. K. Liu, V. K. Wei and D. S. Wong, *Linkable Spontaneous
Anonymous Group Signature for Ad Hoc Groups*, ACISP 2004, LNCS 3108, 325–335
(2004). `DOI <https://doi.org/10.1007/978-3-540-27800-9_28>`__.

.. minigallery:: ../../examples/privacy/signatures/plot_02_linkable_ring_signatures.py

2013 -- A Fistful of Bitcoins: Clustering Addresses by Owner
------------------------------------------------------------

Bitcoin users hide behind addresses, and wallets make a fresh one for every
payment received. Meiklejohn, Pomarole, Jordan, Levchenko, McCoy, Voelker and
Savage showed how much the ledger still gives away.

They grouped addresses that one user controls with two heuristics:

#. **Common input ownership.** All inputs of a transaction are signed
   together, so they belong to one user. Nakamoto's white paper already
   warned of this.
#. **One-time change.** Wallets send change to a fresh address. If exactly
   one output address of a transaction has never been seen before, and no
   input address reappears among the outputs, that output is the change and
   belongs to the sender.

Each heuristic adds edges between addresses. The clusters are the connected
components of the resulting graph, found with *union-find*: a structure that
merges sets and finds the set of an element in nearly constant time.

.. math::

   \text{cluster}(a) = \{\, b : a \leftrightarrow b \text{ through shared inputs or change} \,\}

Why it works:

- One labelled address names its whole cluster. The authors labelled
  clusters by buying from merchants and depositing at exchanges themselves,
  then followed thefts and the Silk Road's coins.
- The change heuristic needs the payee's address to be old. When both
  outputs are fresh, it cannot tell payment from change and abstains.
- The heuristics fail when users deliberately share inputs, which is what
  CoinJoin exploits.

*Implementation:* :func:`blockchainkit.privacy.systems.clustering.cluster_addresses`,
:func:`blockchainkit.privacy.systems.clustering.score_clusters` and
:func:`blockchainkit.privacy.systems.clustering.simulate_payments`. The
simulated economy spends largest coins first and always makes fresh change,
so the change heuristic makes no mistakes here; on Bitcoin it needed manual
exceptions for services that behaved otherwise.

*References:* S. Meiklejohn, M. Pomarole, G. Jordan, K. Levchenko, D. McCoy,
G. M. Voelker and S. Savage, *A Fistful of Bitcoins: Characterizing Payments
Among Men with No Names*, Internet Measurement Conference, 127–140 (2013).
`DOI <https://doi.org/10.1145/2504730.2504747>`__.

.. minigallery:: ../../examples/privacy/analysis/plot_02_fistful_of_bitcoins_clustering.py

2013 -- CryptoNote Stealth Addresses: A Fresh Key for Every Payment
-------------------------------------------------------------------

Reusing an address links every payment to it. Asking every payer for a new
address needs a conversation for every payment.

The CryptoNote white paper, the design behind Monero, let a payee publish one
address and still receive every payment at a fresh key. The address is two
public keys, :math:`A = g^a` and :math:`B = g^b`:

#. The payer picks a random :math:`r` and publishes :math:`R = g^r` with the
   transaction.
#. It pays to the one-time key :math:`P` below.
#. The payee scans each transaction: it computes :math:`R^a`, which equals
   :math:`A^r`, and checks whether :math:`P` matches.
#. To spend, it uses the private key :math:`x = H(R^a) + b`.

.. math::

   P = g^{H(A^r)}\, B = g^{H(R^a) + b} .

In words: payer and payee agree on a secret by Diffie-Hellman, and the
secret shifts the payee's spend key.

Why it works:

- :math:`A^r = R^a = g^{ar}` can be computed only with :math:`r` or
  :math:`a`, so outsiders cannot tell which outputs pay the same address.
- The *view key* :math:`a` finds incoming payments but cannot spend them,
  which is useful for audits. Spending also needs :math:`b`.

*Implementation:* :func:`blockchainkit.privacy.systems.stealth.stealth_keys`,
:func:`blockchainkit.privacy.systems.stealth.stealth_payment`,
:func:`blockchainkit.privacy.systems.stealth.owns_output` and
:func:`blockchainkit.privacy.systems.stealth.one_time_secret`, in the
teaching group rather than on Ed25519, with the output's index hashed in as
in CryptoNote.

*References:* N. van Saberhagen, *CryptoNote v 2.0*, white paper (October
2013).

.. minigallery:: ../../examples/privacy/signatures/plot_03_cryptonote_stealth_addresses.py

2013 -- CoinJoin: Many Payers in One Transaction
------------------------------------------------

The common-input heuristic assumes that a transaction's inputs share an
owner. Nothing in Bitcoin requires it.

Gregory Maxwell proposed *CoinJoin* on the Bitcoin forum:

#. Several users each bring an input and name an output address.
#. Someone assembles one transaction with all the inputs and outputs, in a
   random order.
#. Each user checks that its own output is there and signs only its own
   input.

If every mixed output pays the same *denomination* :math:`d`, nobody can tell
which output belongs to which input. Change is the weak point: each user's
change is its input minus :math:`d`,

.. math::

   \text{change}_i = a_i - d ,

which usually points straight back to its input.

Why it works:

- The users never trust each other with coins: a transaction that does not
  pay a user is simply not signed by it.
- :math:`n` equal outputs hide each participant among :math:`n`, and the
  common-input heuristic now merges strangers into one cluster.
- Only the equal outputs are anonymous. Wallets such as JoinMarket, Wasabi
  and Samourai's Whirlpool coordinate rounds and handle change carefully.

*Implementation:* :func:`blockchainkit.privacy.systems.coinjoin.coinjoin` and
:func:`blockchainkit.privacy.systems.coinjoin.link_change`. The transaction
has no fees and no signatures, and there is no coordinator; real
coordinators use blinded registrations so that they cannot link inputs to
outputs either.

*References:* G. Maxwell, *CoinJoin: Bitcoin privacy for the real world*,
Bitcoin Forum (August 2013). `Post
<https://bitcointalk.org/index.php?topic=279249.0>`__.

.. minigallery:: ../../examples/privacy/mixing/plot_01_coinjoin.py

2013 -- Zerocoin: Spending a Coin without Saying Which
------------------------------------------------------

CoinJoin hides a user among a handful of others in one transaction. Miers,
Garman, Green and Rubin wanted every coin ever minted in the anonymity set.

In *Zerocoin*, a user turns bitcoins into a zerocoin and back:

#. **Mint.** Pay a fixed amount and publish a commitment
   :math:`C = g^S h^r` to a random *serial number* :math:`S`.
#. **Spend.** Reveal :math:`S`, with a zero-knowledge proof of knowing the
   opening of *some* minted commitment with that serial.
#. The ledger records spent serials and refuses a repeat.

To keep the proof short, the minted coins (hashed to primes :math:`c_i`) are
gathered in an *RSA accumulator*: one number standing for the whole set. Each
coin has a *witness*, the accumulator of all the others:

.. math::

   A = u^{c_1 c_2 \cdots c_n} \bmod N, \qquad w_i^{\,c_i} \equiv A \pmod N .

Why it works:

- The serial number reveals nothing about which commitment it came from,
  because the commitment hid it behind :math:`r`.
- The proof shows that a witness exists for a committed coin, without
  revealing the coin.
- Its weaknesses led to Zerocash: proofs of about 25 kB, fixed
  denominations, and an RSA modulus whose factors had to be destroyed.

*Implementation:* :class:`blockchainkit.privacy.systems.zerocoin.ZerocoinPool`,
:func:`blockchainkit.privacy.systems.zerocoin.mint_coin`,
:func:`blockchainkit.privacy.systems.zerocoin.prove_zerocoin_spend`, and
:func:`blockchainkit.privacy.systems.zerocoin.accumulate` with its witnesses
over a 63-bit modulus. The spend proves membership with a ring signature over
every coin (:math:`C_i g^{-S} = h^r` holds only for the spent one), which
grows with the number of coins, instead of Zerocoin's double-discrete-log
proof against the accumulator.

*References:* I. Miers, C. Garman, M. Green and A. D. Rubin, *Zerocoin:
Anonymous Distributed E-Cash from Bitcoin*, IEEE Symposium on Security and
Privacy, 397–411 (2013). `DOI <https://doi.org/10.1109/SP.2013.34>`__.

.. minigallery:: ../../examples/privacy/amounts/plot_01_zerocoin.py

2015 -- Confidential Transactions: Amounts That Add Up Unseen
-------------------------------------------------------------

Even with hidden senders and receivers, amounts leak. A payment of exactly
0.3712 coins can be followed through the ledger by its value alone.

Gregory Maxwell replaced every amount with a Pedersen commitment
:math:`C = g^v h^r`. Because commitments multiply as their amounts add,
anyone can check that a transaction creates no money:

.. math::

   \prod_{\text{in}} C_i = g^{\text{fee}} \prod_{\text{out}} C_j .

The sender chooses the blinding factors :math:`r` so that they cancel.

That check alone is not enough. Amounts are numbers modulo the group order
:math:`q`, so an output of :math:`q - 1` acts as :math:`-1`, and it lets
another output hold one coin more than was paid in. So every output also
carries a *range proof* that its amount is small:

#. Commit to each bit of the amount: :math:`C_k = g^{b_k 2^k} h^{r_k}`, with
   the :math:`C_k` multiplying back to :math:`C`.
#. For each bit, sign with a ring signature over the two keys
   :math:`C_k` and :math:`C_k / g^{2^k}`, with base :math:`h`.
#. One of them is a pure power of :math:`h` exactly when the bit is 0 or 1.

Why it works:

- Pedersen commitments are perfectly hiding, so the amounts are invisible,
  yet the sums can be checked.
- A ring signature over the two keys proves the bit is 0 or 1 without
  saying which.

*Implementation:* :func:`blockchainkit.privacy.systems.confidential.prove_range`,
:func:`blockchainkit.privacy.systems.confidential.confidential_output` and
:func:`blockchainkit.privacy.systems.confidential.verify_confidential`. Each
bit has its own two-member ring signature; Elements uses base-4 digits joined
into one Borromean ring signature, and Bulletproofs
(:mod:`blockchainkit.proofs`) later made range proofs logarithmic in size.

*References:* G. Maxwell, *Confidential Transactions* (2015). `Write-up
<https://people.xiph.org/~greg/confidential_values.txt>`__; G. Maxwell and A.
Poelstra, *Borromean Ring Signatures* (2015).

.. minigallery:: ../../examples/privacy/amounts/plot_02_confidential_transactions.py

2016 -- RingCT: Hiding the Input and the Amounts Together
---------------------------------------------------------

Monero's rings hid which output was spent, but amounts stayed public, so a
ring could only mix outputs of the same denomination. Confidential amounts
would fix that, but then the ledger must check that amounts balance without
knowing which ring member is the input.

Shen Noether's *Ring Confidential Transactions* (RingCT) do both with one
signature. Each ring member is a pair: a one-time key :math:`P_i` and an
amount commitment :math:`C_i`. The signature has a second column whose keys
are

.. math::

   Z_i = \frac{C_i}{g^{\text{fee}} \prod_j C^{\text{out}}_j} .

For the real input, whose amount equals the outputs plus the fee, the
:math:`g` parts cancel and :math:`Z_i = h^{z}`, where :math:`z` is the
difference of blinding factors. For any other member, :math:`Z_i` hides a
leftover power of :math:`g`.

#. The signer signs an *MLSAG*: a linkable ring signature with two keys per
   member, chained by one ring of challenges.
#. In the first column it uses its spend key, as before.
#. In the second column it uses :math:`z`.

Why it works:

- One challenge ring over both columns means both secrets belong to the
  same member, so the member that is spent is also the member that
  balances.
- The key image of the first column stops double spends, exactly as before.

*Implementation:* :func:`blockchainkit.privacy.systems.ringct.ringct_spend`
and :func:`blockchainkit.privacy.systems.ringct.verify_ringct`, on
:func:`blockchainkit.privacy.systems.linkable.mlsag_sign`. There is one input
per transaction; Monero gives each input a pseudo-output commitment so that
several inputs can balance together, and since 2019 it uses CLSAG and
Bulletproofs.

*References:* S. Noether, *Ring Confidential Transactions*, Ledger 1, 1–18
(2016). `DOI <https://doi.org/10.5195/ledger.2016.34>`__.

.. minigallery:: ../../examples/privacy/amounts/plot_03_ringct.py

2016 -- Mimblewimble: No Addresses, and Cut-Through
---------------------------------------------------

In July 2016 a pseudonymous author signing as "Tom Elvis Jedusor" (Lord
Voldemort's French name) posted a design with no addresses and no amounts.

The key observation: in a confidential transaction, the blinding factor can
be the private key. An output is just :math:`C = g^v h^r`, owned by whoever
knows :math:`r`.

#. When a transaction balances, its outputs divided by its inputs (times
   :math:`g^{\text{fee}}`) leave :math:`h^k`, where :math:`k` is the change
   in blinding.
#. The parties sign with :math:`E = h^k` as the public key. This *excess*
   and the signature form the transaction's *kernel*.
#. That signature proves :math:`E` is :math:`h` to a known power, not
   hidden coins.

Because only products matter, transactions merge into one. An output
created and spent inside the merged set appears as both an output and an
input, and *cut-through* deletes both. Nodes can forget every spent output
and still check the whole chain:

.. math::

   \frac{\prod \text{outputs}}{\prod \text{inputs}}\,
   g^{\text{fees} - \text{minted}} = \Big(\prod_k E_k\Big)\, h^{\text{offset}} .

Why it works:

- No output names its owner, and no amount is visible.
- The chain grows with its unspent outputs and kernels, not with its
  history.
- Each transaction moves a random *offset* out of its kernel, so a merged
  block cannot be split back apart by matching kernels to subsets of inputs
  and outputs.

*Implementation:* :func:`blockchainkit.privacy.systems.mimblewimble.mimblewimble_transaction`,
:func:`blockchainkit.privacy.systems.mimblewimble.verify_mimblewimble`,
:func:`blockchainkit.privacy.systems.mimblewimble.aggregate` and
:func:`blockchainkit.privacy.systems.mimblewimble.cut_through`. Outputs carry
no range proofs here (they are shown in the confidential transactions
entry), and transactions are built by one party rather than interactively by
payer and payee as in Grin and Beam.

*References:* T. E. Jedusor, *Mimblewimble* (July 2016); A. Poelstra,
*Mimblewimble* (October 2016).

.. minigallery:: ../../examples/privacy/amounts/plot_04_mimblewimble.py

2017 -- TumbleBit: An Untrusted Tumbler
---------------------------------------

A *tumbler* is a mixing service: payers send it coins and it pays payees.
A centralised tumbler can steal the coins, and it sees who paid whom.

Heilman, Alshenibr, Baldimtsi, Scafuro and Goldberg removed both risks with
RSA puzzles. Using the tumbler's RSA key :math:`(N, e)`:

#. The tumbler promises the payee a payment token, encrypted with a key
   :math:`\epsilon`, along with the *puzzle* :math:`z = \epsilon^e \bmod N`.
   Only the tumbler can solve it.
#. The payee blinds the puzzle with a random :math:`\rho` and hands
   :math:`z'` to a payer.
#. The payer pays the tumbler to solve :math:`z'`, and passes the solution on.
#. The payee divides by :math:`\rho`, gets :math:`\epsilon`, and opens its
   token.

.. math::

   z' = z\,\rho^{e} \bmod N, \qquad (z')^{d} = \epsilon\,\rho .

In words: the payee disguises the puzzle, as Chaum's blind signatures
disguise a message.

Why it works:

- The tumbler saw :math:`z` with the payee and :math:`z'` with the payer.
  Because :math:`\rho` is uniform, :math:`z'` is a uniform number unrelated
  to :math:`z`.
- On chain, every step is a *fair exchange* through hash-locked escrows and
  cut-and-choose, so the tumbler cannot take a payment without solving the
  puzzle, or promise a token it never delivers.

*Implementation:* :class:`blockchainkit.privacy.systems.tumblebit.Tumbler`,
:func:`blockchainkit.privacy.systems.tumblebit.run_tumbler` and
:func:`blockchainkit.privacy.systems.tumblebit.tumbler_links`, with the
blinding of :func:`blockchainkit.crypto.systems.asymmetric.rsa_blind` under
a 62-bit textbook RSA key. The escrows, the fair exchange and cut-and-choose
are left out, and the token is a byte string.

*References:* E. Heilman, L. Alshenibr, F. Baldimtsi, A. Scafuro and S.
Goldberg, *TumbleBit: An Untrusted Bitcoin-Compatible Anonymous Payment
Hub*, NDSS 2017 (2017). `DOI <https://doi.org/10.14722/ndss.2017.23086>`__.

.. minigallery:: ../../examples/privacy/mixing/plot_02_tumblebit.py

2018 -- Traceability in Monero: When Decoys Fail
------------------------------------------------

A Monero input hides its real output among *decoys* (or *mixins*): other
outputs drawn from the ledger. Two independent studies showed that most early
inputs could be traced anyway.

- **Zero-mixin chain reaction.** Until 2016 Monero allowed rings without
  decoys. Such an input reveals which output it spends. That output can then
  be struck from every other ring that uses it as a decoy. Some of those
  rings are left with one member, which reveals theirs, and so on.
- **Guess-newest.** People tend to spend coins soon after receiving them.
  But decoys were drawn uniformly from all past outputs, so most decoys were
  old. The newest ring member was usually the real one.

If decoys follow the same age distribution as real spends, guessing the
newest of :math:`n` members is right with probability about

.. math::

   \Pr[\text{newest is real}] \approx \frac{1}{n} .

Why it matters:

- A ring is only as anonymous as its decoys are plausible.
- Monero responded with a minimum ring size (made 11 in 2018) and with
  decoys drawn from a distribution fitted to real spending ages.

*Implementation:* :func:`blockchainkit.privacy.systems.traceability.simulate_rings`,
:func:`blockchainkit.privacy.systems.traceability.chain_reaction`,
:func:`blockchainkit.privacy.systems.traceability.guess_newest` and
:func:`blockchainkit.privacy.systems.traceability.trace_rings`. Outputs are
created one per step, real spending ages are geometric, and the ``"recent"``
decoys share that distribution exactly; Monero's fitted gamma distribution
only approximates real behaviour.

*References:* M. Möser, K. Soska, E. Heilman, K. Lee, H. Heffan, S.
Srivastava, K. Hogan, J. Hennessey, A. Miller, A. Narayanan and N. Christin,
*An Empirical Analysis of Traceability in the Monero Blockchain*,
Proceedings on Privacy Enhancing Technologies 2018(3), 143–163 (2018). `DOI
<https://doi.org/10.1515/popets-2018-0025>`__; A. Kumar, C. Fischer, S. Tople
and P. Saxena, *A Traceability Analysis of Monero's Blockchain*, ESORICS
2017, LNCS 10493, 153–173 (2017).

.. minigallery:: ../../examples/privacy/analysis/plot_03_monero_traceability.py

2019 -- Tornado Cash: A Mixer Contract with Zero-Knowledge Withdrawals
----------------------------------------------------------------------

Tornado Cash brought Zerocash's notes and nullifiers to Ethereum as a smart
contract, with no operator at all:

#. **Deposit.** A user sends a fixed amount, say 1 ether, with the
   commitment to a secret note. The contract appends it to a Merkle tree of
   deposits.
#. **Withdraw.** Later, from a fresh address, the holder of the note
   reveals its *nullifier* and a zk-SNARK proving that the note is a leaf
   under a recent root.
#. The contract pays the recipient once per nullifier.

The contract never learns which leaf was withdrawn. A withdrawal could have
come from any deposit not yet withdrawn, so its anonymity set is

.. math::

   |S_w| = \#\{\text{deposits before } w\} - \#\{\text{withdrawals before } w\} .

Why it works, and where it does not:

- The proof also commits to the recipient, so nobody can copy a pending
  withdrawal and redirect it.
- Behaviour leaks what the proof hides. Withdrawing to the deposit address,
  or soon after an unusual deposit, shrinks the anonymity set to one.
- In August 2022 the US Treasury sanctioned the Tornado Cash contracts, after
  stolen funds, including the Ronin bridge's, had been laundered through
  them.

*Implementation:* :class:`blockchainkit.privacy.systems.tornado.Mixer` on
:class:`~blockchainkit.contracts.systems.world.World`,
:func:`blockchainkit.privacy.systems.tornado.prove_withdrawal` and
:func:`blockchainkit.privacy.systems.tornado.mixer_report`. Proofs use the
Zerocash spend circuit of :mod:`blockchainkit.proofs.systems.zerocash`
(Groth16 on a toy pairing, MiMC hashing), whose new-note commitment binds the
recipient; Tornado's own circuit binds the recipient, a relayer and its fee
as separate public inputs.

*References:* A. Pertsev, R. Semenov and R. Storm, *Tornado Cash Privacy
Solution*, white paper, version 1.4 (2019); U.S. Department of the Treasury,
*U.S. Treasury Sanctions Notorious Virtual Currency Mixer Tornado Cash*,
press release (8 August 2022).

.. minigallery:: ../../examples/privacy/mixing/plot_03_tornado_cash.py
