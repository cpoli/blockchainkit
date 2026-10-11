Breakthroughs in Layer-2 Scaling and Interoperability
=====================================================

.. include:: /_generated/nav/channels.rst

.. epigraph::

   "The bitcoin protocol can encompass the global financial transaction
   volume in all electronic payment systems today, without a single
   custodial third party holding funds."
   -- Joseph Poon and Thaddeus Dryja, *The Bitcoin Lightning Network*, 2016

Every full node verifies every transaction, so adding nodes adds copies of
the work, not capacity: a blockchain processes no more than one node can.
The ideas below keep the chain's security while moving most of the work
elsewhere: payment and state channels, where two parties update a balance
privately and the chain only judges disputes; child chains and rollups,
which post commitments or compressed data instead of executing everything;
sharding, which splits the work among groups of nodes; and data-availability
sampling, which lets light clients check that the data behind a block
exists without downloading it. Two of these tools, hash time-locks and
light clients, also move value between chains, and bridges that do without
them have been the costliest failures in the field. :doc:`vm_breakthroughs` covers
the hash time-locked contract itself, and :doc:`structures_breakthroughs`
the Merkle proofs and light clients that much of this page builds on.

Every channel output here is a :mod:`blockchainkit.vm.systems.script`
program, judged by :func:`~blockchainkit.vm.systems.script.verify_script`;
the contracts run on :class:`~blockchainkit.contracts.systems.world.World`.
:doc:`/protocol` lists where the models depart from deployed systems.

.. contents:: Timeline
   :local:
   :depth: 1

1960 -- Reed and Solomon's Polynomial Codes
-------------------------------------------

A communication line that loses or corrupts symbols needs redundancy, and
Reed and Solomon found a code that tolerates as much damage as any code of
its length and rate can. They read ``k`` symbols of a finite field as the
coefficients of a polynomial of degree below ``k`` and transmitted its
values at ``n`` points. Two different polynomials of degree below ``k``
agree on at most ``k - 1`` points, since their difference has at most
``k - 1`` roots. So any ``k`` received values determine the polynomial, and
two codewords differ in at least :math:`n - k + 1` places. A decoder can
therefore fill in up to :math:`n - k` lost symbols, and correct a wrong
symbol at the price of two lost ones, as long as

.. math::

   2\,(\text{errors}) + (\text{erasures}) \le n - k.

Decoding errors efficiently took longer; Berlekamp and Welch (1986) reduced
it to linear algebra, by solving for an error-locator polynomial. With
:math:`n = 2k`, any half of the ``n`` values rebuilds the data, which is
what data-availability sampling relies on.

*Implementation:* :func:`blockchainkit.channels.systems.reed_solomon.rs_encode`,
:func:`~blockchainkit.channels.systems.reed_solomon.rs_recover` and
:func:`~blockchainkit.channels.systems.reed_solomon.rs_decode` (Berlekamp-Welch),
over the integers modulo 65,537 by default. Codes are systematic: the data
are the polynomial's values at ``0, ..., k - 1``, as in data-availability
schemes, rather than its coefficients, as in Reed and Solomon's paper.

*References:* I. S. Reed and G. Solomon, *Polynomial codes over certain
finite fields*, Journal of the Society for Industrial and Applied
Mathematics 8(2), 300–304 (1960).
`DOI <https://doi.org/10.1137/0108018>`__; L. R. Welch and E. R. Berlekamp,
*Error correction for algebraic block codes*, US Patent 4,633,470 (1986).

.. minigallery:: ../../examples/channels/coding/plot_01_reed_solomon.py

2013 -- Spilman and Hearn's One-Way Micropayment Channels
---------------------------------------------------------

Paying a few satoshis per second for a service, one transaction per
payment, costs more in fees than it pays. Jeremy Spilman described a
channel that needs two transactions for any number of payments. The payer
locks the channel's capacity in an output that only both parties' signatures
can spend. Before doing so, the payer gets the payee's signature on a
refund that returns everything after a lock time, so a payee who vanishes
cannot hold the coins hostage. Each payment is a new, unpublished
transaction from that output, signed by the payer and paying the payee a
little more than the last. The payee could countersign and publish any of
them, but the last pays it the most, so it publishes only that one. Mike
Hearn implemented the scheme in bitcoinj the same year. For ``m`` payments,
only funding and closing reach the chain,

.. math::

   \text{transactions on chain} = 2 \quad\text{for any } m,

and the payee must close before the lock time, or the payer can take
everything back with the refund.

*Implementation:* :class:`blockchainkit.channels.systems.micropayment.SpilmanChannel`,
whose funding output is a 2-of-2 Script checked by
:func:`~blockchainkit.vm.systems.script.verify_script`. The interpreter has
no ``OP_CHECKMULTISIG``, so the two signatures are checked one after the
other. Before segregated witness, the refund signed a funding transaction
whose identifier could be malleated; the model has no malleability.

*References:* J. Spilman, *Anti DoS for tx replacement*, bitcoin-development
mailing list (April 2013); M. Hearn, micropayment channels in bitcoinj
(2013), and *Contract*, Bitcoin Wiki.

.. minigallery:: ../../examples/channels/payment_channels/plot_01_spilman_channels.py

2013 -- Tier Nolan's Atomic Cross-Chain Swaps
---------------------------------------------

Two people who trade coins on different chains each want the other to pay
first, and neither chain can see the other to enforce the deal. Tier
Nolan's protocol ties the two payments to one secret ``s``, known only to
Alice. Alice locks her coins on chain A to Bob behind ``h = SHA256(s)``,
refundable to her at :math:`T_A`; Bob, seeing this, locks his on chain B to
Alice behind the same ``h``, refundable to him at :math:`T_B`. Alice
claims on B by revealing ``s``, and Bob reads it from chain B and claims on
A. Either both payments happen or neither does. Alice must claim on B
before :math:`T_B`, or Bob takes his coins back, so ``s`` is public by
:math:`T_B` at the latest; Bob then needs time to use it on A before Alice
can refund there. Nobody can lose if

.. math::

   T_A > T_B + \text{the time Bob needs to react}.

With the timeouts reversed, :math:`T_A < T_B`, Alice could wait until
:math:`T_A`, refund on A, and still claim on B.

*Implementation:* :class:`blockchainkit.channels.systems.swaps.AtomicSwap`,
two :func:`~blockchainkit.vm.systems.script.htlc_locking` outputs whose
claims and refunds run through Script. Both chains share one block height,
and neither has fees or confirmation delays; the free option the protocol
gives Alice is left to the exercise.

*References:* T. Nolan, *Alt chains and atomic transfers*, Bitcointalk
forum (May 2013).

.. minigallery:: ../../examples/channels/interoperability/plot_01_atomic_swaps.py

2015 -- Decker and Wattenhofer's Duplex Micropayment Channels
-------------------------------------------------------------

A Spilman channel pays one way and is spent once. Decker and Wattenhofer
combined two, one per direction, and *reset* the pair whenever one side ran
dry, re-funding both from the current balances. Each reset leaves older
pairs signed and publishable, and nothing punishes a party who publishes
one, so the protocol must make sure the newest pair always reaches the
chain first. An *invalidation tree* of time-locked transactions sees to
that. Each reset replaces a node of the tree with a copy whose lock time
is :math:`\delta` lower. Where an old and a new branch part, both spend the
same parent output, and the new branch becomes valid first, so it spends
that output and the old branch can never confirm. Lock times only go down,
so a tree of depth ``d`` with ``s`` lock-time values per level allows
:math:`s^d` resets before it runs out. At worst every level still has its
highest lock time, and closing waits for up to

.. math::

   d\,(s - 1)\,\delta \text{ blocks}.

The paper also built a payment network from these channels, routing over
several hops with hash time-locks.

*Implementation:* :class:`blockchainkit.channels.systems.duplex.DuplexChannel`,
:func:`~blockchainkit.channels.systems.duplex.invalidation_locktimes` and
:func:`~blockchainkit.channels.systems.duplex.first_confirmed`. The channel
is a state machine without transactions or signatures. Lock times are
relative, counted from each parent's confirmation, so closing takes their
sum; with absolute lock times a channel also has a fixed lifetime.

*References:* C. Decker and R. Wattenhofer, *A fast and scalable payment
network with Bitcoin duplex micropayment channels*, Stabilization, Safety,
and Security of Distributed Systems (SSS 2015), LNCS 9212, 3–18 (2015).
`DOI <https://doi.org/10.1007/978-3-319-21741-3_1>`__.

.. minigallery:: ../../examples/channels/payment_channels/plot_02_duplex_channels.py

2016 -- Poon and Dryja's Lightning Network: Revocation and Penalties
--------------------------------------------------------------------

An invalidation tree runs out of lock times, so a duplex channel allows
only so many resets. Lightning stops old states from being published by
deterrence instead: publishing one costs the cheater everything, and since
no lock time is used up, a channel can be updated without limit. Each party
holds its own commitment transaction, signed by the other. It pays the
counterparty at once, but its holder only after a delay, and during that
delay the holder's output can also be taken with a *revocation key*. To
move to a new state, each party hands over the secret behind its previous
commitment's revocation key. From then on, a party that publishes that old
commitment loses its whole balance to a counterparty who is watching,
because the counterparty can sweep it with the revocation key before the
delay ends. The key must be unusable until handed over, so it is split: it
combines the holder's per-commitment point :math:`S_n = s_n G` with the
counterparty's base point :math:`B = b G`,

.. math::

   R_n = S_n + B, \qquad r_n = s_n + b \pmod q.

The counterparty knows only ``b`` and the holder only :math:`s_n`, so
neither can sign with :math:`r_n` until the holder reveals :math:`s_n`. The
paper also linked channels into a network with hash time-locked contracts.

*Implementation:* :class:`blockchainkit.channels.systems.lightning.LightningChannel`,
whose commitments, sweeps and penalties are Script spends of a 2-of-2
funding output and a revocable output. Per-commitment secrets are a hash
chain used backwards, as in Lightning's *shachain*, so the counterparty
stores one secret. Script here lacks ``OP_CHECKSEQUENCEVERIFY``: the delay
is checked by ``OP_CHECKLOCKTIMEVERIFY`` against the commitment's age, and
the revocation key adds the points without the hashed tweaks that stop a
party from cancelling the other's.

*References:* J. Poon and T. Dryja, *The Bitcoin Lightning Network:
Scalable off-chain instant payments*, white paper (January 2016).

.. minigallery:: ../../examples/channels/payment_channels/plot_03_lightning_revocation.py

2016 -- BTC Relay: a Light-Client Bridge in a Smart Contract
------------------------------------------------------------

A contract on one chain cannot see another, so it cannot tell whether a
payment there happened. BTC Relay, launched on Ethereum in 2016, ran a
Bitcoin light client inside a contract. Relayers submitted Bitcoin block
headers; the contract checked that each linked to a stored header and met
its proof-of-work target, and followed the chain with the most cumulative
work. A header whose hash needs ``difficulty`` leading zero bits takes
:math:`2^{\text{difficulty}}` hashes on average, so a chain's work is

.. math::

   W = \sum_{\text{headers}} 2^{\text{difficulty}}.

A contract could then accept a Merkle proof that a Bitcoin transaction was
in a block of that chain under enough confirmations, enabling trustless
ether-for-bitcoin swaps. Faking such a proof means building a heavier chain
of headers than honest Bitcoin miners, so the relay is safe as long as no
attacker can out-mine them: the light-client assumption of Nakamoto's
simplified payment verification.

*Implementation:* :class:`blockchainkit.channels.systems.relay.BTCRelay`
on :class:`~blockchainkit.contracts.systems.world.World`, storing
:class:`~blockchainkit.structures.systems.block.BlockHeader` objects mined
by :func:`~blockchainkit.channels.systems.relay.mine_header` and verifying
:class:`~blockchainkit.structures.systems.merkle.MerkleTree` proofs. The
teaching chain has no difficulty retargeting, so the relay demands a fixed
minimum difficulty instead, and relayers earn no fees.

*References:* J. Chow, *BTC Relay*, ConsenSys,
`github.com/ethereum/btcrelay <https://github.com/ethereum/btcrelay>`__
(2016).

.. minigallery:: ../../examples/channels/interoperability/plot_02_btc_relay.py

2017 -- Sprites and General State Channels
------------------------------------------

On a chain with contracts, a channel can be judged by a contract instead of
enforced by pre-signed transactions. An adjudicator contract holds the
deposits; the parties sign successive numbered versions of any state,
balances or the position of a game; and either can submit the latest. The
other has a dispute period to answer with a newer version, and the contract
settles on the highest, so publishing an old version gains nothing.

Sprites also shortened multi-hop payments. In Lightning, a payment over
``n`` hops locks amount :math:`a_i` on hop ``i`` until an expiry
:math:`\Delta` later than the next hop's: each hop learns the preimage only
when the next one claims, and needs time :math:`\Delta` to claim in turn.
Expiries thus grow towards the sender. Sprites added a global *preimage
manager*, a contract where anyone can publish the preimage. Every hop
settles by asking it whether the preimage was published by one common
deadline, so no hop waits for the next, and collateral is locked for the
same time on every hop,

.. math::

   \sum_i a_i\, (n - i)\,\Delta \;\longrightarrow\; \sum_i a_i\,\Delta.

*Implementation:* :class:`blockchainkit.channels.systems.state_channels.StateChannel`
and :class:`~blockchainkit.channels.systems.state_channels.PreimageManager`,
contracts on :class:`~blockchainkit.contracts.systems.world.World`, with
:func:`~blockchainkit.channels.systems.state_channels.htlc_expiries`,
:func:`~blockchainkit.channels.systems.state_channels.sprites_expiries` and
:func:`~blockchainkit.channels.systems.state_channels.collateral_time`. The
adjudicator decides disputes by version number alone; Sprites and later
designs also let a party advance an application's state on chain when the
other stops responding.

*References:* A. Miller, I. Bentov, S. Bakshi, R. Kumaresan and P. McCorry,
*Sprites and state channels: payment networks that go faster than
Lightning*, Financial Cryptography and Data Security (2019);
`arXiv:1702.05812 <https://arxiv.org/abs/1702.05812>`__ (2017).

.. minigallery:: ../../examples/channels/payment_channels/plot_04_sprites_state_channels.py

2017 -- Plasma: Child Chains with Exit Games
--------------------------------------------

Channels serve a fixed set of parties; Poon and Buterin's Plasma moved
whole chains off the main one. An operator runs a child chain and posts
only its block roots to a root-chain contract, which cannot check the
transactions behind them. Coins stay safe because their owners can always
*exit*: prove ownership on the root chain and wait out a challenge period,
in which anyone may prove the exit invalid. In Plasma Cash (2018) every coin
has a slot in each block's sparse Merkle tree, so its history is a chain of
transfers, each proved by a Merkle branch. An exit names the coin's last
transfer, to the exiter, and the one before it; a challenger cancels it by
showing

.. math::

   \text{a later spend by the exiter} \quad\text{or}\quad
   \text{an earlier spend of its parent}.

The first proves the exiter has already given the coin away; the second,
that the coin left the previous owner before the exiter's transfer, so
that transfer was a double spend. Exits only work while users can see the
blocks. An operator who withholds them can hide invalid transactions, so
every user must exit, and the root chain may not have room for them all:
the data-availability problem that rollups later solved by posting the
data.

*Implementation:* :class:`blockchainkit.channels.systems.plasma.PlasmaChain`
with :func:`~blockchainkit.channels.systems.plasma.sign_transfer`, on
:class:`~blockchainkit.structures.systems.sparse_merkle.SparseMerkleTree`.
The root-chain contract is a Python object rather than a contract on
:class:`~blockchainkit.contracts.systems.world.World`, and Plasma Cash's
invalid-history challenge and bonds are omitted.

*References:* J. Poon and V. Buterin, *Plasma: scalable autonomous smart
contracts*, white paper (August 2017); V. Buterin, *Plasma Cash: Plasma
with much less per-user data checking*, ethresear.ch (March 2018).

.. minigallery:: ../../examples/channels/scaling/plot_01_plasma_exit_games.py

2018 -- eltoo: Channel Updates without Penalties
------------------------------------------------

Lightning's penalty punishes an honest mistake, such as publishing a stale
backup, as hard as theft. eltoo replaces punishment with replacement. Each
state is an *update* transaction, which may spend the funding output or any
earlier update, and a *settlement*, which pays out after a delay. If a
party publishes an old update, the other answers within the delay with a
newer one that spends it, so only the last update settles and nobody needs
to be punished. This needs two properties. First, the latest update must be
able to spend whichever earlier update appears, which a normal signature
cannot do, since it commits to the exact output spent. Updates are
therefore signed with ``SIGHASH_NOINPUT``, which omits the spent output.
Second, an old update must not be able to spend a newer one, so each update
output requires the spending transaction's lock time to exceed its own state
number, and update ``m`` carries lock time ``m``:

.. math::

   \text{update } m \text{ may spend update } n \iff m \ge n + 1.

*Implementation:* :class:`blockchainkit.channels.systems.eltoo.EltooChannel`,
whose update outputs are Script with both branches checked by
:func:`~blockchainkit.vm.systems.script.verify_script`. A signature over a
message without the spent output stands in for ``SIGHASH_NOINPUT``
(BIP 118, not yet active on Bitcoin), and the settlement delay is checked
with ``OP_CHECKLOCKTIMEVERIFY`` against the update's age.

*References:* C. Decker, R. Russell and O. Osuntokun, *eltoo: a simple
layer2 protocol for Bitcoin*, white paper (2018).

.. minigallery:: ../../examples/channels/payment_channels/plot_05_eltoo.py

2018 -- OmniLedger and Sharding
-------------------------------

Splitting validators into shards multiplies throughput, but each shard is
as weak as its own committee. OmniLedger reshuffles validators every epoch
using unbiasable randomness (RandHound), so an adversary with a fraction of
all validators cannot gather them in one shard. A committee runs Byzantine
agreement, which fails once a third or more of its members are malicious.
A committee of ``m`` drawn at random from ``N`` validators, ``M`` of them
malicious, reaches that point with the hypergeometric probability

.. math::

   P(X \ge m/3) = \sum_{x \ge m/3}
   \frac{\binom{M}{x}\binom{N-M}{m-x}}{\binom{N}{m}},

which falls exponentially with ``m`` while :math:`M/N` stays below a third.
A payment whose inputs live on several shards must not succeed on some and
fail on others, so OmniLedger uses Atomix: every input shard locks its
input, then the output shard commits the payment if all accepted, or every
input is unlocked.

*Implementation:* :func:`blockchainkit.channels.systems.sharding.shard_failure_probability`,
:func:`~blockchainkit.channels.systems.sharding.assign_shards`,
:func:`~blockchainkit.channels.systems.sharding.compromised_epochs` and
:func:`~blockchainkit.channels.systems.sharding.atomix_transfer`. A seeded
shuffle stands in for RandHound, and shards' acceptances are taken on
trust rather than as signed proofs from each committee.

*References:* E. Kokoris-Kogias, P. Jovanovic, L. Gasser, N. Gailly,
E. Syta and B. Ford, *OmniLedger: a secure, scale-out, decentralized
ledger via sharding*, IEEE Symposium on Security and Privacy (2018),
583–598. `DOI <https://doi.org/10.1109/SP.2018.000-5>`__.

.. minigallery:: ../../examples/channels/scaling/plot_02_omniledger_sharding.py

2018 -- zk-Rollups: Validity Proofs for Batched Transactions
------------------------------------------------------------

Plasma kept data off chain and paid for it with exit games. A rollup posts
its transactions, compressed, to the chain, so anyone can rebuild its
state, and Barry Whitehat's *roll_up* and Buterin's proposal of 2018 added
a succinct proof that the posted state root follows from them. The contract
verifies the proof at a fixed cost :math:`G_{\text{verify}}` and never
re-executes, so in a batch of ``n`` transactions of ``b`` bytes each, at 16
gas per byte of calldata, the gas per transaction tends to the cost of its
data:

.. math::

   g(n) = \frac{G_{\text{verify}}}{n} + 16\,b
   \quad\text{vs.}\quad 21\,000 \text{ on chain}.

A sound proof system admits no proof of a false state root, so a batch is
final as soon as it is accepted, with no challenge period.

*Implementation:* :class:`blockchainkit.channels.systems.rollups.ZKRollup`,
with :func:`~blockchainkit.channels.systems.rollups.batch_gas` and
:func:`~blockchainkit.channels.systems.rollups.state_root`. There is no
proof system: a :class:`~blockchainkit.channels.core.base.ValidityProof`
states what it proves, and verification re-executes the batch, standing in
for a SNARK verifier. Invalid transactions are skipped, as rollups do.

*References:* Barry Whitehat, *roll_up*,
`github.com/barryWhiteHat/roll_up <https://github.com/barryWhiteHat/roll_up>`__
(2018); V. Buterin, *On-chain scaling to potentially ~500 tx/sec through
mass tx validation*, ethresear.ch (September 2018).

.. minigallery:: ../../examples/channels/scaling/plot_03_zk_rollups.py

2018 -- Al-Bassam, Sonnino and Buterin: Fraud Proofs and Data-Availability Sampling
-----------------------------------------------------------------------------------

Fraud proofs let a light client reject an invalid block once an honest full
node objects, but only if the block's data is available: a producer can
publish a header and withhold the data, and then nobody can prove fraud.
Al-Bassam, Sonnino and Buterin extend the data with a Reed-Solomon code and
commit to the shares, so that any half rebuilds the block. Withholding a
few shares then hides nothing: to keep any data out of reach, the producer
must withhold a fraction :math:`f > 1/2` of the shares. Each share a client
samples at random is then missing with probability ``f``, so a client that
samples ``s`` of them notices with probability

.. math::

   1 - (1 - f)^s \ge 1 - 2^{-s}.

A producer could instead publish shares that are not a valid codeword, so
that different halves rebuild different blocks; any node that rebuilds the
data catches this with an encoding fraud proof. Once enough clients'
samples are published, together they rebuild the block.

*Implementation:* :func:`blockchainkit.channels.systems.data_availability.extend`,
:func:`~blockchainkit.channels.systems.data_availability.simulate_sampling`,
:func:`~blockchainkit.channels.systems.data_availability.encoding_fraud_proof`
and :func:`~blockchainkit.channels.systems.data_availability.verify_encoding_fraud_proof`,
on :mod:`~blockchainkit.channels.systems.reed_solomon` and
:class:`~blockchainkit.structures.systems.merkle.MerkleTree`. The code is
one-dimensional, so a fraud proof holds ``k + 1`` shares rather than the
paper's single row of a two-dimensional square.

*References:* M. Al-Bassam, A. Sonnino and V. Buterin, *Fraud and data
availability proofs: maximising light client security and scaling
blockchains with dishonest majorities*,
`arXiv:1809.09044 <https://arxiv.org/abs/1809.09044>`__ (2018).

.. minigallery:: ../../examples/channels/coding/plot_02_data_availability_sampling.py

2019 -- Optimistic Rollups and Fraud-Proof Challenge Windows
------------------------------------------------------------

Validity proofs were expensive to generate for general computation. An
optimistic rollup, as Adler and Quintyne-Collins proposed in 2019, posts
batches and state roots without proofs, and a root becomes final once a
challenge window has passed with no fraud proven. Re-executing a whole
batch on chain to settle a dispute would cost what the rollup saves, so the
dispute is narrowed by bisection, as in Arbitrum. Asserter and challenger
agree on the state before the batch and disagree on the state after it.
The asserter posts the state root at the midpoint; the challenger says
which half it disputes, and that half is split in turn, until they disagree
about one transaction, which the chain re-executes. A batch of ``n``
transactions takes

.. math::

   \lceil \log_2 n \rceil \text{ rounds}.

Any one honest watcher can win the game, so one suffices; the price is that
withdrawals wait for the window.

*Implementation:* :class:`blockchainkit.channels.systems.rollups.OptimisticRollup`
and :func:`~blockchainkit.channels.systems.rollups.bisect`. The bisection
game runs in one call rather than as alternating transactions, and the
challenger's own bond and the censorship of challenges are not modelled.

*References:* J. Adler and M. Quintyne-Collins, *Building scalable
decentralized payment systems*,
`arXiv:1904.06441 <https://arxiv.org/abs/1904.06441>`__ (2019);
H. Kalodner, S. Goldfeder, X. Chen, S. M. Weinberg and E. W. Felten,
*Arbitrum: scalable, private smart contracts*, 27th USENIX Security
Symposium (2018).

.. minigallery:: ../../examples/channels/scaling/plot_04_optimistic_rollups.py

2019 -- Watchtowers and PISA: Guarding Offline Channel Parties
--------------------------------------------------------------

A Lightning party is safe only while it watches the chain: a revoked
commitment must be answered within its delay. A *watchtower* watches for
it. After each update the party gives the tower half the revoked
commitment's transaction identifier as a hint, and a presigned penalty
encrypted under the whole identifier (Dryja, 2016). The tower watches for
a transaction whose identifier starts with the hint; until one appears it
cannot decrypt the penalty and learns nothing about the channel, and then
it can publish only a penalty that pays the party. PISA made towers
accountable: a tower signs a receipt for each appointment and locks a
deposit, which the party claims if the revoked commitment named in the
receipt was published and its funds were taken by the cheater. A party
that checks the chain every ``T`` blocks, with a delay of ``d`` blocks,
misses a cheat published at a random time with probability
:math:`1 - d/T` when :math:`d < T`, and loses only if the tower also fails:

.. math::

   P(\text{loss}) = \max\!\left(0,\, 1 - \tfrac{d}{T}\right)
   \cdot P(\text{tower fails}).

*Implementation:* :class:`blockchainkit.channels.systems.watchtowers.Watchtower`,
:func:`~blockchainkit.channels.systems.watchtowers.make_appointment`,
:func:`~blockchainkit.channels.systems.watchtowers.verify_receipt` and
:func:`~blockchainkit.channels.systems.watchtowers.tower_liable`, guarding a
:class:`~blockchainkit.channels.systems.lightning.LightningChannel`. The
blob is encrypted with a SHA-256 keystream rather than an authenticated
cipher, and PISA's recourse is a function rather than its arbitration
contract for general state channels.

*References:* P. McCorry, S. Bakshi, I. Bentov, S. Meiklejohn and
A. Miller, *Pisa: arbitration outsourcing for state channels*, ACM
Conference on Advances in Financial Technologies (AFT 2019).
`DOI <https://doi.org/10.1145/3318041.3355461>`__; T. Dryja,
*Unlinkable outsourced channel monitoring*, Scaling Bitcoin, Milan (2016).

.. minigallery:: ../../examples/channels/payment_channels/plot_06_pisa_watchtowers.py

2019 -- Balance Probing and Payment Privacy in Lightning
--------------------------------------------------------

Lightning announces each channel's capacity but hides how it is split, and
so how much each side has paid. Herrera-Joancomartí and co-authors showed
that anyone with a channel can learn the split. The prober routes a payment
through the target channel with a payment hash nobody can claim: if the
channel cannot forward the amount, the error comes from that hop; if it
can, the payment fails at the recipient with a different error. Either way
no money moves, and each probe answers one question: is the balance at
least the amount? Halving the range of possible balances each time, a
binary search finds the balance of a channel of capacity :math:`C`, one of
:math:`C + 1` values, exactly in

.. math::

   \lceil \log_2 (C + 1) \rceil \text{ probes}.

Repeated over time, probing reveals payments themselves.

*Implementation:* :func:`blockchainkit.channels.systems.probing.probe_balance`
over :class:`~blockchainkit.channels.systems.routing.ChannelNetwork`, which
routes hash time-locked payments over a
:class:`~blockchainkit.network.systems.topology.Graph`, with fees and
expiries computed hop by hop from the recipient. Errors return in the
clear; the deployed protocol wraps them in onion encryption, which hides
nothing from the sender, who is the prober.

*References:* J. Herrera-Joancomartí, G. Navarro-Arribas, A. Ranchal-Pedrosa,
C. Pérez-Solà and J. Garcia-Alfaro, *On the difficulty of hiding the
balance of Lightning Network channels*, ACM Asia Conference on Computer and
Communications Security (AsiaCCS 2019).
`DOI <https://doi.org/10.1145/3321705.3329812>`__.

.. minigallery:: ../../examples/channels/routing/plot_01_balance_probing.py

2022 -- Bridge Failures: the Ronin and Wormhole Exploits
--------------------------------------------------------

Most bridges do not verify the other chain at all: a committee signs
withdrawals, and the bridge is as safe as its keys and the code that checks
their signatures. In February 2022, Wormhole's Solana program accepted an
account supplied by the caller as evidence that the guardians' signatures
had been checked; an attacker supplied a forged one, skipped the check, and
minted 120,000 wrapped ether. In March, Ronin, which released funds on 5 of
9 validator signatures, lost 173,600 ether and 25.5 million USDC. One
company ran four validators and still held permission to sign for a fifth,
so breaking into that one company yielded all five signatures. For ``n``
independent keys each compromised with probability ``p``, a ``t``-of-``n``
bridge falls with

.. math::

   \sum_{k=t}^{n} \binom{n}{k} p^k (1-p)^{n-k},

which is tiny for small ``p`` and large ``t``. But keys held by one party
are not independent: they fall together, and Ronin's five signatures took
a single breach.

*Implementation:* :class:`blockchainkit.channels.systems.bridges.ValidatorBridge`,
:class:`~blockchainkit.channels.systems.bridges.GuardianVerifier`,
:class:`~blockchainkit.channels.systems.bridges.WormholeBridge` and
:class:`~blockchainkit.channels.systems.bridges.ForgedVerifier`, contracts on
:class:`~blockchainkit.contracts.systems.world.World`. Solana's accounts
become a caller-supplied verifier contract, and minting and redeeming
wrapped ether happen in one contract instead of on two chains.

*References:* Ronin Network, *Community alert: Ronin validators
compromised* (29 March 2022); Wormhole, *Wormhole incident report*
(February 2022); S.-S. Lee, A. Murashkin, M. Derka and J. Gorzny, *SoK: not
quite water under the bridge: review of cross-chain bridge hacks*,
`arXiv:2210.16209 <https://arxiv.org/abs/2210.16209>`__ (2022).

.. minigallery:: ../../examples/channels/interoperability/plot_03_bridge_exploits.py
