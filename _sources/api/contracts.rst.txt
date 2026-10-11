blockchainkit.contracts
=======================

.. include:: /_generated/nav/contracts.rst

.. automodule:: blockchainkit.contracts
   :no-members:

A world-state model of accounts and contracts calling each other, the
contracts and standards that shaped the field, the bugs behind its largest
losses, and the tools that check contracts: Hoare triples, symbolic
execution, design by contract, and fuzzing.

Every public name below is re-exported by the subpackage: import it as
``bk.contracts.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.contracts.visualizers``, which loads
Matplotlib.

Types and results
-----------------

.. automodule:: blockchainkit.contracts.core.base
   :members:

The world-state model
---------------------

.. automodule:: blockchainkit.contracts.systems.world
   :members:

Contracts
---------

.. automodule:: blockchainkit.contracts.systems.ricardian
   :members:

.. automodule:: blockchainkit.contracts.systems.capabilities
   :members:

.. automodule:: blockchainkit.contracts.systems.tokens
   :members:

.. automodule:: blockchainkit.contracts.systems.payments
   :members:

.. automodule:: blockchainkit.contracts.systems.randomness
   :members:

.. automodule:: blockchainkit.contracts.systems.wallets
   :members:

.. automodule:: blockchainkit.contracts.systems.proxies
   :members:

.. automodule:: blockchainkit.contracts.systems.factory
   :members:

.. automodule:: blockchainkit.contracts.systems.governance
   :members:

Verification
------------

.. automodule:: blockchainkit.contracts.systems.hoare
   :members:

.. automodule:: blockchainkit.contracts.systems.symbolic
   :members:

.. automodule:: blockchainkit.contracts.systems.design_by_contract
   :members:

.. automodule:: blockchainkit.contracts.systems.fuzzing
   :members:

.. automodule:: blockchainkit.contracts.utils.expressions
   :members:

Plotting
--------

.. automodule:: blockchainkit.contracts.visualizers.plots
   :members:
