The breakthroughs behind blockchainkit
======================================

A blockchain combines several answers to different questions. **Who can
authorize a message? Has a record changed? Can one item be checked without
downloading everything? Which of two valid histories should peers follow?**
Confusing these questions is a common source of confusion about blockchains.
A signature does not prevent double spending; a hash does not make a history
immutable; gossip does not create agreement.

This chapter follows the ideas in historical order. Each milestone gives the
problem, the mathematical mechanism, a link into the actual implementation,
and an experiment. The examples deliberately use smaller models than real
protocols. Their assumptions are part of the lesson, not details to hide.
Publication years below distinguish conference presentations from later
proceedings where useful. This is a selected, executable history, not a claim
that one inventor or one paper supplied every ingredient.

**First reading:** start with the “In plain language” and “Reading the
experiment” paragraphs in each milestone. The equations provide a second,
more detailed route; you can skip them initially. See :doc:`start_here` for
the overall picture and :doc:`glossary` for unfamiliar terms.

All snippets use the package's conventional import:

.. code-block:: python

   import blockchainkit as bk

From breakthroughs to a working system
--------------------------------------

.. list-table:: A compact historical map
   :header-rows: 1
   :widths: 18 40 42

   * - Period
     - New capability
     - Question still requiring another ingredient
   * - 1976–1978
     - Public-key exchange and RSA
     - Who is really at the other end of the exchange?
   * - 1979–1983
     - Threshold sharing, Merkle authentication, blind signatures
     - Are shares honest, roots trusted, and tokens spent only once?
   * - 1985–1991
     - Curve groups, proof protocols, signatures, gossip, linked records
     - Which of two conflicting histories should participants accept?
   * - 1997–2009
     - Computational work, standardized hashing, Bitcoin's combination
     - Under which assumptions can a confirmation be reversed?
   * - 2012–2014
     - Stake-based participation and programmable state
     - What voting and execution rules make the whole system agree?

The detailed entries below distinguish original ideas from this package's
teaching adaptations. The :doc:`course` follows prerequisites rather than dates:

.. code-block:: text

   hashes ----> Merkle proofs ----------------------+
      |                                            |
      +-------> proof of work ----+                  v
   keys ------> signatures ------+------> payment lifecycle
   peer links -> gossip ---------+                  |
                                                    v
                                      forks, queues, and reorganization

   Python lists -> stack execution (a separate component)

Run :doc:`gallery/plot_13_payment_lifecycle` to see how these ideas interact.
Use :doc:`solutions` to check your reasoning after each experiment.

.. contents:: Follow the chronology
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
in a finite group [DH76]_.

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

**Experiment:** :doc:`gallery/plot_01_public_keys` includes a key-substitution
attack. Agreement on a secret is not authentication of the other person.

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
modular exponentiation with a composite modulus [RSA78]_. Choose distinct
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

**Experiment:** :doc:`gallery/plot_01_public_keys` demonstrates multiplicative
malleability: altering a ciphertext can predictably alter its plaintext.
Textbook RSA is deterministic and unpadded; this package does not present it
as a secure encryption or signature interface. Public-key cryptography needs
a complete encoding and protocol, not just an impressive formula.

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
recover it together [Shamir79]_. Choose a random degree-at-most-:math:`t-1`
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

**Experiment:** :doc:`gallery/plot_02_secret_sharing` reconstructs from every
three-of-five subset and draws several polynomials compatible with two shares.
Plain sharing does not detect forged shares. Nor does reconstructing a key
implement a threshold signing protocol: those are separate capabilities.

1979–1987 — Merkle trees and compact authentication
---------------------------------------------------

**In plain language.** You can check whether one payment belongs to a large batch
without downloading every payment. Keep the batch’s trusted fingerprint, then combine
the payment with a short trail of supporting fingerprints.

**Reading the experiment.** H means a hash function and the vertical double bar means
joining bytes. A leaf is a bottom-level item; parents combine child fingerprints.
Prefixes 0 and 1 distinguish hashing a record from hashing a pair of tree nodes.
“Canonical” below means the history currently selected by the chain rules.

Authenticating a large collection need not require sending the whole collection.
Merkle's work on public-key systems and hash-based authentication supplied a
tree construction in which hashes of children determine their parent's hash
[Merkle79]_ [Merkle87]_. A trusted root can authenticate a leaf using the
sibling digests on its path.

.. math::

   L_i=H(0\,\|\,m_i),\qquad
   N=H(1\,\|\,N_{\mathrm{left}}\,\|\,N_{\mathrm{right}}).

The prefix bytes above are blockchainkit's domain-separation convention,
not a claim about Merkle's original wire format. Our root additionally binds
the leaf count; an unmatched node is promoted rather than duplicated.

**Implementation:** :class:`blockchainkit.structures.systems.merkle.MerkleTree` and
:func:`blockchainkit.structures.systems.merkle.verify_proof` check index, shape,
payload, and count.

**Experiment:** :doc:`gallery/plot_03_merkle_proofs` measures logarithmic proof
size and rejects modified payloads. It also distinguishes two trust claims:
membership in a list is not proof that the list is valid or canonical.

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
in 1983 [Chaum83]_. RSA's algebra lets a requester obscure a message with an
invertible random factor and remove that factor after signing.

.. math::

   m'=mr^e\bmod n,\qquad
   s'=(m')^d\bmod n,\qquad
   s=s'r^{-1}\bmod n.

Then :math:`s^e=m\pmod n`. The requester obtains an ordinary signature while
the signer processes the blinded value.

**Implementation:** :func:`blockchainkit.crypto.systems.asymmetric.rsa_blind` and
:func:`blockchainkit.crypto.systems.asymmetric.rsa_unblind` expose this identity.

**Experiment:** :doc:`gallery/plot_04_blind_signatures` follows each value
through the exchange. These bare integer operations are not a complete
anonymous cash system: issuance policy, message encoding, and a mechanism to
detect repeated spending remain necessary. Privacy and decentralized agreement
are different design questions.

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
Koblitz independently developed elliptic-curve cryptosystems [Miller86]_
[Koblitz87]_. The relevant object is a finite group of curve points, not a
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

**Experiment:** :doc:`gallery/plot_05_elliptic_curves` plots the tiny group and
recovers a private scalar by enumeration. The same API handles secp256k1,
but this readable Python implementation is variable-time and not hardened.

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
simulation-based sense [GMR85]_. Fiat and Shamir then developed a way to replace
an interactive challenge with a hash-derived one [FS87]_.

Blockchainkit illustrates these ideas through a later Schnorr-style protocol.
An honest-verifier transcript can be simulated by choosing :math:`c,s` first
and computing :math:`R=sG-cQ`. An actual prover must commit to :math:`R` before
receiving an unpredictable :math:`c`. The order is crucial.

**Implementation:** :func:`blockchainkit.crypto.systems.signatures.verify_transcript`
checks the group equation; :func:`blockchainkit.crypto.systems.signatures.challenge`
hashes the message, public key, commitment, and curve domain.

**Experiment:** :doc:`gallery/plot_06_schnorr_proofs` constructs both a real
signature and a simulated accepting transcript. It explains honest-verifier
zero-knowledge intuition; it does not implement a general proof system or claim
that every use of Fiat–Shamir is secure without further assumptions.

1987 — Epidemic dissemination and partial views
-----------------------------------------------

**In plain language.** A message spreads through neighboring peers, much as news passes
between people. Some hear it later than others. Passing the news around does not by
itself settle which of two conflicting stories to accept.

**Reading the experiment.** In the experiment, watch which peers receive the message
before and after a broken connection is restored. Reconnection alone does not send
earlier messages: the example explicitly sends the announcement again.

Demers and colleagues studied epidemic algorithms for propagating updates
among replicated databases [Demers87]_. Local exchanges can spread information
without requiring one central sender to reach every replica at once. The
resulting delays make each participant's view temporarily different.

**Implementation:** :class:`blockchainkit.network.systems.gossip.SimulatedNetwork` is a
simplified flooding model with duplicate suppression, explicit links, and
seeded per-hop delays. It illustrates dissemination rather than reproducing
the paper's anti-entropy algorithms. The simulator orders simultaneous events
deterministically and uses integer time instead of sleeping.

**Experiment:** :doc:`gallery/plot_09_gossip` partitions a peer, reconnects it,
and explicitly retransmits the missing announcement. A new connection alone
does not synchronize old state. Delivery does not imply agreement: peers can
receive the same two conflicting proposals and still need rules for choosing
between them. That distinction becomes visible in the blockchain experiment.

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
and efficient [Schnorr91]_. In additive notation, a prover with secret
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

**Experiment:** :doc:`gallery/plot_06_schnorr_proofs` signs two different messages
with one deliberately reused nonce and recovers the private key. The scheme
is not BIP-340. Explicit nonces are experiment controls, not a recommendation
for application key management.

1991 — Hash-linked timestamps and tamper evidence
-------------------------------------------------

**In plain language.** Include the previous record’s fingerprint in each new record.
Editing an earlier record then breaks later links unless those records are recalculated
too. Detecting such changes still requires something trustworthy to compare against.

**Reading the experiment.** The subscript i means the current block, and i−1 the
preceding block. H hashes an encoded bundle containing the previous hash, the current
payment-batch root, and descriptive fields such as height and timestamp.

Haber and Stornetta investigated how to establish when a digital document
existed without trusting easily edited metadata [HS91]_. Linking commitments
to earlier records makes an alteration affect subsequent commitments.

.. math::

   h_i=H(\mathrm{encode}(h_{i-1},\mathrm{root}_i,\mathrm{metadata}_i)).

**Implementation:** :class:`blockchainkit.structures.systems.block.Block` hashes a
canonical header containing the parent hash, transaction root, height,
timestamp, difficulty, and mining nonce. Changing any of those fields changes
the block digest.

**Experiment:** :doc:`gallery/plot_10_blockchain` creates linked records and
two conflicting continuations. A hash link alone cannot make one history
authoritative: somebody can recompute an entire alternative chain. Anchoring,
publication, or consensus supplies additional assumptions. The timestamps here
are caller-chosen simulation integers, not trusted real-world time certificates.
This is the hash-linking lesson, not a reproduction of the full timestamp service.

1997–2002 — Hashcash and proofs of computational effort
-------------------------------------------------------

**In plain language.** Make someone search for a rare hash result, then check their
answer with one hash calculation. Searching can take many attempts even though checking
the finished result is quick.

**Reading the experiment.** Difficulty d sets the rarity. The probability of success on
each trial is 1 divided by 2 to the power d; the expected number of trials T is 2 to the
power d. At difficulty 5 that means 32 attempts on average, not a guarantee of success
within 32.

Back's Hashcash proposal used a computational puzzle to impose a cost on
requests while keeping verification cheap; the 2002 paper describes the
construction [Back02]_. A sender varies a nonce until a hash meets a target.

.. math::

   H(\mathrm{header})\leq 2^{256-d}-1,\qquad
   \Pr[\mathrm{success}]=2^{-d},\qquad \mathbb{E}[T]=2^d.

**Implementation:** :func:`blockchainkit.consensus.systems.pow.mine` searches a bounded
nonce interval; :func:`blockchainkit.consensus.systems.pow.valid_pow` checks one hash.
The header encoding is blockchainkit's, not a Hashcash token format.

**Experiment:** :doc:`gallery/plot_08_proof_of_work` compares measured trial
counts with the expected exponential cost. Search is random-looking, so a
mean is not a deadline. An exhausted attempt budget raises ``TimeoutError``.
Computational effort becomes a consensus ingredient only when combined with
validation rules, a network, and a rule for comparing histories.

2002 — SHA-256 as a standardized hash primitive
-----------------------------------------------

**In plain language.** Different programs need to calculate the same fingerprint for the
same data. A standardized hash gives them a shared rule and known examples against which
to check their implementations.

**Reading the experiment.** The displayed result is hexadecimal: two characters
represent each byte. Changing an input bit usually changes many output bits. A
scrambled-looking output does not, by itself, establish that a hash is secure.

NIST's FIPS 180-2 specified SHA-256 alongside other secure hash algorithms
[FIPS1802]_. Hashes became shared building blocks that independent systems
could implement and test against common vectors. A fixed-size output gives
a compact fingerprint; it does not encrypt the input.

**Implementation:** :func:`blockchainkit.crypto.systems.hashing.sha256` delegates to
Python's standard-library implementation instead of reimplementing the
compression function. :func:`blockchainkit.crypto.systems.commitments.commit` adds domain
separation and explicit salt framing for a simple commitment experiment.

.. doctest::

   >>> bk.crypto.sha256(b"abc").hex()
   'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

**Experiment:** :doc:`gallery/plot_07_hashing` flips individual input bits and
measures output changes. This illustrates diffusion, not a proof of security.
An unsalted hash of a small guessable message does not hide it; commitment
hiding depends on unpredictable secret salt. Earlier milestones above use
SHA-256 as a modern teaching primitive, not as a historical implementation.

2008–2009 — Bitcoin combines the ingredients
--------------------------------------------

**In plain language.** Alice could sign two payments that each spend her entire balance.
Both signatures could be valid, but both payments cannot be accepted together. Bitcoin
combined earlier tools into rules for ordering payments across a network.

**Reading the experiment.** Follow the balances as a competing history wins. A payment
can leave the selected history even though its signature and its membership proof for
the old block remain valid. This package uses account balances; Bitcoin instead tracks
individual unspent transaction outputs (UTXOs).

Nakamoto's 2008 proposal combined signatures, hash-linked blocks, proof of work,
and peer-to-peer dissemination into an electronic cash design [Nakamoto08]_.
The key systems question is double spending: two individually authorized
payments may conflict, so participants need a shared ordering rule.

**Implementation:** :class:`blockchainkit.structures.systems.chain.Blockchain` validates
account transfers and selects greatest cumulative work. Each fork retains its
own :class:`blockchainkit.structures.systems.ledger.Ledger`, so a reorganization also
restores the appropriate balances and account nonces. Difficulty is fixed by
genesis; this model does not implement Bitcoin's adjustment schedule or UTXOs.

**Experiment:** :doc:`gallery/plot_10_blockchain` mines and gossips a signed
payment, then removes its confirmation when a competing fork wins. The
payment's signature and original Merkle proof still verify. Cryptographic
validity, inclusion, and finality are three different properties.

Equal-work ties use a deterministic hash ordering for reproducible experiments.
No finite confirmation count is presented as unconditional finality.

2012 — Stake as an alternative participation weight
---------------------------------------------------

**In plain language.** A weighted lottery can give someone with twice as much stake
twice the chance of being selected. This demonstrates one building block used in some
consensus designs, rather than a whole agreement process.

**Reading the experiment.** The weight w for participant i is divided by the sum of
everybody’s weights. Weights 1 and 3 give probabilities one quarter and three quarters.
Repeated draws approach those proportions without guaranteeing them in a short run. PRNG
means pseudorandom number generator.

King and Nadal's Peercoin proposal explored proof of stake alongside proof of
work [KN12]_. The broader design question is how participants earn influence
over proposing or confirming state changes without weighting every decision
by newly performed computation.

**Implementation:** :class:`blockchainkit.consensus.systems.pos.StakeSampler` isolates
a simple stake-proportional lottery:

.. math::

   \Pr[\text{proposer}=i]=\frac{w_i}{\sum_j w_j}.

It samples integer weights without floating-point rounding and uses a private,
seeded PRNG for reproducible experiments. This is not Peercoin's protocol and
does not model coin age, voting, slashing, finality, or an unbiasable beacon.

**Experiment:** :doc:`gallery/plot_11_stake` compares observed proposer
frequencies to stake fractions. Splitting one stake across many names preserves
its combined expected weight. Fair proposer sampling alone does not resolve
equivocation or competing chains; those require additional protocol rules.

2014 — Ethereum and programmable replicated state
-------------------------------------------------

**In plain language.** Participants can agree on program results as well as payments if
they all execute the same rules. A work budget stops one program from consuming
unlimited computation.

**Reading the experiment.** S is the state before execution and S prime is the state
afterward. In this experiment, a successful program returns updated storage; an error
leaves the original storage untouched. This small virtual machine is separate from the
payment ledger, rather than an Ethereum implementation.

Ethereum's whitepaper describes a blockchain as a state-transition system
whose rules can include programmable contracts [Ethereum14]_. Replication
requires deterministic execution, while bounded execution cost limits the
resources an individual program can demand.

.. math::

   (S,\mathrm{program},\mathrm{input})\longrightarrow S'
   \quad\text{or an execution error}.

**Implementation:** :func:`blockchainkit.vm.systems.stack_machine.execute` provides a
256-bit stack machine, integer storage, branches, a stack bound, and an
instruction budget. It works on a storage copy and returns a new state only
after success; errors leave the caller's state unchanged.

**Experiment:** :doc:`gallery/plot_12_execution` compares successful execution,
out-of-gas failure, and a bounded infinite loop. Costs are one unit per
instruction, not an EVM gas schedule. The VM is independent of the transfer-only
ledger: connecting arbitrary contract transactions would require a further
consensus specification.

What the sequence teaches
-------------------------

Each ingredient changes what can be verified, under particular assumptions.
The most useful next experiment is often to remove one assumption: reuse a
nonce, reveal a commitment salt, forge a share, partition a link, replay a
transfer, or exhaust an execution budget. The tests and gallery show which
properties survive, which fail, and which the simplified model never promised.

See :doc:`protocol` for exact encodings and :doc:`simulation` for the scope of
research experiments. Primary sources are collected in :doc:`references`.
