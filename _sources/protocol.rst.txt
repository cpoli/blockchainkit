:orphan:

Exact conventions and model boundaries
======================================

This page specifies exact rules for readers implementing or inspecting the model. It is
optional on a first reading. Start with :doc:`/start_here` for the concepts and
:doc:`/quickstart` for a complete worked payment.

Byte and number conventions
---------------------------

Hash inputs are bytes; callers explicitly encode text. Digests are 32-byte
values, and proof-of-work interprets them as unsigned big-endian integers.
Amounts, sequence numbers, heights, and timestamps are integers. A value of
the wrong type (including a boolean, a float, or a string) raises ``TypeError``;
an integer out of range raises ``ValueError``. Simulation seeds must be integers. No binary floating-point
amounts enter consensus state. Transaction amounts and block fields fit in
unsigned 64-bit integers. Account balances can grow beyond that per-transfer
bound, using Python's exact integers.

Signatures and accounts
-----------------------

Accounts are lowercase SHA-256 hex digests of uncompressed secp256k1 public
points: ``0x04 || x[32] || y[32]``. The signature challenge is SHA-256 of:

.. code-block:: text

   "blockchainkit:schnorr:v1:{p}:{a}:{b}:{order}:"
   || encode(generator) || encode(commitment) || encode(public) || message

The digest is reduced modulo the subgroup order. A signature is the point
``R`` and scalar ``s = k + challenge*x mod order``. Verification checks
canonical coordinates, subgroup membership, scalar bounds, and the Schnorr
equation. Subgroup membership costs one extra scalar multiplication per point,
so it is skipped when Hasse's bound proves the cofactor is 1
(``2*order > p + 1 + 2*(isqrt(p) + 1)``); then every curve point is in the
subgroup. This holds for secp256k1 and the toy curve. This format differs from BIP-340, ECDSA, and Bitcoin addresses.
Private keys and fresh signing nonces lie in ``[1, order)``.

Transactions and replay
-----------------------

The signed payload is a JSON object with exactly these fields:
``version=1``, ``chain_id``, ``sender`` (hex public point), ``recipient``,
``amount``, and ``nonce``. Encoding uses sorted keys, compact separators,
ASCII escapes, and UTF-8 bytes. There are no float-valued fields. This is
a package-specific encoding, not a general implementation of canonical JSON.

Signed transaction bytes encode another object with ``payload`` (that JSON
as a string) and ``signature`` (``[[Rx, Ry], s]`` or null). A transaction's
signature must be a ``SchnorrSignature`` or absent. The transaction ID
hashes those signed bytes. The ledger checks the signature, chain ID,
expected next sender nonce, and sufficient funds. It consumes a nonce even
for a self-transfer. Batch application is atomic.

The account nonce and signing nonce solve different problems. Account nonces
are public sequence numbers preventing replay. Signing nonces are secret,
fresh cryptographic scalars; their reuse can reveal a key.

Merkle commitments
------------------

* Leaf: ``SHA256(0x00 || payload)``.
* Internal node: ``SHA256(0x01 || left_digest || right_digest)``.
* Odd unpaired node: promote the digest unchanged.
* Final root: ``SHA256(0x02 || leaf_count[8, big-endian] || top_digest)``.
* Empty tree: the same final-root formula with count zero and no top digest.

Proofs carry a zero-based index, leaf count, and bottom-up siblings, using
``None`` for an unpaired promotion. Verification rejects extra/missing levels
and inconsistent positions. The trusted root binds the count. These conventions
deliberately differ from Bitcoin's odd-leaf duplication convention.

Block headers and chain selection
---------------------------------

Header JSON uses ``version=1``, ``previous_hash``, ``merkle_root`` (both hex),
``height``, ``timestamp``, ``difficulty``, and ``nonce``. The block hash is
one SHA-256 of this encoding. All transaction bytes are committed by the root.
Mining varies only the header nonce: the Merkle root is computed once per
block, not once per attempt.

For difficulty ``d``, the inclusive target is ``2**(256-d)-1``. Each valid
block contributes ``2**d`` units of cumulative expected work. Genesis fixes
the difficulty; a child cannot choose a lower difficulty to gain acceptance.
The selected tip maximizes work, breaking ties by the smaller hash. Height
must increment by one; timestamps cannot decrease along a branch. There is
no claim that a supplied timestamp matches civil time.

Genesis must be mined, empty, at height zero, with a zero parent hash. The
initial ledger allocation and chain ID are shared out-of-band simulation
configuration; they are not committed in genesis. Peers must be configured
identically. A node rejects unknown parents rather than silently buffering
them; synchronization examples send parents before children.

There is no difficulty adjustment, issuance, reward, fee market, persistent
database, production mempool, or live chain interoperability. Fork state is
retained in memory for teaching, without pruning.

Network semantics
-----------------

Links are undirected. Latency is sampled uniformly from inclusive integer
bounds, with a minimum of one tick. Duplicate payload hashes are suppressed
per peer; origin receipt counts as a delivery. Equal-time events are ordered
by a monotonically increasing sequence number. Peer enumeration is sorted
to avoid dependence on input mapping order.

Disconnect/reconnect creates a new link generation: old in-flight events
are discarded. Healing a partition does not trigger automatic anti-entropy;
the experiment explicitly retransmits. A receive callback can reject a payload,
which remains seen and is not forwarded by that peer. Exceptions from callbacks
propagate to the caller; they are not silently interpreted as rejection, and the
payload is not marked seen, so it can be delivered again.

VM instruction set
------------------

Each instruction is ``(opcode, operand)``, where the opcode is a string.
Operand-free instructions use ``None``. Every instruction costs one gas unit, including ``STOP``. Whole
program syntax is validated before execution, even for unreachable code.

.. list-table:: Stack and control operations
   :header-rows: 1
   :widths: 24 76

   * - Opcode
     - Semantics
   * - PUSH n
     - Push a 256-bit unsigned integer.
   * - ADD, SUB, MUL
     - Pop right then left; push the result modulo 2**256.
   * - DIV
     - Unsigned integer division; division by zero raises VMError.
   * - EQ, LT
     - Compare left and right; push 0 or 1.
   * - DUP, DROP, SWAP
     - Duplicate, remove, or swap stack elements.
   * - LOAD k, STORE k
     - Load a slot (default 0), or pop into a slot.
   * - JMP i
     - Jump to an absolute instruction index.
   * - JZ i
     - Pop a condition and jump if zero.
   * - STOP
     - Finish successfully; falling off the end also succeeds.

Storage is copied before execution. Underflow, invalid operands, out-of-gas,
and stack overflow raise ``VMError`` without mutating input state. Returned
storage is read-only. Gas bounds interpreter steps, not all host CPU/memory
costs: parsing/materializing a huge program is not metered. This teaching VM
is not a hostile-code sandbox and is not connected to the transfer ledger.

Contract world model
--------------------

:class:`~blockchainkit.contracts.systems.world.World` models the EVM's call
semantics, not its bytecode. Contracts are Python classes; public methods
(names without a leading underscore) are dispatched by name, not by a 4-byte
selector, and values are Python objects rather than 256-bit words, with
unbounded integer arithmetic. Field ``i`` of a contract's ``layout`` is
storage slot ``i``, and entry ``k`` of a mapping field is slot ``(i, k)``
rather than a Keccak hash; writing 0 clears a slot, and an unwritten slot
reads 0. ``delegatecall`` runs the callee's code on the caller's storage
through the callee's layout.

Every call runs on a snapshot of balances, code, storage, nonces and
events: a revert (:class:`~blockchainkit.contracts.core.base.ContractError`)
restores the snapshot of that call only, and the caller sees the error. A
Python exception that is not a revert restores the snapshot and propagates.
A reverted transaction still increments the sender's nonce and reports the
gas it used, but no ether is charged for gas.

.. list-table:: Teaching gas schedule
   :header-rows: 1
   :widths: 30 20 50

   * - Operation
     - Gas
     - Ethereum, for comparison
   * - Transaction
     - 21,000
     - 21,000
   * - Storage read / write
     - 800 / 5,000
     - 2,100 cold read; 20,000 to fill an empty slot, 2,900 to change one
   * - Call, create, log
     - 700, 32,000, 375
     - 100-2,600 (warm/cold), 32,000, 375 plus data
   * - ``send`` stipend
     - 2,300
     - 2,300

A call forwards at most 63/64 of the remaining gas (EIP-150), and the
default call-depth limit is 128 rather than 1024, to stay within Python's
recursion limit. ``selfdestruct`` deletes code and storage at once rather
than at the end of the transaction. Contract addresses are
``"0x" + SHA-256(tag || canonical_json([deployer, nonce]))[-20:]`` for CREATE
and ``"0x" + SHA-256(tag || canonical_json([deployer, salt]) ||
code_hash)[-20:]`` for CREATE2, where the code hash covers the class and its
constructor arguments. Block hashes are SHA-256 of a seed and the block
number, available for the 256 previous blocks. The domain tags are in
:mod:`blockchainkit.constants`.

Economic models
---------------

:mod:`blockchainkit.economics` adds no consensus rule: the chain in
:mod:`blockchainkit.structures` still has no issuance, reward or fee. The
models are pure functions and seeded simulations, and the market contracts
run on the contract world model above.

- **Block subsidy.** :func:`~blockchainkit.economics.systems.rewards.block_subsidy`
  is Bitcoin's schedule exactly: ``50 * 10**8 >> (height // 210000)``
  satoshis, 0 from the 64th halving. ``issued_supply`` counts the genesis
  coins, which Bitcoin cannot spend.
- **Base fee.** :func:`~blockchainkit.economics.systems.fee_market.next_base_fee`
  follows the EIP-1559 integer update (maximum change 1/8, elasticity 2, a
  minimum increase of 1 above target). The simulated mempool holds only
  21,000-gas transfers, with values drawn uniformly and integer fees per
  gas; there are no nonces, replacements or blob fees.
- **Swaps.** :func:`~blockchainkit.economics.systems.amm.amount_out` is
  Uniswap V2's ``getAmountOut`` with the fee in basis points.
  :class:`~blockchainkit.economics.systems.amm.ConstantProductPool` keeps
  its reserves in storage rather than reading token balances, records
  shares in a mapping rather than an ERC-20 token, locks no minimum
  liquidity, and exposes the price before the current block's first trade
  in place of V2's cumulative time-weighted price.
- **Vaults.** :class:`~blockchainkit.economics.systems.lending.VaultEngine`
  uses Single-Collateral Dai's 150% ratio and 13% penalty, with integer
  prices in Dai per ether. A liquidator buys the collateral at the oracle
  price, rounded up to whole ether; there is no auction, stability fee or
  global settlement.
- **Mining games.** :func:`~blockchainkit.economics.systems.mining_games.optimal_mining_revenue`
  caps both branches at ``max_lead`` blocks and stops value iteration when
  the gain's sign is certain, so the result is a lower bound accurate to
  ``tolerance``.
- **Auctions and builders.** Values are independent and uniform; ties in
  :func:`~blockchainkit.economics.systems.auctions.first_price_auction` and
  :func:`~blockchainkit.economics.systems.auctions.second_price_auction`
  go to the alphabetically first bidder. Builder auctions in
  :func:`~blockchainkit.economics.systems.pbs.simulate_pbs` are sealed and
  second-price, without relays.

Channels, rollups and bridges
-----------------------------

:mod:`blockchainkit.channels` adds no consensus rule to the chain in
:mod:`blockchainkit.structures`. Channel outputs are
:mod:`blockchainkit.vm.systems.script` programs, and the relay, state
channel and bridges are contracts on the world model above. Off-chain
messages are signed as ``tag || canonical_json(fields)`` under the
``CHANNEL_DOMAIN``, ``PLASMA_DOMAIN``, ``BRIDGE_DOMAIN`` and
``WATCHTOWER_DOMAIN`` tags of :mod:`blockchainkit.constants`, with RFC 6979
signing nonces.

- **Scripts.** There is no ``OP_CHECKMULTISIG``: a 2-of-2 output is
  ``<A> OP_CHECKSIG OP_VERIFY <B> OP_CHECKSIG``. There is no
  ``OP_CHECKSEQUENCEVERIFY``: a relative delay is written with
  ``OP_CHECKLOCKTIMEVERIFY`` and the spender passes the output's age as the
  lock time. eltoo's ``SIGHASH_NOINPUT`` is a signature over a message that
  omits the spent output.
- **Lightning.** The revocation key is the sum of the holder's
  per-commitment point and the counterparty's base point, without
  Lightning's hashed tweaks. Per-commitment secrets are a SHA-256 hash
  chain used backwards; there are no in-channel HTLC outputs or fees.
- **Routing.** :class:`~blockchainkit.channels.systems.routing.ChannelNetwork`
  routes by fewest hops among channels with enough capacity, with one fee
  policy (base fee plus millionths) and one ``cltv_delta`` for every node.
  Errors are returned in the clear, without onion encryption.
- **Relay.** :class:`~blockchainkit.channels.systems.relay.BTCRelay`
  stores teaching :class:`~blockchainkit.structures.systems.block.BlockHeader`
  objects and requires a fixed minimum difficulty instead of retargeting.
- **Plasma.** Each block is a sparse Merkle tree of depth 16 keyed by the
  coin's 8-byte identifier; leaves are the canonical JSON of the transfer.
  Only the spend and double-spend challenges exist, without bonds.
- **Rollups.** The state root is a :class:`~blockchainkit.structures.systems.merkle.MerkleTree`
  over ``ROLLUP_DOMAIN || canonical_json([account, balance])``, sorted by
  account. Invalid transfers are skipped. A validity proof is verified by
  re-executing the batch; gas is the fixed cost plus 16 per calldata byte.
- **Data availability.** Reed-Solomon codes are one-dimensional and
  systematic over the integers modulo 65,537; shares are committed as
  8-byte big-endian leaves of a Merkle tree.
- **Bridges.** Validators sign ``BRIDGE_DOMAIN || canonical_json([bridge,
  recipient, amount, nonce])``. Wrapped ether is minted and redeemed by the
  same contract.

Proof systems
-------------

:mod:`blockchainkit.proofs` adds no consensus rule: no block or transaction
carries a proof. Its parameters are chosen so that every number can be
inspected, not for security.

- **Field.** Polynomials, circuits, FRI and STARKs work over BabyBear,
  :math:`p = 15 \cdot 2^{27} + 1`, whose multiplicative group (generator 31)
  has power-of-two subgroups up to :math:`2^{27}`. Coefficient tuples list
  the constant term first. Deployed systems use larger fields or extension
  fields for their challenges; Schwartz-Zippel errors here are about
  :math:`d / 2^{31}`.
- **Pairing.** :data:`~blockchainkit.proofs.systems.pairing.PAIRING_CURVE`
  is :math:`y^2 = x^3 + x` over the 35-bit prime :math:`12p - 1`, with a
  generator of order :math:`p`. The pairing is the symmetric reduced Tate
  pairing with the distortion map :math:`(x, y) \mapsto (-x, iy)`, computed
  by Miller's algorithm with denominator elimination. Its discrete
  logarithms take about :math:`2^{16}` steps, so every trusted setup can be
  broken by brute force.
- **Groth16 and PLONK.** Groth16 places :math:`B` in the same group as
  :math:`A`. Every R1CS gets one row :math:`x_i \cdot 0 = 0` for the
  constant and each public input, as Bellman and snarkjs do. PLONK opens
  every polynomial at :math:`\zeta` (no linearization), adds no blinding,
  and has no public inputs; its copy-constraint cosets are shifted by 31
  and 961.
- **Transcripts.** Fiat-Shamir challenges are SHA-256 over
  ``TRANSCRIPT_DOMAIN``, a protocol label, and length-prefixed labelled
  messages, reduced modulo the field. Interactive protocols (sum-check,
  IP = PSPACE, the PCP verifier, Kilian) draw challenges from a seeded
  ``random.Random`` instead.
- **Zerocash.** Hashes are MiMC-7 with 12 rounds in Miyaguchi-Preneel
  mode, round constants from SHA-256 under ``MIMC_DOMAIN``. Notes are
  committed as :math:`H(H(\mathit{owner}, v), H(\rho, r))`, owners are
  :math:`H(\mathit{sk}, 0)`, nullifiers :math:`H(\mathit{sk}, \rho)`, and
  the commitment tree pads with zeros. A spend has one input and one output
  and range-checks the output to 16 bits.
- **Bulletproofs and Halo.** Both run in the multiplicative
  ``TEACHING_GROUP`` of :mod:`blockchainkit.crypto`, with generators hashed
  into it under ``IPA_GENERATOR_DOMAIN``. Halo's commitments are not
  blinded, and its accumulation is verified in Python, not in a circuit.
- **FRI and STARKs.** Leaves are 8-byte big-endian field elements in a
  :class:`~blockchainkit.structures.systems.merkle.MerkleTree`. FRI folds
  by two down to a constant on the coset :math:`31 \langle \omega \rangle`;
  query positions are reduced modulo half the domain. The STARK proves only
  the Fibonacci recurrence from 1, 1, with a blowup of 8 by default.

Fraud models
------------

:mod:`blockchainkit.fraud` adds no consensus rule. Its scam contracts run on
the contract world model above, and its detectors are pure functions over
simulated transfers, trades and prices.

- **Merkle sum trees.** A leaf is
  ``SHA256(SUM_LEAF_DOMAIN || canonical_json([salt.hex(), label, balance]))``
  with the balance as its sum; a node is
  ``SHA256(SUM_NODE_DOMAIN || canonical_json([left_sum, right_sum]) || left || right)``
  with the two sums added. Odd nodes are promoted unchanged. Verification
  rejects a negative balance or sibling sum.
- **Proofs of solvency.** Pedersen commitments in the 62-bit
  ``TEACHING_GROUP``. OR proofs follow Cramer, Damgård and Schoenmakers with
  Fiat-Shamir challenges ``SHA256(SOLVENCY_DOMAIN || canonical_json([p, q, g,
  commitment, value, A0, A1])) mod q``; range proofs commit to each of 16
  bits. Unlike Provisions, nothing proves knowledge of the owned addresses'
  keys or that two exchanges do not share an address.
- **Malleability.** A second signature by the exchange over the same
  payment stands in for a third party re-encoding a Bitcoin signature.
- **Verified source.** Code is compared by Python class, not compiled
  bytecode; :func:`~blockchainkit.fraud.systems.verification.effective_code`
  follows only EIP-1967 proxies.
- **Honeypots.** The Solidity-level techniques (inheritance disorder,
  uninitialised storage structs, ``var`` type deduction and the skipped
  empty string literal) are reproduced by their effect on storage and
  arguments, with no compiler or parser. :func:`~blockchainkit.fraud.systems.honeypots.explorer_view`
  lists every top-level call and only those internal calls that carry
  ether, as block explorers did around 2018.
- **Markets.** Prices follow a log-normal walk with linear impact
  (:func:`~blockchainkit.fraud.systems.manipulation.simulate_bot_market`)
  or a fee-free constant-product market starting with a million coins
  (:func:`~blockchainkit.fraud.systems.manipulation.simulate_pump_and_dump`).
- **Look-alike addresses.** Candidates are the last 20 bytes of
  ``SHA256(LOOKALIKE_DOMAIN || canonical_json([seed, index]))``, not
  addresses derived from key pairs.
