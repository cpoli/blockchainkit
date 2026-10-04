Life of a payment
=================

Follow one payment, Alice paying Bob 25 units, from a private key to a block
buried under others, through a fork that undoes it and the reinclusion that
restores it. Each stage uses a different subpackage, and each stage answers a
different question: who authorized it, who knows about it, which history holds
it, and how sure we are.

All snippets use ``import blockchainkit as bk``. The keys and nonces are
teaching fixtures; never use fixed values like these for real money.

1. Keys and addresses
---------------------

Alice's private key is a number; her public key is a point on secp256k1; her
address is the hash of the public key (:doc:`/tutorials/hashes_everywhere`).

.. doctest::

   >>> alice_key, bob_key = 7, 11
   >>> alice_public = bk.crypto.public_key(alice_key)
   >>> alice = bk.structures.address(alice_public)
   >>> bob = bk.structures.address(bk.crypto.public_key(bob_key))
   >>> len(alice), alice == bk.crypto.sha256(bk.crypto.encode_point(alice_public)).hex()
   (64, True)

*Who can spend?* Whoever knows ``alice_key``. Nothing else identifies Alice.

2. Authorization: a signed transaction
--------------------------------------

The transaction names the sender's public key, the recipient, the amount, the
sender's *account nonce* and the chain ID, and is signed with a Schnorr
signature over all of them (:doc:`/tutorials/nonces_everywhere`).

.. doctest::

   >>> payment = bk.structures.Transaction(alice_public, bob, 25, 0)
   >>> payment.is_valid()
   False
   >>> payment = payment.signed(alice_key, signing_nonce=17)
   >>> payment.is_valid()
   True
   >>> from dataclasses import replace
   >>> replace(payment, amount=2500).is_valid()  # Any change breaks the signature.
   False

A valid signature says Alice authorized *this* payment. It does not say she
can afford it, or that she has not signed a conflicting one.

3. Validation against a state
-----------------------------

Each node keeps a ledger of balances and account nonces. Applying a payment
returns a new ledger and leaves the old one untouched; a payment that
overspends or reuses a nonce is rejected.

.. doctest::

   >>> genesis_state = bk.structures.Ledger({alice: 100})
   >>> after = genesis_state.apply([payment])
   >>> after.balances[bob], after.balances[alice], genesis_state.balances.get(bob, 0)
   (25, 75, 0)
   >>> greedy = bk.structures.Transaction(alice_public, bob, 101, 0).signed(alice_key, signing_nonce=19)
   >>> try:
   ...     genesis_state.apply([greedy])
   ... except ValueError:
   ...     print("rejected: insufficient funds")
   rejected: insufficient funds

4. Propagation: gossip
----------------------

Alice's node broadcasts the payment, and peers forward it to their neighbors.
For a while, peers disagree about what is pending.

.. doctest::

   >>> net = bk.network.SimulatedNetwork(["alice", "relay", "miner"], seed=1)
   >>> net.connect("alice", "relay", latency=(1, 3))
   >>> net.connect("relay", "miner", latency=(1, 3))
   >>> net.broadcast("alice", payment.txid)
   >>> _ = net.run(until=1)
   >>> sorted(d.recipient for d in net.deliveries)
   ['alice', 'relay']
   >>> _ = net.run()
   >>> sorted(d.recipient for d in net.deliveries)
   ['alice', 'miner', 'relay']

See :doc:`/api/gallery/network/events/plot_01_discrete_event_simulation`.

5. Inclusion: a mined block
---------------------------

A miner puts the payment in a block, whose header commits to the transactions
through a Merkle root, and searches for a nonce that makes the header's hash
small enough.

.. doctest::

   >>> genesis = bk.consensus.mine(bk.structures.Block(difficulty=4)).block
   >>> chain = bk.structures.Blockchain(genesis, genesis_state)
   >>> block = bk.consensus.mine(bk.structures.Block(genesis.hash, (payment,), 1, 1, 4)).block
   >>> bk.consensus.valid_pow(block), chain.add(block)
   (True, True)
   >>> chain.state.balances[bob]
   25

A light client that holds only the header can check inclusion with a Merkle
proof:

.. doctest::

   >>> proof = bk.structures.MerkleTree([payment.to_bytes()]).proof(0)
   >>> bk.structures.verify_proof(payment.to_bytes(), proof, block.merkle_root)
   True

6. Confirmation: how sure?
--------------------------

Each block mined on top makes reversal less likely. With an attacker holding
10% of the hash power, Nakamoto's calculation gives:

.. doctest::

   >>> [round(bk.consensus.attacker_success_probability(0.1, z), 5) for z in (1, 3, 6)]
   [0.20459, 0.01317, 0.00024]

This is why merchants wait for confirmations. There is no point at which a
proof-of-work payment becomes impossible to reverse, only ever less likely
(compare Casper's finality in :doc:`/tutorials/who_do_you_trust`).

7. A fork undoes it
-------------------

Meanwhile, another miner who never saw the payment built a longer branch. Every
node switches to the branch with the most work, and the payment's effect
disappears.

.. doctest::

   >>> rival = bk.consensus.mine(bk.structures.Block(genesis.hash, (), 1, 2, 4)).block
   >>> rival_2 = bk.consensus.mine(bk.structures.Block(rival.hash, (), 2, 3, 4)).block
   >>> chain.add(rival), chain.add(rival_2)
   (True, True)
   >>> chain.tip == rival_2, chain.state.balances.get(bob, 0)
   (True, 0)
   >>> len(chain.tips())  # Both branches are kept; only one is selected.
   2

The signature is still valid, and on the new branch Alice has not used account
nonce 0, so the payment is eligible again: back to the pending queue.

8. Reinclusion, and no replay
-----------------------------

.. doctest::

   >>> chain.state.apply([payment]).balances[bob]
   25
   >>> again = bk.consensus.mine(bk.structures.Block(rival_2.hash, (payment,), 3, 4, 4)).block
   >>> chain.add(again), chain.state.balances[bob]
   (True, 25)
   >>> try:
   ...     chain.state.apply([payment])
   ... except ValueError:
   ...     print("replay rejected: account nonce already used")
   replay rejected: account nonce already used

Had the winning branch contained a *conflicting* payment from Alice with the
same account nonce, the original would not have been eligible again, despite
its valid signature (see :doc:`/exercises/structures`, problem 7).

Where each question was answered
--------------------------------

.. list-table::
   :header-rows: 1
   :widths: 34 30 36

   * - Question
     - Answered by
     - Subpackage
   * - Did Alice authorize it?
     - Schnorr signature
     - :mod:`blockchainkit.crypto`
   * - Can she afford it? Is it a replay?
     - ledger state and account nonce
     - :mod:`blockchainkit.structures`
   * - Who knows about it?
     - gossip
     - :mod:`blockchainkit.network`
   * - Which history holds it?
     - proof of work and fork choice
     - :mod:`blockchainkit.consensus`
   * - How sure are we?
     - confirmations against an attacker's share
     - :mod:`blockchainkit.consensus`

The full simulation, with two peers, a partition, and a balance and queue
table, is :doc:`/api/gallery/structures/chain/plot_02_payment_lifecycle`.
