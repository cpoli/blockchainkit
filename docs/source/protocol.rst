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
