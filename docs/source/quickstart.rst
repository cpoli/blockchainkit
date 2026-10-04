Your first payment, step by step
================================

We will give Alice 100 imaginary units, have her pay Bob 25, and check the
result. You need basic Python, but no prior cryptography knowledge. Read
:doc:`/start_here` first if blocks, keys, or signatures are unfamiliar.

Install locally
---------------

Open a terminal in the package directory (the one containing ``pyproject.toml``),
with Python 3.10 or newer:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e . jupyterlab

The virtual environment keeps this project's dependencies together. The
``-e`` option makes edits to the local package available without reinstalling.
JupyterLab runs the notebooks.

Use ``pip install -e .`` for the package with its plotting helpers alone. No published
PyPI package is assumed. On Windows, activate with ``.venv\Scripts\activate``.

Authorize a transfer
--------------------

Alice signs with her private key; Bob is identified by an address derived from
his public key. The tiny fixed keys below make the lesson repeatable. Amounts
are imaginary integer units.

There are two different nonces here. ``nonce=0`` is Alice's public payment
sequence number: her next payment must use 1. ``signing_nonce=17`` is a secret
one-time value inside the signature. It is fixed only for this lesson; omit
that argument to let the package generate fresh randomness.

.. doctest::

   >>> import blockchainkit as bk
   >>> alice_key, bob_key = 7, 11
   >>> alice = bk.structures.address(bk.crypto.public_key(alice_key))
   >>> bob = bk.structures.address(bk.crypto.public_key(bob_key))
   >>> tx = bk.structures.Transaction(
   ...     sender=bk.crypto.public_key(alice_key), recipient=bob, amount=25, nonce=0
   ... )
   >>> tx = tx.signed(alice_key, signing_nonce=17)
   >>> tx.is_valid()
   True

``True`` confirms that the signature verifies. It does not check whether
Alice has enough money; the ledger checks that when applying the payment.

Create a chain and mine the payment
-----------------------------------

The initial allocation is a shared simulation input. This model has no coinbase
rewards, issuance schedule, transaction fees, or mempool.

.. doctest::

   >>> initial = bk.structures.Ledger({alice: 100})
   >>> genesis = bk.consensus.mine(bk.structures.Block(difficulty=5)).block
   >>> chain = bk.structures.Blockchain(genesis, initial)
   >>> candidate = bk.structures.Block(
   ...     previous_hash=genesis.hash, transactions=(tx,), height=1,
   ...     timestamp=1, difficulty=5,
   ... )
   >>> mined = bk.consensus.mine(candidate).block
   >>> chain.add(mined)
   True
   >>> chain.state.balances[alice], chain.state.balances[bob]
   (75, 25)
   >>> chain.state.nonces[alice]
   1

The genesis block is the starting block, at height 0. Our new block is at
height 1 and points to genesis using its hash. ``(tx,)`` is Python's notation
for a tuple containing one payment. The timestamp is a simulation number,
not real clock time. Difficulty 5 requires about 32 attempts on average;
individual searches can take fewer or more attempts.

``mine`` searches for a suitable block hash. ``chain.add`` checks the block
and payments before accepting them. The result is Alice with 75 and Bob with
25. Alice's next payment number is 1, so replaying this payment with number 0
will be rejected.

Verify inclusion independently
------------------------------

A Merkle proof answers “is this exact payment in this block?” The index 0
means the first payment. ``to_bytes()`` converts the payment to a consistent
byte representation, and ``merkle_root`` is the block's batch fingerprint.

.. doctest::

   >>> tree = bk.structures.MerkleTree(t.to_bytes() for t in mined.transactions)
   >>> bk.structures.verify_proof(tx.to_bytes(), tree.proof(0), mined.merkle_root)
   True

The proof establishes membership in that block. It does not establish that
the block is on the selected chain or that it will remain there. Explore this
distinction in :doc:`/api/gallery/structures/chain/plot_01_blockchain`.

Continue the course
-------------------

Every experiment in the :doc:`/examples/index` has a **Download Jupyter
notebook** link at the bottom of its page. Open a downloaded notebook with
``jupyter lab``, read it from top to bottom, and run its cells in that order.
The HTML pages contain the same explanations and figures without requiring a
running Python environment. To begin, ``notebooks/quickstart.ipynb`` takes one
payment from a signature to a mined block. Each experiment ends with an exercise.

If Python says ``ModuleNotFoundError``, check that your terminal or notebook
kernel uses the environment where you installed the package. If you get a
payment sequence error after rerunning only part of an experiment, restart
with a fresh ledger and run all cells in order.

Direct script execution creates figures without waiting for a GUI window.
For interactive inspection, use ``python -i examples/crypto/hashing/plot_04_sha256_avalanche.py`` and
then call ``matplotlib.pyplot.show()``. Documentation build instructions and
developer tools are covered in :doc:`/contributing`.
