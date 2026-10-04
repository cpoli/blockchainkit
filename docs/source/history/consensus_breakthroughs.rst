Breakthroughs in Consensus
==========================

.. include:: /_generated/nav/consensus.rst

Signatures say who authorized a payment; they cannot say which of two
conflicting payments came first. Consensus mechanisms answer that question by
making some resource scarce: computation, or stake. This chronology traces the
ideas behind :mod:`blockchainkit.consensus`.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

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
construction. A sender varies a nonce until a hash meets a target.

.. math::

   H(\mathrm{header})\leq 2^{256-d}-1,\qquad
   \Pr[\mathrm{success}]=2^{-d},\qquad \mathbb{E}[T]=2^d.

**Implementation:** :func:`blockchainkit.consensus.systems.pow.mine` searches a bounded
nonce interval; :func:`blockchainkit.consensus.systems.pow.valid_pow` checks one hash.
The header encoding is blockchainkit's, not a Hashcash token format.

**Experiment:** :doc:`/api/gallery/consensus/pow/plot_01_proof_of_work` compares measured trial
counts with the expected exponential cost. Search is random-looking, so a
mean is not a deadline. An exhausted attempt budget raises ``TimeoutError``.
Computational effort becomes a consensus ingredient only when combined with
validation rules, a network, and a rule for comparing histories.

*References:* A. Back, *Hashcash — A Denial of Service Counter-Measure* (2002),
describing the earlier 1997 proposal. `Author's paper
<http://www.hashcash.org/papers/hashcash.pdf>`__.

.. minigallery:: ../../examples/consensus/pow/plot_01_proof_of_work.py


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
and peer-to-peer dissemination into an electronic cash design.
The key systems question is double spending: two individually authorized
payments may conflict, so participants need a shared ordering rule.

**Implementation:** :class:`blockchainkit.structures.systems.chain.Blockchain` validates
account transfers and selects greatest cumulative work. Each fork retains its
own :class:`blockchainkit.structures.systems.ledger.Ledger`, so a reorganization also
restores the appropriate balances and account nonces. Difficulty is fixed by
genesis; this model does not implement Bitcoin's adjustment schedule or UTXOs.

**Experiment:** :doc:`/api/gallery/structures/chain/plot_01_blockchain` mines and gossips a signed
payment, then removes its confirmation when a competing fork wins. The
payment's signature and original Merkle proof still verify. Cryptographic
validity, inclusion, and finality are three different properties.

Equal-work ties use a deterministic hash ordering for reproducible experiments.
No finite confirmation count is presented as unconditional finality.

*References:* S. Nakamoto, *Bitcoin: A Peer-to-Peer Electronic Cash System*
(2008). `Original announcement
<https://www.metzdowd.com/pipermail/cryptography/2008-October/014810.html>`__;
`paper <https://bitcoin.org/bitcoin.pdf>`__.

.. minigallery:: ../../examples/structures/chain/plot_01_blockchain.py


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
work. The broader design question is how participants earn influence
over proposing or confirming state changes without weighting every decision
by newly performed computation.

**Implementation:** :class:`blockchainkit.consensus.systems.pos.StakeSampler` isolates
a simple stake-proportional lottery:

.. math::

   \Pr[\text{proposer}=i]=\frac{w_i}{\sum_j w_j}.

It samples integer weights without floating-point rounding and uses a private,
seeded PRNG for reproducible experiments. This is not Peercoin's protocol and
does not model coin age, voting, slashing, finality, or an unbiasable beacon.

**Experiment:** :doc:`/api/gallery/consensus/pos/plot_01_stake` compares observed proposer
frequencies to stake fractions. Splitting one stake across many names preserves
its combined expected weight. Fair proposer sampling alone does not resolve
equivocation or competing chains; those require additional protocol rules.

*References:* S. King and S. Nadal, *PPCoin: Peer-to-Peer Crypto-Currency with
Proof-of-Stake* (2012). `Project paper
<https://www.peercoin.net/assets/paper/peercoin-paper.pdf>`__.

.. minigallery:: ../../examples/consensus/pos/plot_01_stake.py
