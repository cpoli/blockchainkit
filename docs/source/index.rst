blockchainkit
=============

.. include:: /_generated/vars.rst

**Cryptography and blockchains, understood through experiments.**

**blockchainkit** is a teaching toolkit spanning |num_subpackages| subpackages,
from public-key cryptography to replicated execution, under one small typed
API. Start with two people agreeing on a secret. Follow the ideas that make
it possible to prove knowledge, authenticate a payment, commit to a history,
compare competing histories, and execute a shared program. Each step links
an explanation to working Python, a figure, and an experiment you can change.

The :doc:`history </history/index>` is the spine of the package. Each
subpackage's history page traces the breakthroughs behind it and their
limitations, from Diffie-Hellman to Ethereum, each linked to the code and
the gallery example that reproduce it. Cryptography is central even though
it is not in the package name.

.. important::

   This is teaching software, not hardened cryptography or a node compatible
   with an existing blockchain. Tiny RSA and Diffie-Hellman parameters and
   variable-time curve arithmetic keep the mathematics visible; the Schnorr
   scheme is not BIP-340, and blocks are not Bitcoin or Ethereum wire formats.
   :doc:`/protocol` states every such choice precisely. For real systems, use
   audited libraries such as `cryptography <https://cryptography.io/>`__ or
   `libsecp256k1 <https://github.com/bitcoin-core/secp256k1>`__.

- :mod:`blockchainkit.crypto`: hashing and commitments, Diffie-Hellman and
  RSA, blind signatures, Shamir secret sharing, elliptic curves, and Schnorr
  proofs and signatures.
- :mod:`blockchainkit.structures`: Merkle trees and proofs, signed transfers,
  blocks, ledger state, and cumulative-work fork selection.
- :mod:`blockchainkit.consensus`: proof-of-work search and its expected
  cost, catch-up probabilities, and stake-weighted proposer selection.
- :mod:`blockchainkit.network`: peer graphs, Lamport and vector clocks,
  epidemic gossip and Byzantine reliable broadcast, the CAP trade-off,
  Kademlia with its Sybil and eclipse attacks, block relay, forks, and
  transaction privacy.
- :mod:`blockchainkit.vm`: a deterministic 256-bit stack machine with gas,
  traces and atomic failure; its assembler, expression compiler and bytecode
  verifier; Turing machines and busy beavers; Bitcoin Script with P2PKH and
  HTLCs; and smart contracts with the reentrancy and overflow attacks.

**blockchainkit** is part of a family of packages, with
`physicskit <https://cpoli.github.io/physicskit/>`_,
`mathematicskit <https://cpoli.github.io/mathematicskit/>`_ and
`chemistrykit <https://cpoli.github.io/chemistrykit/>`_, that share the same
architecture, API conventions, and history-driven documentation.

Choose a route
--------------

* **New to the topic?** Begin with :doc:`/start_here`. It explains the ideas
  using one imaginary payment, without assuming cryptography or finance
  knowledge. Keep the :doc:`/glossary` nearby.
* **Learn in order:** follow the :doc:`/tutorials/course`, with
  :doc:`/tutorials/solutions` to check your reasoning.
* **Learn the ideas:** read the :doc:`history </history/index>`, then run each
  linked experiment.
* **Build a chain:** follow :doc:`/quickstart` and the end-to-end payment
  experiment.
* **Run simulations:** read :doc:`/simulation` for assumptions and
  reproducibility.

Install and try it
------------------

.. code-block:: bash

   pip install -e ".[dev]"   # from a clone; see the quick start

``import blockchainkit`` loads only the standard library. Matplotlib and NumPy
are installed with the package for each subpackage's plotting helpers in
``visualizers``. Every gallery example can be downloaded as a script or a
notebook.

Conventionally imported as ``bk``:

.. code-block:: python

   import blockchainkit as bk

   alice = bk.crypto.public_key(7)
   signature = bk.crypto.sign(b"pay Bob 25", 7, nonce=11)
   print(bk.crypto.verify(b"pay Bob 25", signature, alice))  # True

.. toctree::
   :maxdepth: 2
   :caption: Getting started
   :hidden:

   start_here
   quickstart
   glossary

.. toctree::
   :maxdepth: 2
   :caption: Subpackages
   :hidden:

   subpackages/index

.. toctree::
   :maxdepth: 2
   :caption: History
   :hidden:

   history/index

.. toctree::
   :maxdepth: 2
   :caption: Examples
   :hidden:

   examples/index

.. toctree::
   :maxdepth: 2
   :caption: Tutorials
   :hidden:

   tutorials/index

.. toctree::
   :maxdepth: 2
   :caption: Model boundaries
   :hidden:

   protocol
   simulation

.. toctree::
   :maxdepth: 2
   :caption: API
   :hidden:

   api/index

.. toctree::
   :maxdepth: 1
   :caption: Development
   :hidden:

   contributing
