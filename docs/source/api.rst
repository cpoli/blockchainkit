API reference
=============

This is a lookup reference for Python functions and classes. You do not need to read it
from top to bottom. Begin with :doc:`start_here` or :doc:`quickstart`, then return here
to check arguments and return values.

Import as ``import blockchainkit as bk``. Public names are re-exported by
the five domain subpackages; the modules below show implementation details.

Cryptography
------------

.. automodule:: blockchainkit.crypto.hashing
   :members:

.. automodule:: blockchainkit.crypto.asymmetric
   :members:

.. automodule:: blockchainkit.crypto.sharing
   :members:

.. automodule:: blockchainkit.crypto.curves
   :members:

.. automodule:: blockchainkit.crypto.signatures
   :members:

Structures and state
--------------------

.. automodule:: blockchainkit.structures.merkle
   :members:

.. automodule:: blockchainkit.structures.transaction
   :members:
   :exclude-members: canonical_json

.. automodule:: blockchainkit.structures.block
   :members:

.. automodule:: blockchainkit.structures.chain
   :members:

Consensus models
----------------

.. automodule:: blockchainkit.consensus.pow
   :members:

.. automodule:: blockchainkit.consensus.pos
   :members:

Peer simulation
---------------

.. automodule:: blockchainkit.network.p2p
   :members:

Execution
---------

.. automodule:: blockchainkit.vm.execution
   :members:
