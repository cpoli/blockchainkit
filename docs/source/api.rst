API reference
=============

This is a lookup reference for Python functions and classes. You do not need to read it
from top to bottom. Begin with :doc:`start_here` or :doc:`quickstart`, then return here
to check arguments and return values.

Import as ``import blockchainkit as bk``. Public names are re-exported by
the five domain subpackages; the modules below show implementation details.

Cryptography
------------

.. automodule:: blockchainkit.crypto.systems.hashing
   :members:

.. automodule:: blockchainkit.crypto.systems.commitments
   :members:

.. automodule:: blockchainkit.crypto.core.base
   :members:

.. automodule:: blockchainkit.crypto.systems.asymmetric
   :members:

.. automodule:: blockchainkit.crypto.systems.sharing
   :members:

.. automodule:: blockchainkit.crypto.systems.curves
   :members:

.. automodule:: blockchainkit.crypto.systems.signatures
   :members:

Structures and state
--------------------

.. automodule:: blockchainkit.structures.core.base
   :members:

.. automodule:: blockchainkit.structures.systems.merkle
   :members:

.. automodule:: blockchainkit.structures.systems.transaction
   :members:

.. automodule:: blockchainkit.structures.systems.block
   :members:

.. automodule:: blockchainkit.structures.systems.ledger
   :members:

.. automodule:: blockchainkit.structures.systems.chain
   :members:

Consensus models
----------------

.. automodule:: blockchainkit.consensus.core.base
   :members:

.. automodule:: blockchainkit.consensus.systems.pow
   :members:

.. automodule:: blockchainkit.consensus.systems.catch_up
   :members:

.. automodule:: blockchainkit.consensus.systems.pos
   :members:

Peer simulation
---------------

.. automodule:: blockchainkit.network.core.base
   :members:

.. automodule:: blockchainkit.network.systems.gossip
   :members:

Execution
---------

.. automodule:: blockchainkit.vm.core.base
   :members:

.. automodule:: blockchainkit.vm.systems.stack_machine
   :members:
